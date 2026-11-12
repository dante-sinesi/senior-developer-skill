"""El paquete promete Python 3.8: ningún script usa sintaxis ni funciones de versiones más nuevas."""
import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


# funciones y formas que no existen en 3.8
NUEVO = re.compile(r"\.removesuffix\(|\.removeprefix\(|\bmath\.lcm\(|\bzip\([^)]*strict=|:\s*(?:list|dict|set|tuple)\[|->\s*(?:list|dict|set|tuple)\[|:\s*\w+\s*\|\s*None|\bmatch\s+\w+:|\.is_relative_to\(")
archivos = sorted((RAIZ / "skills").rglob("*.py")) + [RAIZ / "instalar.py"] + sorted((RAIZ / "tests").glob("*.py"))
for f in archivos:
    texto = f.read_text(encoding="utf-8")
    nombre = f.relative_to(RAIZ).as_posix()
    try:
        ast.parse(texto, feature_version=(3, 8))
        sintaxis = True
    except SyntaxError as e:
        sintaxis = False
        detalle = e
    chequear(f"{nombre}: sintaxis de 3.8", sintaxis, "" if sintaxis else detalle)
    # los comentarios y las cadenas que nombran estas formas no cuentan: se mira solo el código
    codigo = "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))
    if f.name != "probar_compatibilidad.py":
        usos = sorted(set(NUEVO.findall(codigo)))
        chequear(f"{nombre}: sin funciones posteriores a 3.8", not usos, usos)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
