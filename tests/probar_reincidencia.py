"""Sesiones largas sin supervisión: un bloqueo repetido se cuenta y se vuelve una orden con la alternativa primero, y NINGÚN mensaje de los hooks
manda a parar, a preguntarle al usuario ni a esperarlo: lo que necesita al usuario se anota en docs/pendientes.md y el trabajo sigue."""
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = RAIZ / "skills" / "senior" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import modo_hooks  # noqa: E402

P = RAIZ / ".temporal" / "proy-reincidencia"
mal = 0
# frases que mandan a hablar con el usuario o a quedarse esperando: no pueden aparecer en ningún mensaje de bloqueo
PROHIBIDAS = re.compile(r"(?i)propon[ée]s?(?:ele|ele|erle|éselo|ele)|proponé(?:le|selo)|\bproponer(?:le|selo)\b|pedile|pedirle|pedí(?:sela|selo)|avisale|avisarle|contale|preguntale|"
                        r"decírselo|esperá\b|esperá a|detenete|pará\b|\bparar\b")


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(P, onerror=_forzar) if P.exists() else None
P.mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=P)


def hook(script, herramienta, **entrada):
    ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(P), "hook_event_name": "PreToolUse"}
    r = subprocess.run([sys.executable, str(script)], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(P)})
    if "Traceback" in r.stderr:
        raise RuntimeError(r.stderr[-500:])
    if r.returncode == 2:
        return r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if r.stdout.strip() else ""


def registro():
    return modo_hooks.cargar(P)["bloqueos"]


# 1. el contador
chequear("la primera vez cuenta 1", modo_hooks.registrar_bloqueo(P, "prueba", "algo") == 1)
chequear("la segunda cuenta 2", modo_hooks.registrar_bloqueo(P, "prueba", "algo") == 2)
chequear("otro detalle empieza de nuevo", modo_hooks.registrar_bloqueo(P, "prueba", "otra cosa") == 1)
chequear("lo registrado tiene veces y fechas", all({"veces", "primera", "ultima"} <= set(b) for b in registro()), registro())
chequear("un registro anterior, sin contadores, se cuenta bien", modo_hooks.registrar_bloqueo(P, "viejo", "x") == 1 and True)

# 2. el mensaje: indicación las dos primeras veces; desde la tercera, orden con la alternativa PRIMERO y sin parar
alt = "escribí en `.temporal/x.txt` y seguí"
m1, m2, m3, m5 = (modo_hooks.razon_de_bloqueo("escritura fuera del proyecto", "se intentó crear /tmp/x", alt, n) for n in (1, 2, 3, 5))
chequear("las dos primeras veces es una explicación con la alternativa", alt in m1 and alt in m2 and "ª vez" not in m1 + m2 and "Hacé esto en su lugar" not in m1 + m2, (m1, m2))
chequear("desde la tercera dice que repetir no sirve, con las veces", all("no va a funcionar por más que lo repitas" in m for m in (m3, m5)) and "3ª vez" in m3 and "5ª vez" in m5, m3)
chequear("la alternativa viene ANTES que el resto en el mensaje firme", m3.index("Hacé esto en su lugar") < m3.index(alt) < m3.index("Seguí con la tarea"), m3)
chequear("manda a seguir sin detenerse ni esperar a nadie", "sin detenerte" in m3 and "sin esperar a nadie" in m3, m3)
chequear("el aviso para el usuario va al registro, no a una conversación", "registrado como reincidente" in m3 and "avis" not in m3.lower(), m3)

