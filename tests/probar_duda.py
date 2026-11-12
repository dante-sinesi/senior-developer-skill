import io
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "senior" / "scripts" / "duda.py"
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
import duda  # noqa: E402

mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def d(*ciclos):
    return duda.decidir([duda.parsear_ciclo(c) for c in ciclos])[0]


# decidir
chequear("sin ciclos: seguir", d() == "seguir")
chequear("ciclo sin hallazgos: parar", d("ninguno") == "parar")
chequear("solo triviales: parar", d("trivial,trivial") == "parar")
chequear("hay accionable: seguir", d("accionable,ruido") == "seguir")
chequear("hay accionable y se corrigió: el ciclo siguiente limpio para", d("accionable", "ninguno") == "parar")
chequear("solo contrato: seguir y aclarar", d("contrato") == "seguir")
chequear("solo compromiso en el primer ciclo: parar documentando", d("compromiso") == "parar")
chequear("solo ruido en el primer ciclo: parar", d("ruido,trivial") == "parar")
chequear("teatro de duda: dos ciclos con compromiso/ruido y ningún accionable", d("compromiso", "ruido") == "escalar")
chequear("no es teatro si el primero tuvo un accionable", d("accionable", "ruido") == "parar")
chequear("no es teatro si el segundo aclara contrato", d("ruido", "contrato") == "seguir")
chequear("tercer ciclo con hallazgos: escalar", d("accionable", "accionable", "accionable") == "escalar")
chequear("tercer ciclo limpio: parar", d("accionable", "accionable", "ninguno") == "parar")
msg = duda.decidir([["compromiso"], ["ruido"]])[1]
chequear("el mensaje del teatro lo nombra", "teatro de duda" in msg, msg)
try:
    duda.parsear_ciclo("accionable,inventada")
    chequear("una clase desconocida da error", False)
except ValueError:
    chequear("una clase desconocida da error", True)

# la orden de línea de comandos y su código de salida
def correr(*args):
    p = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout, p.stderr


rc, out, _ = correr("decidir", "accionable", "ninguno")
chequear("CLI: parar sale con 0", rc == 0 and out.startswith("PARAR"), out)
rc, out, _ = correr("decidir", "compromiso", "ruido")
chequear("CLI: escalar sale con 1", rc == 1 and out.startswith("ESCALAR"), out)
rc, out, err = correr("decidir", "rara")
chequear("CLI: clase desconocida no pasa", rc != 0)

# armar: solo artefacto y contrato, sin la afirmación
T = RAIZ / ".temporal" / "duda-muestra"
T.mkdir(parents=True, exist_ok=True)
(T / "funcion.py").write_text("def total(items):\n    return sum(i.precio for i in items)\n", encoding="utf-8")
(T / "contrato.md").write_text("El total de una lista vacía es 0 y nunca es negativo.\n", encoding="utf-8")
rc, out, err = correr("armar", "--artefacto", str(T / "funcion.py"), "--contrato", str(T / "contrato.md"))
chequear("armar incluye el artefacto y el contrato", "def total(items)" in out and "nunca es negativo" in out, out[:300])
chequear("armar trae la instrucción adversarial", "No resumas ni elogies" in out and "Sin hallazgos" in out)
chequear("armar no trae la afirmación del autor (no la recibe)", "afirmación" not in out.split("ARTEFACTO:")[1])
chequear("sin avisos si es chico y hay contrato", err.strip() == "", err)
rc, out, err = correr("armar", "--artefacto", str(T / "funcion.py"))
chequear("sin contrato avisa", "no hay contrato" in err, err)
rc, out, err = correr("armar", "--artefacto", str(T / "funcion.py"), "--contrato", "algo", "--max-lineas", "1")
chequear("artefacto grande avisa que se divida", "dividirlo" in err, err)
rc, out, err = correr("armar", "--artefacto", "def f(): return 1", "--contrato", "devuelve 1")
chequear("el artefacto también puede ser texto", "def f(): return 1" in out, out[:200])

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
