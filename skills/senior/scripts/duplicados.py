#!/usr/bin/env python3
"""Detecta bloques de código repetidos (candidatos a refactor).

Uso:
    python duplicados.py [--raiz .] [--lineas 6] [--minimo 2] [--max 15]

Normaliza cada archivo (quita líneas vacías, comentarios simples y espacios) y
busca ventanas de N líneas consecutivas idénticas en dos o más lugares.
Informa los grupos de mayor a menor tamaño, con las ubicaciones.

Limitaciones: detecta repetición literal (salvo espacios y comentarios de una
línea). No detecta duplicación con nombres cambiados. Los resultados son
CANDIDATOS: decidir si extraer o no es criterio de quien refactoriza (regla de
tres: tolerar dos copias, extraer a la tercera, salvo que sea lógica de negocio
crítica).

Solo biblioteca estándar. Código de salida: 0 sin duplicados, 1 con duplicados.
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".idea",
           ".vscode", "coverage", ".next", "docs"}
EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".kt", ".cs", ".go", ".rs", ".rb", ".c", ".cc",
       ".cpp", ".h", ".hpp", ".swift", ".lua", ".sql", ".css", ".html", ".vue"}
COMENTARIO = re.compile(r"^\s*(//|#|--|\*|/\*|\*/)")
TRIVIAL = re.compile(r"^[\s{}()\[\];,]*$|^\s*(else|end|try|finally|\}\s*else\s*\{?)\s*$")


def normalizar(texto):
    """Devuelve lista de (numero_linea_original, linea_normalizada)."""
    res = []
    for i, l in enumerate(texto.splitlines(), 1):
        s = " ".join(l.split())
        if not s or COMENTARIO.match(s) or TRIVIAL.match(s):
            continue
        res.append((i, s))
    return res


def analizar(raiz, ventana, minimo):
    indice = defaultdict(list)
    for actual, carpetas, nombres in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR]
        for nombre in nombres:
            ruta = Path(actual) / nombre
            if ruta.suffix.lower() not in EXT or nombre.endswith((".min.js", ".min.css")):
                continue
            try:
                lineas = normalizar(ruta.read_text(encoding="utf-8-sig", errors="replace"))
            except OSError:
                continue
            rel = ruta.relative_to(raiz).as_posix()
            for k in range(len(lineas) - ventana + 1):
                trozo = lineas[k:k + ventana]
                clave = "\n".join(t[1] for t in trozo)
                if sum(len(t[1]) for t in trozo) < ventana * 8:
                    continue
                indice[clave].append((rel, trozo[0][0], trozo[-1][0]))
    grupos = []
    for clave, lugares in indice.items():
        distintos = []
        for lugar in lugares:
            # evitar contar ventanas solapadas del mismo archivo como lugares distintos
            if not any(l[0] == lugar[0] and abs(l[1] - lugar[1]) < ventana for l in distintos):
                distintos.append(lugar)
        if len(distintos) >= minimo:
            grupos.append((clave, distintos))
    # fusionar ventanas contiguas del mismo conjunto de archivos para no repetir el mismo bloque
    grupos.sort(key=lambda g: (-len(g[1]), g[1][0]))
    vistos, finales = set(), []
    for clave, lugares in grupos:
        firma = tuple(sorted({l[0] for l in lugares}))
        marca = (firma, lugares[0][0], lugares[0][1] // max(ventana, 1))
        if any(l[0] == v[0] and abs(l[1] - v[1]) < ventana * 3 for l in lugares for v in vistos):
            continue
        vistos.update((l[0], l[1]) for l in lugares)
        finales.append((clave, lugares))
    return finales


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--lineas", type=int, default=6, help="líneas consecutivas mínimas (por defecto 6)")
    ap.add_argument("--minimo", type=int, default=2, help="repeticiones mínimas (por defecto 2)")
    ap.add_argument("--max", type=int, default=15)
    args = ap.parse_args()
    grupos = analizar(Path(args.raiz).resolve(), args.lineas, args.minimo)
    if not grupos:
        print(f"Duplicados: no hay bloques de {args.lineas}+ líneas repetidos.")
        sys.exit(0)
    print(f"Duplicados: {len(grupos)} grupos de bloques repetidos (>= {args.lineas} líneas).")
    for clave, lugares in grupos[:args.max]:
        primera = clave.splitlines()[0][:70]
        print(f"  {len(lugares)} copias de «{primera}…»")
        for rel, ini, fin in lugares[:6]:
            print(f"    {rel}:{ini}-{fin}")
    if len(grupos) > args.max:
        print(f"  … y {len(grupos) - args.max} grupos más.")
    sys.exit(1)


if __name__ == "__main__":
    main()