# 3. sesión con un modelo que insiste, hook por hook: cinco intentos idénticos
GT = chr(62)
HOOKS = {
    "fuera": (SCRIPTS / "hook_fuera_del_proyecto.py", "escritura fuera del proyecto", "Bash", dict(command="echo a " + GT + " /tmp/salida.txt")),
    "protegidos": (SCRIPTS / "hook_archivos_protegidos.py", "archivos protegidos", "Write", dict(file_path=".env", content="A=1\n")),
    "secretos": (SCRIPTS / "hook_secretos_claude.py", "secretos", "Read", dict(file_path=".env")),
}
mensajes = []
for clave, (script, nombre, herramienta, entrada) in HOOKS.items():
    (P / ".git" / "senior-hooks.json").unlink(missing_ok=True)
    razones = [hook(script, herramienta, **entrada) for _ in range(5)]
    mensajes += razones
    chequear(f"{clave}: las dos primeras no escalan, de la tercera en adelante sí", all("ª vez" not in r for r in razones[:2]) and all("ª vez" in r for r in razones[2:]), razones[2])
    chequear(f"{clave}: el registro tiene un solo renglón con 5 repeticiones", len([b for b in registro() if b["hook"] == nombre]) == 1 and [b for b in registro() if b["hook"] == nombre][0]["veces"] == 5)

# 4. más hooks y mensajes: ninguno manda a hablar con el usuario ni a esperarlo
(P / ".git" / "senior-hooks.json").unlink(missing_ok=True)
(P / "plano.png").write_bytes(b"\x89PNG" + b"0" * 100)
(P / "manual.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 100)
mensajes.append(hook(SCRIPTS / "hook_secretos_claude.py", "Bash", command="git add -f build/x.js"))
mensajes.append(hook(SCRIPTS / "hook_secretos_claude.py", "Bash", command="echo X=1 " + GT + " .env"))
mensajes.append(hook(SCRIPTS / "hook_secretos_claude.py", "Write", file_path="app.py", content="K = '" + "AKIA" + "QWERTYUIOPASDFGH" + "'\n"))
mensajes.append(hook(SCRIPTS / "hook_senior.py", "Read", file_path=".env") if (SCRIPTS / "hook_senior.py").exists() else "")
mensajes = [m for m in mensajes if m]
chequear(f"se juntaron los mensajes de todos los hooks ({len(mensajes)})", len(mensajes) >= 8, len(mensajes))
malos = [(PROHIBIDAS.search(m).group(0), m[:120]) for m in mensajes if PROHIBIDAS.search(m)]
chequear("ningún mensaje de bloqueo manda a proponerle, pedirle, avisarle ni preguntarle al usuario, ni a parar o esperar", not malos, malos[:3])
chequear("todo lo que necesita al usuario se anota en docs/pendientes.md y se sigue", all("pendientes.md" in m for m in mensajes if "/permitir" in m or "aprobaci" in m), [m[:100] for m in mensajes if ("/permitir" in m or "aprobaci" in m) and "pendientes.md" not in m][:2])

# 5. la lectura de .env se puede completar igual (con los nombres) y el resumen para el usuario no interrumpe
m = hook(SCRIPTS / "hook_secretos_claude.py", "Read", file_path=".env")
chequear("al leer .env ofrece completar la tarea con los nombres y `<definido en .env>`", "estructura" in m and "<definido en .env>" in m and "completala igual" in m, m)
for _ in range(3):
    modo_hooks.registrar_bloqueo(P, "secretos", "se intentó leer .env")
r = subprocess.run([sys.executable, str(SCRIPTS / "permisos_hooks.py"), "bloqueos", "--raiz", str(P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
chequear("permisos_hooks.py bloqueos muestra las veces y marca lo que reincide", "×" in r.stdout and "reincide" in r.stdout, r.stdout)
cs = (RAIZ / "skills" / "cerrar-sesion" / "SKILL.md").read_text(encoding="utf-8")
chequear("/cerrar-sesion lo cuenta como aviso al cerrar y aclara que no interrumpe", "reincide" in cs and "no interrumpe el trabajo" in cs)
rd = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("el README explica que los mensajes no mandan a parar y que lo pendiente va a docs/pendientes.md", "sin supervisión" in rd and "nunca manda a parar" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
