"""El despachador decide igual que los hooks sueltos, más rápido (un proceso en lugar de cinco), y la guardia migra los hooks sueltos."""
import json
import os
import shutil
import stat
import statistics
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = RAIZ / "skills" / "senior" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(RAIZ / "skills" / "senior-git" / "scripts"))
import guardia_autoria  # noqa: E402
import hook_senior  # noqa: E402

P = RAIZ / ".temporal" / "proy-despachador"
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
(P / ".gitignore").write_text("local/\n.env\n", encoding="utf-8")
(P / ".env").write_text("A=1\n", encoding="utf-8")
ENV = {**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(P), "SENIOR_LECTURA_DIRECTA": ""}
GT = chr(62)
CLAVE = "AKIA" + "QWERTYUIOPASDFGH"[:16]


def correr(script, evento):
    r = subprocess.run([sys.executable, str(script)], input=json.dumps(evento), capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P, env=ENV)
    if "Traceback" in r.stderr:
        raise RuntimeError(r.stderr[-500:])
    decision = "pasa"
    if r.returncode == 2:
        decision = "bloquea"
    elif r.stdout.strip():
        decision = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]
    return decision, r.returncode, r.stdout, r.stderr


def sueltos(evento):
    """Lo que decidirían los hooks de uno en uno: el primero que bloquea gana; si no, el primero que pregunta."""
    pregunta = None
    for skill, archivo, herramientas in hook_senior.HOOKS:
        if evento["tool_name"] not in herramientas:
            continue
        d, rc, out, err = correr(RAIZ / "skills" / skill / "scripts" / archivo, evento)
        if d in ("bloquea", "deny"):
            return "bloquea" if d == "bloquea" else "deny", out, err
        if d == "ask" and pregunta is None:
            pregunta = (d, out, err)
    return pregunta or ("pasa", "", "")


def evento(herramienta, **entrada):
    return {"tool_name": herramienta, "tool_input": entrada, "cwd": str(P), "hook_event_name": "PreToolUse"}


