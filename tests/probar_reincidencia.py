"""Un mismo bloqueo que se repite se cuenta y, a la tercera vez, el mensaje pasa de indicación a alto (principio 17)."""
import json
import os
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


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(P, onerror=_forzar) if P.exists() else None
P.mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=P)


def hook(script, herramienta, **entrada):
    ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(P), "hook_event_name": "PreToolUse"}
    r = subprocess.run([sys.executable, str(SCRIPTS / script)], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(P)})
    if "Traceback" in r.stderr:
        raise RuntimeError(r.stderr[-500:])
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if r.stdout.strip() else ""


def registro():
    return json.loads((P / ".git" / "senior-hooks.json").read_text(encoding="utf-8"))["bloqueos"]


# 1. el contador
chequear("la primera vez cuenta 1", modo_hooks.registrar_bloqueo(P, "prueba", "algo") == 1)
chequear("la segunda cuenta 2", modo_hooks.registrar_bloqueo(P, "prueba", "algo") == 2)
chequear("otro detalle empieza de nuevo", modo_hooks.registrar_bloqueo(P, "prueba", "otra cosa") == 1)
chequear("el aviso no aparece antes de la tercera", modo_hooks.aviso_de_reincidencia(2) == "" and "ALTO" in modo_hooks.aviso_de_reincidencia(3))
chequear("lo registrado tiene veces y fechas", all({"veces", "primera", "ultima"} <= set(b) for b in registro()), registro())

# 2. una sesión con un modelo que insiste: cada hook, cinco intentos idénticos
GT = chr(62)
casos = (
    ("hook_fuera_del_proyecto.py", "escritura fuera del proyecto", "Bash", dict(command="echo a " + GT + " /tmp/salida.txt")),
    ("hook_archivos_protegidos.py", "archivos protegidos", "Write", dict(file_path=".env", content="A=1\n")),
    ("hook_secretos_claude.py", "secretos", "Read", dict(file_path=".env")),
)
for script, nombre, herramienta, entrada in casos:
    shutil.rmtree(P / ".git" / "senior-hooks.json", onerror=_forzar) if (P / ".git" / "senior-hooks.json").is_dir() else None
    (P / ".git" / "senior-hooks.json").unlink(missing_ok=True)
    razones = [hook(script, herramienta, **entrada) for _ in range(5)]
    chequear(f"{nombre}: los dos primeros intentos son una indicación", "ALTO" not in razones[0] and "ALTO" not in razones[1], razones[1])
    chequear(f"{nombre}: del tercero en adelante es un alto con las veces", all("ALTO" in r for r in razones[2:]) and "3 veces" in razones[2] and "5 veces" in razones[4], razones[2])
    chequear(f"{nombre}: el alto manda a avisar al usuario y a proponer una autorización o una barrera",
             "contale al usuario" in razones[2] and "/permitir" in razones[2] and "principio 17" in razones[2], razones[2])
    b = [x for x in registro() if x["hook"] == nombre]
    chequear(f"{nombre}: el registro tiene un solo renglón con 5 repeticiones", len(b) == 1 and b[0]["veces"] == 5, b)

# 3. lo que reincide se ve al listar los bloqueos
r = subprocess.run([sys.executable, str(SCRIPTS / "permisos_hooks.py"), "bloqueos", "--raiz", str(P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
chequear("permisos_hooks.py bloqueos muestra cuántas veces y marca lo que reincide", "×5" in r.stdout and "reincide" in r.stdout, r.stdout)

# 4. un registro viejo, sin contadores, sigue funcionando
(P / ".git" / "senior-hooks.json").write_text(json.dumps({"modo": "denegar", "bloqueos": [{"hook": "secretos", "detalle": "se intentó leer .env"}]}), encoding="utf-8")
chequear("un registro anterior (sin veces) se cuenta bien", modo_hooks.registrar_bloqueo(P, "secretos", "se intentó leer .env") == 2)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
