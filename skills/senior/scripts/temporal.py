#!/usr/bin/env python3
"""Prepara `.temporal/`, la carpeta del proyecto para todo lo que es de trabajo y no se sube: muestras, capturas,
borradores, resultados de pruebas y archivos generados de paso.

Regla máxima del paquete senior: nada se crea fuera del directorio del proyecto. Si hace falta un archivo de
paso, va acá, no en la carpeta temporal del sistema ni en el escritorio. Un caso puntual que necesite salir del
proyecto (por ejemplo, un servidor local) se le pide al usuario cada vez.

Uso:
    python temporal.py [--raiz .]
Crea `.temporal/` y agrega `.temporal/` al `.gitignore` del proyecto si falta (y crea el `.gitignore` si no existe).
Imprime la ruta de la carpeta. Es seguro repetirlo. Solo biblioteca estándar.
"""
import argparse
import sys
from pathlib import Path

CARPETA = ".temporal"
LINEA = ".temporal/"


def preparar(raiz):
    """Devuelve (carpeta, creada, gitignore_actualizado)."""
    carpeta = raiz / CARPETA
    creada = not carpeta.is_dir()
    carpeta.mkdir(parents=True, exist_ok=True)
    gi = raiz / ".gitignore"
    texto = gi.read_text(encoding="utf-8-sig", errors="replace") if gi.exists() else ""
    ignorada = any(l.strip() in (LINEA, CARPETA, "/" + LINEA, "/" + CARPETA) for l in texto.splitlines())
    if not ignorada:
        sep = "" if not texto or texto.endswith("\n") else "\n"
        gi.write_text(texto + sep + "\n# Archivos de trabajo de Claude (no se suben)\n" + LINEA + "\n", encoding="utf-8", newline="\n")
    return carpeta, creada, not ignorada


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    args = ap.parse_args()
    carpeta, creada, gi = preparar(Path(args.raiz).resolve())
    print(f"Carpeta de trabajo: {carpeta.as_posix()}" + (" (creada)" if creada else ""))
    if gi:
        print("Se agregó `.temporal/` al .gitignore: git no la sube.")


if __name__ == "__main__":
    main()
