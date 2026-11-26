#!/usr/bin/env python3
"""El ancla: un bloque marcado en el CLAUDE.md del proyecto con la secuencia mínima. No toca nada fuera del bloque y sin --aplicar no escribe."""
import io
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "senior" / "scripts" / "ancla.py"
P = RAIZ / ".temporal" / "proy-ancla"
INICIO, FIN = "<!-- senior:ancla", "<!-- /senior:ancla -->"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def cli(*args):
    p = subprocess.run([sys.executable, "-I", "-X", "utf8", str(SCRIPT), "--raiz", str(P), *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def leer():
    return (P / "CLAUDE.md").read_bytes()


def preparar(contenido=None):
    shutil.rmtree(P, ignore_errors=True)
    P.mkdir(parents=True)
    if contenido is not None:
        (P / "CLAUDE.md").write_bytes(contenido)


preparar()
rc, s = cli()
chequear("sin --aplicar muestra el bloque y no escribe", rc == 0 and INICIO in s and not (P / "CLAUDE.md").exists(), s[:200])
rc, s = cli("--aplicar")
texto = leer().decode("utf-8") if (P / "CLAUDE.md").exists() else ""
chequear("--aplicar crea CLAUDE.md con el bloque", rc == 0 and INICIO in texto and FIN in texto, s)
chequear("el bloque no pasa de 30 líneas", 0 < len(texto.strip().splitlines()) <= 30, len(texto.strip().splitlines()))
chequear("trae los cinco pasos, el orden de las fuentes y qué decir al delegar",
         all(x in texto for x in ("1. ", "2. ", "3. ", "4. ", "5. ", "docs/ESTADO.md", "inferido del código, por confirmar", "Al delegar", "no aplica")))
antes = leer()
rc, s = cli("--aplicar")
chequear("aplicar dos veces no cambia nada", rc == 0 and leer() == antes and "al día" in s, s)

preparar("# Mío\r\n\r\nRegla propia con eñe.\r\n".encode("utf-8-sig"))
cli("--aplicar")
b = leer()
chequear("conserva lo propio, el BOM y los finales de línea CRLF",
         b.startswith("# Mío\r\n\r\nRegla propia con eñe.\r\n".encode("utf-8-sig")) and b.count(b"\n") == b.count(b"\r\n"), b[:120])

viejo = f"antes\n{INICIO} (viejo) -->\ntexto viejo\n{FIN}\ndespués\n".encode("utf-8")
preparar(viejo)
rc, s = cli()
chequear("sin --aplicar avisa que hay que actualizar y no escribe", leer() == viejo and "actualiz" in s, s)
cli("--aplicar")
t = leer().decode("utf-8")
chequear("actualiza solo el bloque", t.startswith("antes\n" + INICIO) and t.endswith(FIN + "\ndespués\n") and "texto viejo" not in t and t.count(INICIO) == 1, t)

for nombre, roto in (("sin cierre", f"{INICIO} -->\nalgo mío\n"), ("repetido", f"{INICIO} -->\n{FIN}\n{INICIO} -->\n{FIN}\n"), ("al revés", f"{FIN}\nmío\n{INICIO} -->\n")):
    preparar(roto.encode("utf-8"))
    rc, s = cli("--aplicar")
    chequear(f"marcas rotas ({nombre}): no toca el archivo y lo dice", rc == 1 and leer() == roto.encode("utf-8") and "marca" in s, s)

preparar("año\n".encode("latin-1"))
rc, s = cli("--aplicar")
chequear("un CLAUDE.md que no es UTF-8 no se reescribe", rc == 1 and leer() == "año\n".encode("latin-1") and "UTF-8" in s, s)

# el núcleo de senior y el brief de delegación traen la secuencia; la adopción la propone sin escribirla
nucleo = (RAIZ / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8")
chequear("el núcleo de senior trae la secuencia de todo cambio de código", "Todo cambio de código" in nucleo and "docs/ESTADO.md" in nucleo and "no aplica" in nucleo)
brief = (RAIZ / "skills" / "senior" / "references" / "brief-delegacion.md").read_text(encoding="utf-8")
chequear("el brief de delegación pide leer y actualizar la documentación", "docs/ESTADO.md" in brief and "actualizá" in brief)
preparar()
(P / "docs").mkdir()
subprocess.run([sys.executable, "-I", "-X", "utf8", str(RAIZ / "skills" / "adoptar-proyecto" / "scripts" / "plan_adopcion.py"), "--raiz", str(P)], capture_output=True)
p = subprocess.run([sys.executable, "-I", "-X", "utf8", str(RAIZ / "skills" / "adoptar-proyecto" / "scripts" / "plan_adopcion.py"), "--raiz", str(P)], capture_output=True, text=True, encoding="utf-8")
chequear("la adopción propone el ancla", "ancla" in p.stdout.lower() and not (P / "CLAUDE.md").exists(), p.stdout[-400:])
shutil.rmtree(P, ignore_errors=True)
print("\nfallos:", mal)
sys.exit(1 if mal else 0)
