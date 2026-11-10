#!/usr/bin/env python3
"""Valida mensajes de commit (Conventional Commits) y el nombre de la rama.

Uso:
    python validar_commits.py [--raiz .] [--base main]

Revisa los commits de la rama actual que no están en la base (por defecto
main o master, el que exista) y comprueba:
  - Formato: tipo(ámbito opcional): descripción
  - Tipos válidos: feat, fix, docs, refactor, test, chore, perf, build, ci, style, revert, security
  - Descripción en minúscula inicial, sin punto final, de hasta 72 caracteres
  - Nombre de rama: tipo/descripcion-corta (no se permite trabajar en main/master)
Ejemplo válido: feat(carrito): aplicar descuento por volumen (RN-001)

El IDIOMA de la descripción (español neutro) no se puede comprobar de forma
fiable por script: lo revisa quien hace el commit.
Códigos de salida: 0 todo bien, 1 hay problemas. Solo biblioteca estándar.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

TIPOS = "feat|fix|docs|refactor|test|chore|perf|build|ci|style|revert|security"
PATRON = re.compile(rf"^(?:{TIPOS})(?:\([\w\-./]+\))?!?: \S.*$")
RAMA = re.compile(rf"^(?:{TIPOS})/[a-z0-9][a-z0-9\-._]*$")


def git(raiz, *args):
    p = subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8",
                       errors="replace", timeout=60)
    return p.stdout.strip(), p.returncode


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--base", default=None)
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0] != "true":
        print("Commits: no es un repositorio git.")
        sys.exit(1)
    rama, _ = git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
    problemas = []
    if rama in ("main", "master"):
        problemas.append(f"Rama: se está trabajando directamente en '{rama}'; crear una rama por cambio.")
    elif not RAMA.match(rama):
        problemas.append(f"Rama: '{rama}' no sigue tipo/descripcion-corta (ej. feat/descuento-volumen).")
    base = args.base
    if not base:
        for candidata in ("main", "master"):
            if git(raiz, "rev-parse", "--verify", "--quiet", candidata)[1] == 0:
                base = candidata
                break
    if not base:
        problemas.append("Commits: no se encontró rama base (main/master); indicar --base.")
        mensajes = []
    else:
        salida, _ = git(raiz, "log", f"{base}..HEAD", "--format=%h%x09%s")
        mensajes = [l.split("\t", 1) for l in salida.splitlines() if l]
    for h, asunto in mensajes:
        if not PATRON.match(asunto):
            problemas.append(f"Commit {h}: «{asunto[:60]}» no cumple tipo(ámbito): descripción.")
            continue
        descripcion = asunto.split(": ", 1)[1]
        if len(asunto) > 72:
            problemas.append(f"Commit {h}: asunto de {len(asunto)} caracteres (máx. 72).")
        if descripcion.endswith("."):
            problemas.append(f"Commit {h}: la descripción no debe terminar con punto.")
        if descripcion[0].isupper():
            problemas.append(f"Commit {h}: la descripción debe empezar en minúscula.")
    if problemas:
        print(f"Commits: {len(problemas)} problemas ({len(mensajes)} commits revisados en {rama}).")
        for p in problemas:
            print(f"  {p}")
        sys.exit(1)
    print(f"Commits: {len(mensajes)} commits válidos en la rama {rama}.")


if __name__ == "__main__":
    main()
