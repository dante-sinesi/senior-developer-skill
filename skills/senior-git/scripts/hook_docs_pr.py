#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): un Pull Request que cambia el código no se abre sin la documentación al día.

Vale en proyectos con `docs/ESTADO.md` de escala mediana o grande, ante cada `gh pr create`. Si la rama cambia código y no toca
requisitos, casos de uso, secuencias, diagramas ni decisiones:
  - `feat`, o cualquier tipo que agregue archivos de código, rutas, pantallas o comandos nuevos          → bloquea
  - `fix`, `refactor`, `perf`, `test`, `chore`, `style`, `docs`, `build`, `ci` o `revert`                → pasa si la descripción
    trae la línea «Documentación: sin cambios porque <motivo>», que queda a la vista de quien revisa
  - no se puede saber el tipo o el diff                                                                  → pasa y lo dice
El usuario autoriza uno escribiendo `/permitir-sin-docs`, o deja el proyecto en advertencia con `/docs-modo aviso`. Si algo
falla por dentro, deja pasar (con SENIOR_HOOK_DEPURAR=1 el error se ve). Solo biblioteca estándar.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parents[1] / "senior" / "scripts"))

CREAR = re.compile(r"(?:^|[;&|(\n])\s*(?:&\s*)?(?:\S*[\\/])?gh(?:\.exe)?\b(?:\s+(?:-R|--repo)[ =]\S+)*\s+pr\s+create\b", re.IGNORECASE)
CAMBIO_DE_CARPETA = re.compile(r"(?:^|[;&|\n])\s*(?:cd|pushd|Set-Location)\s+(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", re.IGNORECASE)
COMMIT_PREVIO = re.compile(r"\bgit\b[^;&|\n]*\bcommit\b")
VALOR = r"""(?:\s+|=)("(?:[^"\\`]|[\\`].)*"|'[^']*'|[^\s;&|]+)"""
TIPOS_JUSTIFICABLES = {"fix", "refactor", "perf", "test", "chore", "style", "docs", "build", "ci", "revert"}
CARPETAS_DE_DOCUMENTACION = ("docs/requisitos/", "docs/casos-de-uso/", "docs/secuencias/", "docs/diagramas/", "docs/decisiones/")
JUSTIFICACION = re.compile(r"Documentaci[oó]n:\s*sin cambios porque[ \t]+(?![<\"'])\S+(?:[ \t]+\S+)+", re.IGNORECASE)
SUPERFICIE = re.compile(r"""Route::(?:get|post|put|patch|delete|resource)\(|\b(?:app|router)\.(?:get|post|put|patch|delete)\(\s*['"`]/|"""
                        r"""@\w+\.(?:route|get|post|put|patch|delete)\(\s*['"]/|<Route\s|\badd_parser\(|@(?:\w+\.)?command\(""")
LINEA_PEDIDA = "«Documentación: sin cambios porque <motivo>»"


def git(raiz, *args):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
    return r.returncode, r.stdout


def opcion(argumentos, *nombres):
    for nombre in nombres:
        m = re.search(r"(?<![\w-])" + re.escape(nombre) + VALOR, argumentos)
        if m:
            return m.group(1).strip("\"'")
    return None


def carpeta_del_comando(comando, antes, cwd):
    """La carpeta donde correrá gh: la del último `cd` anterior, si lo hay."""
    carpeta = Path(cwd)
    for m in CAMBIO_DE_CARPETA.finditer(comando[:antes]):
        destino = m.group(1).strip("\"'")
        unidad = re.match(r"^/([a-zA-Z])/(.*)$", destino)  # rutas de Git Bash
        if unidad:
            destino = f"{unidad.group(1)}:/{unidad.group(2)}"
        destino = Path(os.path.expanduser(destino))
        carpeta = destino if destino.is_absolute() else carpeta / destino
    return carpeta


