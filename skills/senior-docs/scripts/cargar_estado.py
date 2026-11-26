#!/usr/bin/env python3
"""Imprime el estado del proyecto para cargarlo al abrir una sesión.

Corre como hook SessionStart de Claude Code (al abrir, retomar, limpiar y
compactar): lo que imprime entra como contexto de la sesión. Es un resumen
corto (hasta unas 600 palabras), no los documentos completos:
  - la secuencia de todo cambio de código y la escala del proyecto
  - cuántos documentos hay de cada tipo y cuántos commits de código pasaron
    desde el último cambio en la documentación
  - docs/ESTADO.md (recortado si es largo)
  - fichas de cambio "en curso" con sus pasos abiertos
  - cantidad de pendientes en la bandeja y pista del mapa de conceptos

Uso:
    python cargar_estado.py [--raiz .]    # a mano
    python cargar_estado.py --hook        # como hook: lee el JSON de la entrada y busca el proyecto desde su `cwd`

Como hook no hace nada fuera de un proyecto con docs/ESTADO.md, y ante cualquier
falla sale en silencio (con SENIOR_HOOK_DEPURAR=1 el error se ve).

Antes de nada comprueba la guardia de autoría y, si falta algún hook, lo activa (solo imprime cuando actúa).
Si no existe docs/ESTADO.md, no imprime más. Solo biblioteca estándar.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def asegurar_guardia(raiz):
    """Activa la guardia de autoría si falta (hooks de Git del repositorio y hook global de Claude Code).
    No imprime nada cuando ya está todo activo."""
    guardia = Path(__file__).resolve().parents[2] / "senior-git" / "scripts" / "guardia_autoria.py"
    if not guardia.exists():
        return
    try:
        p = subprocess.run([sys.executable, "-I", str(guardia), "asegurar", "--silencioso", "--raiz", str(raiz)],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return
    if p.stdout.strip():
        print(p.stdout.strip())


def avisar_token_diet(raiz):
    """Si Token Diet no está instalada (o es anterior a la 1.0.2), lo dice UNA vez por proyecto; senior sigue funcionando igual."""
    import importlib.util
    ruta = Path(__file__).resolve().parents[2] / "senior" / "scripts" / "token_diet.py"
    marca = raiz / ".temporal" / ".aviso-token-diet"
    try:
        if marca.exists():
            return
        espec = importlib.util.spec_from_file_location("senior_token_diet", ruta)
        modulo = importlib.util.module_from_spec(espec)
        espec.loader.exec_module(modulo)
        aviso = modulo.aviso()
        if not aviso:
            return
        print("# Token Diet (opcional)")
        print(aviso + " Este aviso sale una sola vez en este proyecto.\n")
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text("avisado\n", encoding="utf-8")
    except Exception:  # noqa: BLE001 - es solo un aviso
        return


SECUENCIA = ("En todo cambio de código, por chico que sea: leer el estado y los documentos afectados, test que falle si cambia el comportamiento, "
             "programar lo mínimo, verificar y documentar en el mismo cambio. Lo que no corresponda, decirlo al cerrar. El código es evidencia, no fuente: "
             "mandan los requisitos y las decisiones del usuario.")
TOPE_ESTADO = 320  # palabras de ESTADO.md; con el resto del resumen queda por debajo de 600


def raiz_desde(cwd):
    """El proyecto es la carpeta de `cwd` o la primera de sus carpetas superiores con docs/ESTADO.md."""
    actual = Path(cwd).resolve()
    for carpeta in (actual, *actual.parents):
        if (carpeta / "docs" / "ESTADO.md").is_file():
            return carpeta
    return None


def recortar(lineas, palabras, maximo_lineas=60):
    """(líneas que entran, True si quedó algo afuera)."""
    salida, quedan = [], palabras
    for linea in lineas[:maximo_lineas]:
        n = len(linea.split())
        if n > quedan:
            if quedan:
                salida.append(" ".join(linea.split()[:quedan]) + " …")
            return salida, True
        salida.append(linea)
        quedan -= n
    return salida, len(lineas) > maximo_lineas


def escala_de(texto):
    m = re.search(r"(?m)^\*\*Escala del proyecto:\*\*[ \t]*(\S+)", texto)
    return m.group(1) if m else "sin declarar"


def documentos_por_tipo(docs):
    cuentas = []
    for carpeta in sorted(d for d in docs.iterdir() if d.is_dir() and not d.name.startswith(".")):
        n = sum(1 for f in carpeta.rglob("*") if f.is_file() and not f.name.startswith("."))
        if n:
            cuentas.append(f"{carpeta.name}: {n}")
    return cuentas


def atraso_de_docs(raiz):
    """Commits que tocaron código desde el último que tocó docs/. 0 si no se puede saber."""
    def git(*args):
        r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    try:
        ultimo = git("log", "-1", "--format=%H", "--", "docs")
        if not ultimo:
            return 0
        n = git("rev-list", "--count", ultimo + "..HEAD", "--", ".", ":(exclude)docs", ":(exclude,glob)**/*.md")
        return int(n or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def olvidar_lecturas(datos):
    """Tras compactar o limpiar, lo leído ya no está en la conversación: la barrera de lectura lo vuelve a pedir."""
    ruta = Path(__file__).resolve().parents[2] / "senior" / "scripts" / "hook_lectura_previa.py"
    if datos.get("source") not in ("compact", "clear") or not ruta.exists():
        return
    import importlib.util
    espec = importlib.util.spec_from_file_location("senior_lectura_previa", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    modulo.olvidar(datos.get("session_id"), {c for c in (datos.get("cwd") or os.getcwd(), os.environ.get("CLAUDE_PROJECT_DIR")) if c})


def resumen(raiz):
    docs = raiz / "docs"
    texto = (docs / "ESTADO.md").read_text(encoding="utf-8-sig", errors="replace")
    print("# Estado del proyecto (cargado automáticamente)")
    print(f"Proyecto: {raiz.as_posix()} — escala: {escala_de(texto)}.")
    print(SECUENCIA)
    cuentas = documentos_por_tipo(docs)
    if cuentas:
        print("Documentos en docs/ (" + ", ".join(cuentas[:12]) + ")" + ("; se ubican con docs/INDEX.md." if (docs / "INDEX.md").exists() else "."))
    atraso = atraso_de_docs(raiz)
    if atraso:
        print(f"Atención: {atraso} commits de código desde el último cambio en la documentación.")
    carpeta = docs / "cambios"
    for ficha in sorted(carpeta.glob("*.md"))[:40] if carpeta.is_dir() else []:
        contenido = ficha.read_text(encoding="utf-8-sig", errors="replace")
        if re.search(r"(?im)^\s*\**estado\**\s*:\s*\**\s*en curso", contenido):
            abiertos = [l.strip() for l in contenido.splitlines() if re.match(r"^\s*-\s*\[ \]", l)]
            print(f"Ficha en curso: docs/cambios/{ficha.name} — pasos abiertos: {len(abiertos)}")
            for paso in abiertos[:3]:
                print("  " + " ".join(paso.split()[:20]))
            break
    pendientes = docs / "pendientes.md"
    if pendientes.exists():
        n = len([l for l in pendientes.read_text(encoding="utf-8-sig", errors="replace").splitlines() if re.match(r"^\s*-\s*\[ \]", l)])
        if n:
            print(f"Bandeja de pendientes: {n} abiertos (docs/pendientes.md).")
    if (docs / ".grafo.json").exists():
        print("Mapa de conceptos: indexar_docs.py (consultar <término> | vecinos <id>) antes de leer documentos completos.")
    lineas, cortado = recortar(texto.splitlines(), TOPE_ESTADO)
    print("\n## docs/ESTADO.md")
    print("\n".join(lineas))
    if cortado:
        print("… (ESTADO.md sigue: leerlo completo antes de tocar código)")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--hook", action="store_true")
    args = ap.parse_args()
    try:
        if args.hook:
            datos = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
            olvidar_lecturas(datos)
            raiz = raiz_desde(datos.get("cwd") or os.getcwd())
            if raiz is None:
                return 0
        else:
            raiz = Path(args.raiz).resolve()
        asegurar_guardia(raiz)
        avisar_token_diet(raiz)
        if (raiz / "docs" / "ESTADO.md").exists():
            resumen(raiz)
    except Exception:  # noqa: BLE001 motivo: un recordatorio nunca rompe la sesión
        if not args.hook or os.environ.get("SENIOR_HOOK_DEPURAR") == "1":
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
