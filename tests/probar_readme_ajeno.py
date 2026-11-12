import io
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
import verificar  # noqa: E402

mal = 0


def chequear(nombre, cond):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre)


ca = verificar.contenido_ajeno
chequear("el texto que molestó se detecta", len(ca("viven fuera del repositorio: conviene copiarlos antes de reinstalar el sistema.")) == 2)
chequear("sección 'Lo que no está en este repositorio'", bool(ca("### Lo que no está en este repositorio\n\nalgo")))
chequear("memoria personal de Claude", bool(ca("La memoria de Claude Code guarda cosas")))
chequear("referencia a una conversación", bool(ca("Como te comenté, esto sirve")))
chequear("README normal no da señales", ca("# App\n\nInstalar con `pip install`. Ver ~/.claude/skills.\n") == [])
chequear("lo que está en un bloque de código se ignora", ca("```\nmemoria de claude\n```\ntexto") == [])

# El README real del repositorio no debe dar señales
chequear("el README del repositorio está limpio", ca((RAIZ / "README.md").read_text(encoding="utf-8")) == [])

# integración: chequeo_readme lo informa
p = RAIZ / ".temporal" / "proy-readme"
p.mkdir(parents=True, exist_ok=True)
(p / "README.md").write_text("# X\n\nQué es.\n\n### Lo que no está en este repositorio\n\nCopiarlos antes de reinstalar el sistema.\n", encoding="utf-8")


class A:
    base = "HEAD"


lineas, ok = verificar.chequeo_readme(p, A())
chequear("chequeo_readme avisa y falla", (not ok) and "no es del proyecto" in lineas[0])
print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
