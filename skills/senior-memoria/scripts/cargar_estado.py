#!/usr/bin/env python3
"""Imprime el estado del proyecto para cargarlo al abrir una sesión.

Pensado para usarse como hook de apertura (SessionStart) de Claude Code: lo
que este script imprime entra como contexto de la sesión. Muestra un resumen
corto, no los documentos completos:
  - docs/ESTADO.md (hasta 60 líneas)
  - fichas de cambio "en curso" con sus pasos abiertos
  - cantidad de pendientes en la bandeja
  - pista de cómo consultar el mapa de conceptos

Uso manual:
    python cargar_estado.py [--raiz .]

Antes de nada comprueba la guardia de autoría y, si falta algún hook, lo activa (solo imprime cuando actúa).
Si no existe docs/ESTADO.md, no imprime más (el hook no debe molestar en
proyectos que no usan esta metodología). Solo biblioteca estándar.
"""
import argparse
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


def iniciar_fuentes(raiz):
    """Crea documentos-externos/ si falta y convierte lo pendiente (mudo si no hay nada que hacer)."""
    conversor = Path(__file__).resolve().parents[2] / "senior-relevar" / "scripts" / "convertir_fuentes.py"
    if not conversor.exists():
        return
    try:
        p = subprocess.run([sys.executable, "-I", str(conversor), "--iniciar", "--raiz", str(raiz)],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return
    if (p.stdout + p.stderr).strip():
        print((p.stdout + p.stderr).strip())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    asegurar_guardia(raiz)
    iniciar_fuentes(raiz)
    estado = raiz / "docs" / "ESTADO.md"
    if not estado.exists():
        return
    lineas = estado.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    print("# Estado del proyecto (cargado automáticamente al abrir la sesión)")
    print("\n".join(lineas[:60]))
    if len(lineas) > 60:
        print(f"… (ESTADO.md tiene {len(lineas)} líneas; leerlo completo si hace falta)")
    carpeta = raiz / "docs" / "cambios"
    for ficha in sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []:
        texto = ficha.read_text(encoding="utf-8-sig", errors="replace")
        if re.search(r"(?im)^\s*\**estado\**\s*:\s*\**\s*en curso", texto):
            abiertos = [l.strip() for l in texto.splitlines() if re.match(r"^\s*-\s*\[ \]", l)]
            print(f"\nFicha en curso: docs/cambios/{ficha.name} — pasos abiertos: {len(abiertos)}")
            for paso in abiertos[:6]:
                print(f"  {paso}")
    pendientes = raiz / "docs" / "pendientes.md"
    if pendientes.exists():
        n = len([l for l in pendientes.read_text(encoding="utf-8-sig").splitlines() if re.match(r"^\s*-\s*\[ \]", l)])
        if n:
            print(f"\nBandeja de pendientes: {n} abiertos (docs/pendientes.md).")
    if (raiz / "docs" / ".grafo.json").exists():
        print("\nMapa de conceptos disponible: consultar con senior-memoria/scripts/indexar_docs.py "
              "(consultar <término> | vecinos <id>) antes de leer documentos completos.")


if __name__ == "__main__":
    main()
