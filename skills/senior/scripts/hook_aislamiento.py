#!/usr/bin/env python3
"""Hook de aislamiento de roles: cada rol escribe solo en su carpeta.

Regla: el diseñador escribe únicamente en <proyecto>/diseno/; producción (senior) escribe en todo
lo demás y no toca diseno/. Ambos pueden leer todo.

Cómo se determina el rol (en este orden):
  1. Si el directorio de trabajo de la sesión está dentro de <proyecto>/diseno/  ->  rol "diseno".
  2. Si existe <proyecto>/.claude/rol-activo con "diseno" o "produccion"          ->  ese rol.
  3. Si no hay nada de lo anterior                                                 ->  sin restricciones.
Así dos sesiones simultáneas no se pisan: la de diseño se abre dentro de diseno/ y la de producción
usa el marcador "produccion"; en un solo chat que alterna de rol se cambia el marcador.

Uso:
    (sin argumentos)                     funciona como hook PreToolUse leyendo el JSON de stdin
    rol <diseno|produccion|ninguno>      escribe o borra el marcador de rol (--raiz)
    estado [--raiz] [--cwd]              muestra qué rol rige
    probar --rol R --ruta P [--raiz]     dice si el rol R podría escribir en la ruta P
    configuracion                        imprime el bloque de settings.json para registrar el hook

Control aproximado de comandos de terminal: se analizan redirecciones y comandos de escritura
frecuentes (>, tee, cp, mv, rm, sed -i, Set-Content…), pero un script o un comando ofuscado puede
escribir sin ser detectado. El hook bloquea con código de salida 2. Solo biblioteca estándar.
"""
import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path

HERRAMIENTAS_ARCHIVO = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
HERRAMIENTAS_TERMINAL = {"Bash", "PowerShell"}
MARCADOR = Path(".claude") / "rol-activo"


def norm(p):
    return os.path.normcase(os.path.abspath(str(p)))


def dentro(ruta, carpeta):
    r, c = norm(ruta), norm(carpeta)
    return r == c or r.startswith(c + os.sep)


def encontrar_raiz(cwd):
    """Raíz del proyecto: el ancestro más cercano que contiene diseno/, o el padre de diseno/ si cwd está dentro."""
    p = Path(cwd).resolve()
    for a in [p, *p.parents]:
        if a.name.lower() == "diseno" and a.parent.exists():
            return a.parent
        if (a / "diseno").is_dir() or (a / MARCADOR).exists():
            return a
    return None


def rol_de(cwd):
    """Devuelve (rol, raiz). rol: 'diseno', 'produccion' o None."""
    raiz = encontrar_raiz(cwd)
    if raiz is None:
        return None, None
    if dentro(cwd, raiz / "diseno"):
        return "diseno", raiz
    marcador = raiz / MARCADOR
    if marcador.exists():
        valor = marcador.read_text(encoding="utf-8", errors="replace").strip().lower()
        if valor in ("diseno", "produccion"):
            return valor, raiz
    return None, raiz


def decidir(rol, raiz, ruta):
    """Devuelve (permitido, motivo)."""
    if rol is None or raiz is None:
        return True, ""
    if dentro(ruta, raiz / MARCADOR):
        return True, ""
    en_diseno = dentro(ruta, raiz / "diseno")
    if rol == "diseno" and not en_diseno:
        return False, ("Aislamiento de roles: el diseñador solo escribe en diseno/. "
                       f"Para cambiar «{ruta}», dejar el pedido en diseno/ENTREGA.md para producción.")
    if rol == "produccion" and en_diseno:
        return False, ("Aislamiento de roles: producción no escribe en diseno/. "
                       "Dejar el pedido en docs/solicitudes-de-diseno.md para el diseñador.")
    return True, ""


REDIRECCION = re.compile(r"(?<![0-9&<>])>>?\s*(\"[^\"]+\"|'[^']+'|[^\s|;&<>()]+)")
ESCRITORES = ("tee", "cp", "mv", "rm", "touch", "mkdir", "rmdir", "ln", "truncate", "install", "sed", "Set-Content",
              "Add-Content", "Out-File", "New-Item", "Remove-Item", "Copy-Item", "Move-Item", "Rename-Item", "Clear-Content")