def archivos_cambiados(raiz, base, cabeza, con_arbol):
    """[(estado, ruta)] de la rama frente a su base, más lo sin commitear si el commit va en el mismo comando. None si no se puede saber."""
    for referencia in (f"origin/{base}", base):
        codigo, salida = git(raiz, "merge-base", referencia, cabeza)
        if codigo == 0:
            break
    else:
        return None, None
    comun = salida.strip()
    codigo, salida = git(raiz, "diff", "--name-status", "--no-renames", comun, *([] if con_arbol else [cabeza]))
    if codigo != 0:
        return None, None
    cambios = [(l.split("\t")[0][:1], l.split("\t")[-1]) for l in salida.splitlines() if "\t" in l]
    if con_arbol:
        cambios += [("A", l) for l in git(raiz, "ls-files", "--others", "--exclude-standard")[1].splitlines() if l]
    return comun, cambios


def agrega_superficie(raiz, comun, cabeza, con_arbol, codigo):
    """Rutas de lo nuevo: archivos de código agregados o líneas que declaran rutas, pantallas o comandos."""
    nuevos = [r for estado, r in codigo if estado == "A"]
    if nuevos:
        return nuevos
    salida = git(raiz, "diff", "-U0", comun, *([] if con_arbol else [cabeza]), "--", *[r for _, r in codigo][:200])[1]
    archivo, hallados = "", []
    for linea in salida.splitlines():
        if linea.startswith("+++ "):
            archivo = linea[6:]
        elif linea.startswith("+") and SUPERFICIE.search(linea) and archivo not in hallados:
            hallados.append(archivo)
    return hallados


def tipo_de(raiz, titulo, comun, cabeza):
    patron = re.compile(r"^\s*([a-z]+)(?:\([^)]*\))?!?:", re.IGNORECASE)
    if titulo:
        m = patron.match(titulo)
        tipos = [m.group(1).lower()] if m else []
    else:
        asuntos = git(raiz, "log", "--format=%s", f"{comun}..{cabeza}")[1].splitlines()
        tipos = [m.group(1).lower() for m in map(patron.match, asuntos) if m]
    if "feat" in tipos:
        return "feat"
    return tipos[0] if tipos and tipos[0] in TIPOS_JUSTIFICABLES else None


def texto_del_cuerpo(raiz, carpeta, comando, argumentos, comun, cabeza):
    archivo = opcion(argumentos, "--body-file", "-F")
    if archivo and archivo != "-":
        ruta = Path(archivo) if Path(archivo).is_absolute() else carpeta / archivo
        try:
            return comando + "\n" + ruta.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return comando
    if re.search(r"(?<![\w-])--fill", argumentos):
        return comando + "\n" + git(raiz, "log", "--format=%B", f"{comun}..{cabeza}")[1]
    return comando


def evaluar(comando, cwd):
    """(None, "") si pasa en silencio; ("aviso", texto) si pasa diciendo algo; ("falta", datos) si corresponde frenar."""
    m = CREAR.search(comando)
    if not m:
        return None, ""
    carpeta = carpeta_del_comando(comando, m.start(), cwd)
    if not carpeta.is_dir():
        return None, ""
    codigo, salida = git(carpeta, "rev-parse", "--show-toplevel")
    if codigo != 0:
        return None, ""
    raiz = Path(salida.strip())
    if not (raiz / "docs" / "ESTADO.md").is_file():
        return None, ""
    import ci
    import escala
    import hook_lectura_previa
    if escala.declarada(raiz) not in ("mediano", "grande"):
        return None, ""
    argumentos = comando[m.end():]
    base = opcion(argumentos, "--base", "-B") or ci.rama_principal(str(raiz))
    cabeza = (opcion(argumentos, "--head", "-H") or "HEAD").split(":")[-1]
    con_arbol = bool(COMMIT_PREVIO.search(comando[:m.start()]))
    comun, cambios = archivos_cambiados(raiz, base, cabeza, con_arbol)
    if cambios is None:
        return "aviso", f"senior (documentación en el Pull Request): no se pudo determinar el diff contra «{base}»; no se comprobó si la documentación quedó al día."
    codigo_cambiado = [(e, r) for e, r in cambios if hook_lectura_previa.es_codigo(r.lower())]
    if not codigo_cambiado or any(r.lower().startswith(CARPETAS_DE_DOCUMENTACION) for _, r in cambios):
        return None, ""
    tipo = tipo_de(raiz, opcion(argumentos, "--title", "-t"), comun, cabeza)
    nuevo = agrega_superficie(raiz, comun, cabeza, con_arbol, codigo_cambiado)
    if tipo != "feat" and not nuevo:
        if tipo is None:
            return "aviso", "senior (documentación en el Pull Request): no se pudo saber el tipo del cambio (falta el prefijo de Conventional Commits en el título); no se comprobó la documentación."
        if JUSTIFICACION.search(texto_del_cuerpo(raiz, carpeta, comando, argumentos, comun, cabeza)):
            return None, ""
    return "falta", {"raiz": raiz, "tipo": tipo, "nuevo": nuevo, "codigo": [r for _, r in codigo_cambiado]}