casos = [
    ("escribir una clave en el código", evento("Write", file_path="app.py", content="K = '" + CLAVE + "'\n")),
    ("escribir normal", evento("Write", file_path="app.py", content="print('hola')\n")),
    ("escribir fuera del proyecto", evento("Write", file_path="C:/Users/Public/x.txt", content="a")),
    ("redirección fuera del proyecto", evento("Bash", command="echo a " + GT + " /tmp/x.txt")),
    ("editar .env", evento("Write", file_path=".env", content="B=2\n")),
    ("leer .env", evento("Read", file_path=".env")),
    ("grep en .env", evento("Grep", pattern="A", path=".env")),
    ("cat .env", evento("Bash", command="cat .env")),
    ("git add -f", evento("Bash", command="git add -f build/x.js")),
    ("commit con Co-Authored-By", evento("Bash", command="git commit -m \"feat: algo\n\nCo-Authored-By: Alguien <a@b.test>\"")),
    ("commit normal", evento("Bash", command="git commit -m \"feat: algo\"")),
    ("ls", evento("Bash", command="ls")),
    ("leer un archivo común", evento("Read", file_path="app.py")),
    ("leer un PDF sin convertir", evento("Read", file_path="manual.pdf")),
    ("una herramienta que no controla nadie", evento("WebFetch", url="https://example.com")),
    ("NotebookEdit con una clave", evento("NotebookEdit", notebook_path="n.ipynb", new_source="K = '" + CLAVE + "'")),
]
(P / "manual.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 100)

# 1. mismas decisiones que los hooks de uno en uno
for desc, ev in casos:
    uno, _, _ = sueltos(ev)
    todos, rc, out, err = correr(SCRIPTS / "hook_senior.py", ev)
    chequear(f"mismo resultado que los hooks sueltos: {desc} ({todos})", (uno == todos) or (uno in ("bloquea", "deny") and todos in ("bloquea", "deny")), (uno, todos, out, err))
bloquean = [d for d, ev in casos if correr(SCRIPTS / "hook_senior.py", ev)[0] != "pasa"]
chequear("y bloquea lo que tiene que bloquear (al menos 8 de los 16 casos)", len(bloquean) >= 8, bloquean)

# 2. salida de autoría (código 2 con el mensaje por stderr) y de los demás (JSON)
d, rc, out, err = correr(SCRIPTS / "hook_senior.py", casos[9][1])
chequear("un bloqueo de autoría sale con código 2 y su mensaje", rc == 2 and "autoría" in err, (rc, err))
d, rc, out, err = correr(SCRIPTS / "hook_senior.py", casos[0][1])
chequear("un bloqueo de secretos sale como decisión deny con el motivo", d == "deny" and "secretos" in out and CLAVE not in out, out)

# 3. un hook que falla por dentro no frena nada; depurando, se ve
base = {k: v for k, v in ENV.items() if k != "SENIOR_HOOK_DEPURAR"}
r = subprocess.run([sys.executable, str(SCRIPTS / "hook_senior.py")], input="[]", capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P, env=base)
chequear("una entrada rota deja pasar sin ruido", r.returncode == 0 and not r.stdout.strip() and "Traceback" not in r.stderr, r.stderr[-200:])
r = subprocess.run([sys.executable, str(SCRIPTS / "hook_senior.py")], input="[]", capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P, env=ENV)
chequear("con SENIOR_HOOK_DEPURAR=1 se ve el error", r.returncode != 0 and "Traceback" in r.stderr, r.stderr[-200:])

# 4. más rápido: un proceso en lugar de cinco
caso = casos[3][1]
con_todos, un_proceso = [], []
for _ in range(5):
    t = time.perf_counter()
    for skill, archivo, herramientas in hook_senior.HOOKS:
        if caso["tool_name"] in herramientas:
            correr(RAIZ / "skills" / skill / "scripts" / archivo, caso)
    con_todos.append(time.perf_counter() - t)
    t = time.perf_counter()
    correr(SCRIPTS / "hook_senior.py", caso)
    un_proceso.append(time.perf_counter() - t)
sueltos_s, junto_s = statistics.median(con_todos), statistics.median(un_proceso)
print(f"     (una llamada de Bash: {sueltos_s * 1000:.0f} ms con los hooks sueltos, {junto_s * 1000:.0f} ms con el despachador)")
chequear("el despachador tarda menos del 60 % de los hooks sueltos", junto_s < 0.6 * sueltos_s, (sueltos_s, junto_s))

# 5. la guardia registra el despachador y migra los hooks sueltos sin tocar lo demás
FALSO = P / "casa"
(FALSO / ".claude").mkdir(parents=True)
viejos = [{"matcher": "Bash|PowerShell", "hooks": [{"type": "command", "command": 'python "C:/x/hook_autoria_claude.py"'}]},
          {"matcher": "Read|Bash", "hooks": [{"type": "command", "command": 'python "C:/x/hook_lectura_externa.py"'}, {"type": "command", "command": "otro"}]},
          {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": 'python "C:/x/hook_archivos_protegidos.py"'}]}]
(FALSO / ".claude" / "settings.json").write_text(json.dumps({"model": "x", "hooks": {"PreToolUse": viejos}}), encoding="utf-8")
env_casa = {**os.environ, "USERPROFILE": str(FALSO), "HOME": str(FALSO)}
codigo = ("import sys, json; sys.path.insert(0, r'" + str(RAIZ / "skills" / "senior-git" / "scripts") + "'); import guardia_autoria as g; "
          "print(json.dumps(g.asegurar_claude(%s)[0], ensure_ascii=False))")
r = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo % "True"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_casa)
chequear("--solo-verificar avisa que hay hooks sueltos para migrar y no escribe", "FALTA migrar 3 hooks sueltos" in r.stdout
         and "hook_autoria_claude.py" in (FALSO / ".claude" / "settings.json").read_text(encoding="utf-8"), r.stdout + r.stderr)
r = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo % "False"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_casa)
ajustes = json.loads((FALSO / ".claude" / "settings.json").read_text(encoding="utf-8"))
comandos = [h["command"] for g_ in ajustes["hooks"]["PreToolUse"] for h in g_["hooks"]]
chequear("asegurar saca los tres sueltos y deja el ajeno", "otro" in comandos and not any(s in c for c in comandos for s in guardia_autoria.HOOKS_SUELTOS), comandos)
chequear("y registra el despachador una sola vez, con todas las herramientas", sum("hook_senior.py" in c for c in comandos) == 1
         and all(t in json.dumps(ajustes["hooks"]["PreToolUse"]) for t in hook_senior.HERRAMIENTAS), comandos)
chequear("sin dejar grupos vacíos y conservando los otros ajustes", all(g_.get("hooks") for g_ in ajustes["hooks"]["PreToolUse"]) and ajustes["model"] == "x")
r = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo % "False"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_casa)
ajustes2 = json.loads((FALSO / ".claude" / "settings.json").read_text(encoding="utf-8"))
chequear("repetir no duplica nada", ajustes2 == ajustes and "saqué" not in r.stdout, r.stdout)

rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el README explica el despachador", "hook_senior.py" in rd and "un solo proceso" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