def rutas_escritas(comando):
    """Rutas que un comando de terminal probablemente escribe (aproximado)."""
    rutas = []
    for m in REDIRECCION.finditer(comando):
        destino = m.group(1).strip("\"'")
        if destino not in ("/dev/null", "NUL", "nul", "$null") and not destino.startswith("&"):
            rutas.append(destino)
    for sub in re.split(r"[;|&]+|\n", comando):
        try:
            tokens = shlex.split(sub, posix=False)
        except ValueError:
            tokens = sub.split()
        if not tokens:
            continue
        cmd = tokens[0].strip("\"'")
        if cmd in ESCRITORES:
            if cmd == "sed" and not any(t.startswith("-i") for t in tokens):
                continue
            candidatos = [t.strip("\"'") for t in tokens[1:] if not t.startswith("-") and not t.startswith("$")]
            candidatos = [t for t in candidatos if re.search(r"[\\/.]", t)]
            if cmd in ("cp", "Copy-Item") and candidatos:
                candidatos = candidatos[-1:]
            rutas.extend(candidatos)
    return rutas


def accion_hook():
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return 0  # sin entrada interpretable no se bloquea nada
    cwd = datos.get("cwd") or os.getcwd()
    rol, raiz = rol_de(cwd)
    if rol is None:
        return 0
    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}
    objetivos = []
    if herramienta in HERRAMIENTAS_ARCHIVO:
        objetivos = [entrada.get("file_path") or entrada.get("notebook_path") or ""]
    elif herramienta in HERRAMIENTAS_TERMINAL:
        objetivos = rutas_escritas(entrada.get("command", ""))
    for objetivo in objetivos:
        if not objetivo:
            continue
        ruta = objetivo if os.path.isabs(objetivo) else os.path.join(cwd, objetivo)
        permitido, motivo = decidir(rol, raiz, ruta)
        if not permitido:
            print(motivo, file=sys.stderr)
            return 2
    return 0


def cmd_rol(valor, raiz):
    marcador = raiz / MARCADOR
    if valor == "ninguno":
        if marcador.exists():
            marcador.unlink()
        print("Rol: sin restricciones (marcador borrado).")
        return
    marcador.parent.mkdir(parents=True, exist_ok=True)
    marcador.write_text(valor + "\n", encoding="utf-8")
    print(f"Rol activo: {valor} (marcador en {MARCADOR.as_posix()}).")


def cmd_configuracion():
    ruta = str(Path(__file__).resolve())
    bloque = {"hooks": {"PreToolUse": [{
        "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell",
        "hooks": [{"type": "command", "command": f"python \"{ruta}\""}]}]}}
    print(json.dumps(bloque, indent=2, ensure_ascii=False))
    print("\nAgregar este bloque a .claude/settings.json del proyecto (con aprobación del usuario). "
          "Sin marcador de rol ni sesión dentro de diseno/, no restringe nada.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) == 1:
        sys.exit(accion_hook())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["rol", "estado", "probar", "configuracion"])
    ap.add_argument("valor", nargs="?", choices=["diseno", "produccion", "ninguno"])
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--rol", choices=["diseno", "produccion"])
    ap.add_argument("--ruta")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if args.accion == "configuracion":
        cmd_configuracion()
    elif args.accion == "rol":
        if not args.valor:
            ap.error("indicar diseno, produccion o ninguno")
        cmd_rol(args.valor, raiz)
    elif args.accion == "estado":
        rol, r = rol_de(args.cwd or raiz)
        print(f"Rol que rige: {rol or 'ninguno (sin restricciones)'}; raíz del proyecto: {r or 'no detectada'}.")
    else:
        permitido, motivo = decidir(args.rol, raiz, args.ruta)
        print("PERMITIDO" if permitido else f"BLOQUEADO: {motivo}")


if __name__ == "__main__":
    main()