def lista(rutas):
    return ", ".join(rutas[:4]) + (f" y {len(rutas) - 4} más" if len(rutas) > 4 else "")


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        if datos.get("tool_name") not in ("Bash", "PowerShell"):
            return 0
        comando = str((datos.get("tool_input") or {}).get("command") or "")
        if "create" not in comando.lower():
            return 0
        cwd = datos.get("cwd") or os.getcwd()
        que, dato = evaluar(comando, cwd)
        if que is None:
            return 0
        if que == "aviso":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": dato}}, ensure_ascii=False))
            return 0
        import modo_hooks
        raiz = dato["raiz"]
        sesion = modo_hooks.raiz_del_proyecto(cwd)  # donde guarda lo que escribe el usuario
        if "aviso" in (modo_hooks.cargar(raiz)["docs_modo"], modo_hooks.cargar(sesion)["docs_modo"]):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext":
                              f"senior (documentación en el Pull Request, en modo aviso): cambia {lista(dato['codigo'])} sin tocar la documentación."}}, ensure_ascii=False))
            return 0
        if modo_hooks.consumir_sin_docs(sesion) or modo_hooks.consumir_sin_docs(raiz):
            return 0
        if dato["nuevo"]:
            motivo = f"agrega algo nuevo ({lista(dato['nuevo'])}) y no toca la documentación; con eso no alcanza ninguna etiqueta ni justificación"
        elif dato["tipo"] == "feat":
            motivo = f"es un `feat` que cambia {lista(dato['codigo'])} y no toca la documentación"
        else:
            motivo = f"cambia {lista(dato['codigo'])} sin tocar la documentación y la descripción no trae la línea {LINEA_PEDIDA}"
        actualizar = ("actualizá en esta rama los documentos que el cambio afecta (docs/requisitos, docs/casos-de-uso, docs/secuencias, docs/diagramas o docs/decisiones; "
                      "mandan los requisitos y las decisiones, no el código), commitealos con la misma autorización que tenías para el Pull Request y repetí `gh pr create`.")
        if not dato["nuevo"] and dato["tipo"] != "feat":
            actualizar = f"si la documentación sigue siendo cierta, agregá a la descripción la línea {LINEA_PEDIDA} con el motivo real; si no, " + actualizar
        instruccion = (actualizar + " Si no se puede, anotá el pendiente en `docs/pendientes.md` y seguí con otra tarea. Solo el usuario puede dejarlo pasar así, escribiendo en el chat "
                       "`/permitir-sin-docs` (vale para uno).")
        print(modo_hooks.respuesta(raiz, "documentación en el Pull Request", "se intentó abrir un Pull Request " + motivo,
                                   f"Claude quiere abrir un Pull Request que {motivo}. ¿Lo autorizás así?", instruccion))
    except Exception:  # noqa: BLE001 motivo: si algo falla, el hook deja pasar y no frena nada (con SENIOR_HOOK_DEPURAR=1 el error se ve)
        if os.environ.get("SENIOR_HOOK_DEPURAR") == "1":
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
