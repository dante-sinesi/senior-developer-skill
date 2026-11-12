"""docs/revision-completa.md es el documento base de mejora: se vigila que conserve su estructura para poder mantenerlo al día."""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


texto = (RAIZ / "docs" / "revision-completa.md").read_text(encoding="utf-8")
for seccion in ("## Cómo se mantiene", "## Cómo se midió", "## Puntaje por parte, con su mejora", "## Puntos ciegos y cómo resolverlos", "## Historial", "## Cómo seguir creciendo"):
    chequear(f"tiene la sección «{seccion[3:]}»", seccion in texto)


def filas(titulo):
    """Filas (listas de celdas) de la primera tabla que sigue al título."""
    resto = texto.split(titulo, 1)[1]
    tabla = []
    for l in resto.splitlines():
        if l.startswith("|"):
            tabla.append([c.strip() for c in l.strip().strip("|").split("|")])
        elif tabla:
            break
    return tabla[2:]  # sin encabezado ni separador


partes = filas("## Puntaje por parte")
chequear("el puntaje tiene 5 columnas en todas las filas", partes and all(len(f) == 5 for f in partes), [len(f) for f in partes])
chequear("las notas son números", all(re.fullmatch(r"[0-9](,5)?|—.*", f[1]) and re.fullmatch(r"[0-9](,5)?", f[2]) and re.fullmatch(r"[0-9](,5)?", f[4]) for f in partes), [f[:3] for f in partes])
chequear("la nota estimada nunca es menor que la de hoy", all(float(f[4].replace(",", ".")) >= float(f[2].replace(",", ".")) for f in partes))

ciegos = filas("## Puntos ciegos")
chequear("los puntos ciegos tienen 5 columnas", ciegos and all(len(f) == 5 for f in ciegos), [len(f) for f in ciegos])
chequear("están numerados sin saltos", [f[0] for f in ciegos] == [str(i) for i in range(1, len(ciegos) + 1)], [f[0] for f in ciegos])
chequear("cada uno tiene un estado válido", all(f[4].split(" ")[0] in ("Abierto", "En", "Parcial", "Resuelto") for f in ciegos), [f[4] for f in ciegos])

historial = filas("## Historial")
chequear("el historial tiene fecha, cambio y partes afectadas", historial and all(len(f) == 3 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f[0]) for f in historial), historial[:1])
chequear("el historial está en orden cronológico", [f[0] for f in historial] == sorted(f[0] for f in historial))
cm = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
chequear("CLAUDE.md exige mantenerlo en el mismo PR", "docs/revision-completa.md" in cm and "mismo PR" in cm)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
