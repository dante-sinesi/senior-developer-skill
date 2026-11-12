import io
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "senior-docs" / "scripts" / "consultas.py"
sys.path.insert(0, str(RAIZ / "skills" / "senior-docs" / "scripts"))
import consultas  # noqa: E402

P = RAIZ / ".temporal" / "proy-intencion"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def correr(*args):
    p = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


# 1. qué cuenta como confirmación
cf = consultas.es_confirmacion
NO = ["Dale, lo que te parezca", "no sé", "decidí vos", "como quieras", "me da igual", "mmm puede ser", "Sí, pero sin lo del plazo",
      "", "   ", "supongo que sí", "¿cómo era lo del plazo?", "más o menos", "lo que sea", "Sí, y además quiero que los clientes puedan reservar desde el celular y pagar con tarjeta"]
SI = ["sí", "Sí.", "ok", "OK!", "Correcto", "sí, exacto", "Perfecto, así es", "Confirmo", "dale", "está bien"]
for r in NO:
    chequear(f"no confirma: «{r}»", cf(r)[0] is False, cf(r))
for r in SI:
    chequear(f"confirma: «{r}»", cf(r)[0] is True, cf(r))

# 2. la orden de línea de comandos devuelve el código
chequear("confirmar devuelve 1 ante «dale, lo que te parezca»", correr("confirmar", "dale, lo que te parezca")[0] == 1)
chequear("confirmar devuelve 0 ante «sí»", correr("confirmar", "sí")[0] == 0)

# 3. la intención se crea sin pisar nada y aparece en el estado
if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)
rc, s = correr("intencion", "Agenda de turnos", "--raiz", str(P))
f = P / "docs" / "consultas" / "01-intencion-agenda-de-turnos.md"
chequear("crea docs/consultas/01-intencion-…", rc == 0 and f.exists(), s)
t = f.read_text(encoding="utf-8")
chequear("nace sin confirmar y con las seis secciones", "estado: sin confirmar" in t and all(x in t for x in (
    "## Resultado", "## Quién lo usa", "## Por qué ahora", "## Éxito", "## Restricción", "## Fuera de alcance")), t[:200])
chequear("no queda ninguna marca sin reemplazar", "{{" not in t)
rc, s = correr("intencion", "Agenda de turnos", "--raiz", str(P))
chequear("el siguiente número es 02 y no pisa nada", (P / "docs" / "consultas" / "02-intencion-agenda-de-turnos.md").exists() and f.exists())
rc, s = correr("nueva", "Reservas", "--raiz", str(P))
chequear("una consulta común sigue funcionando (03)", (P / "docs" / "consultas" / "03-reservas.md").exists(), s)
rc, s = correr("estado", "--raiz", str(P))
chequear("estado muestra la intención sin confirmar y la consulta", "intención, sin confirmar" in s and "03-reservas.md" in s, s)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
