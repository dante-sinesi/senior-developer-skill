"""Las listas de carpetas que cada script ignora no se desalinean: todas contienen la base común (cada skill va por su cuenta,
sin importar de otra, así que la consistencia se vigila acá en lugar de compartir un módulo)."""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
BASE = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv"}
mal = 0


def conjunto_ignorar(archivo):
    """El conjunto literal asignado a IGNORAR en el nivel superior del script, o None si no lo define."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "IGNORAR" for t in nodo.targets) and isinstance(nodo.value, ast.Set):
            return {e.value for e in nodo.value.elts if isinstance(e, ast.Constant)}
    return None


vistos = 0
for f in sorted((RAIZ / "skills").rglob("*.py")):
    c = conjunto_ignorar(f)
    if c is None:
        continue
    vistos += 1
    falta = BASE - c
    ok = not falta
    mal += 0 if ok else 1
    print(("ok   " if ok else "MAL  ") + f"{f.relative_to(RAIZ).as_posix()}: ignora la base común" + ("" if ok else f"  (le faltan {sorted(falta)})"))
if vistos < 8:
    mal += 1
    print(f"MAL  se esperaban al menos 8 scripts con IGNORAR y hay {vistos}")

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
