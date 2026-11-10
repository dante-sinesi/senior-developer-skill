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

Si no existe docs/ESTADO.md, no imprime nada (el hook no debe molestar en
proyectos que no usan esta metodología). Solo biblioteca estándar.
"""
import argparse
import re
import sys
from pathlib import Path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
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
