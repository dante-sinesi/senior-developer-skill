import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SKILLS = ["senior", "senior-tdd", "senior-git", "senior-seguridad", "refactor"]
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + extra))


for s in SKILLS:
    ruta = RAIZ / "skills" / "senior" / "references" / "refactor.md" if s == "refactor" else RAIZ / "skills" / s / "SKILL.md"
    t = ruta.read_text(encoding="utf-8")
    if s == "senior":
        t += (RAIZ / "skills" / s / "references" / "metodo-completo.md").read_text(encoding="utf-8")  # el núcleo es corto: las excusas viven en la capa completa
    m = re.search(r"^## Excusas frecuentes[^\n]*\n(.*?)(?=^## |\Z)", t, re.M | re.S)
    chequear(f"{s}: tiene la sección", bool(m))
    if not m:
        continue
    filas = [l for l in m.group(1).splitlines() if l.startswith("|") and not l.startswith("|---") and not l.startswith("| Excusa")]
    chequear(f"{s}: entre 4 y 6 filas ({len(filas)})", 4 <= len(filas) <= 6)
    celdas = [[c.strip() for c in f.strip().strip("|").split("|")] for f in filas]
    chequear(f"{s}: cada fila tiene excusa y respuesta", all(len(c) == 2 and c[0] and c[1] for c in celdas))
    chequear(f"{s}: cada excusa va entre comillas", all(c[0].startswith("«") and c[0].endswith("»") for c in celdas))
    chequear(f"{s}: ninguna respuesta pasa de 230 caracteres", all(len(c[1]) <= 230 for c in celdas), str([len(c[1]) for c in celdas]))
    chequear(f"{s}: el archivo sigue bajo las 500 líneas", len(t.splitlines()) < 500)
    # los scripts que nombra existen
    for nombre in set(re.findall(r"`([a-z_]+\.py)", m.group(1))):
        existe = any(RAIZ.glob(f"skills/*/scripts/{nombre}"))
        chequear(f"{s}: el script {nombre} existe", existe)
r = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el README lo menciona", "excusas frecuentes" in r)
print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
