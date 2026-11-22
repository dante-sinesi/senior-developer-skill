"""CI local: cuando la CI de GitHub no está disponible (sin minutos), el usuario activa `/ci-modo local` y el guardia de fusión acepta la verificación local del commit. Con un `gh` simulado."""
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
GIT = RAIZ / "skills" / "senior-git" / "scripts"
SENIOR = RAIZ / "skills" / "senior" / "scripts"
sys.path.insert(0, str(GIT))
sys.path.insert(0, str(SENIOR))
import modo_hooks as mh  # noqa: E402

P = RAIZ / ".temporal" / "proy-ci-local"
mal = 0
FLUJO = "on:\n  pull_request:\njobs:\n  t:\n    steps:\n      - run: pytest\n"


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def git(c, *a):
    return subprocess.run(["git", *a], cwd=c, capture_output=True, text=True).stdout.strip()


def proyecto(nombre):
    c = P / nombre
    (c / ".github" / "workflows").mkdir(parents=True)
    (c / ".github" / "workflows" / "ci.yml").write_text(FLUJO, encoding="utf-8")
    (c / "_gh").mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=c, check=True)
    subprocess.run(["git", "config", "user.name", "prueba"], cwd=c, check=True)
    subprocess.run(["git", "config", "user.email", "p@x.test"], cwd=c, check=True)
    (c / ".gitignore").write_text("_gh/\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=c, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=c, check=True)
    return c


def entorno(c, modo="rojo", extra=None):
    return {**os.environ, "CLAUDE_PROJECT_DIR": str(c), "SENIOR_GH": json.dumps([sys.executable, str(RAIZ / "tests" / "gh_falso.py")]), "GH_FALSO_DIR": str(c / "_gh"),
            "GH_FALSO_CHECKS": modo, **(extra or {})}


def hook(c, comando, modo="rojo", extra=None):
    entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(c)})
    r = subprocess.run([sys.executable, str(GIT / "hook_fusion_ci.py")], input=entrada, capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno(c, modo, extra))
    return r.stdout + r.stderr


def bloquea(s):
    try:
        return json.loads(s)["hookSpecificOutput"]["permissionDecision"] == "deny"
    except (ValueError, KeyError):
        return False


def ci_local(c, extra=None):
    r = subprocess.run([sys.executable, str(GIT / "ci.py"), "local", "--raiz", str(c)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno(c, extra=extra))
    return r.returncode, r.stdout + r.stderr


def chat(c, texto):
    r = subprocess.run([sys.executable, str(SENIOR / "hook_permisos_chat.py")], input=json.dumps({"prompt": texto, "cwd": str(c)}), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=entorno(c))
    return r.stdout


if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)
PASA = f'"{sys.executable}" -c "import sys; sys.exit(0)"'
FALLA = f'"{sys.executable}" -c "import sys; sys.exit(1)"'

# ---- el comando de chat (solo del usuario)
c = proyecto("a")
chequear("por defecto el modo es estricto", mh.cargar(c)["ci_modo"] == "estricto")
chequear("/ci-modo local fija el modo y el comando de pruebas", "Modo de CI: local" in chat(c, f"/ci-modo local {PASA}") and mh.cargar(c)["ci_modo"] == "local" and mh.cargar(c)["ci_comando"] == PASA)
chequear("/permisos muestra el modo de CI", "CI: modo local" in chat(c, "/permisos"))
chequear("un modo inválido se rechaza y no cambia nada", "Modos de CI válidos" in chat(c, "/ci-modo raro") and mh.cargar(c)["ci_modo"] == "local")
chequear("/ci-modo estricto vuelve a mandar la CI de GitHub", "Modo de CI: estricto" in chat(c, "/ci-modo estricto") and mh.cargar(c)["ci_modo"] == "estricto")

# ---- sin indicar comando: se usa el detectado, y el chat dice cuál
import ci  # noqa: E402
cr = proyecto("corredor")
(cr / "tests").mkdir()
(cr / "tests" / "correr_todo.py").write_text("print('ok')" + chr(10), encoding="utf-8")
(cr / "tests" / "probar_a.py").write_text("print('a')" + chr(10), encoding="utf-8")
chequear("el corredor propio del proyecto (tests/correr_todo.py) manda sobre el genérico", ci.detectar(cr) == [("python", {"instalar": None, "probar": "python tests/correr_todo.py"})], ci.detectar(cr))
r = chat(cr, "/ci-modo local")
chequear("/ci-modo local sin comando funciona: el chat dice qué comando detectó", "python tests/correr_todo.py" in r and mh.cargar(cr)["ci_modo"] == "local" and mh.cargar(cr)["ci_comando"] == "", r)
vacio = proyecto("vacio")
r = chat(vacio, "/ci-modo local")
chequear("si no detecta pruebas, lo dice y pide el comando (el modo queda activado)", "no se detectaron pruebas" in r and "/ci-modo local <comando de pruebas>" in r and mh.cargar(vacio)["ci_modo"] == "local", r)

# ---- /ci-modo aparece al escribir «/» con los dos modos a la vista
sk = (RAIZ / "skills" / "ci-modo" / "SKILL.md").read_text(encoding="utf-8")
chequear("la skill ci-modo muestra los dos modos en la pista del menú, solo la invoca el usuario y no depende de Claude para cambiar nada",
         re.search(r'(?m)^argument-hint:\s*"local \[comando de pruebas\] \| estricto"', sk) and "disable-model-invocation: true" in sk and "no esta skill" in sk, sk[:200])
chequear("figura en el README", "`ci-modo`" in (RAIZ / "README.md").read_text(encoding="utf-8"))

# ---- en modo estricto nada cambia
rc, s = ci_local(c)
chequear("en modo estricto el guardia sigue bloqueando con rojo, aunque haya una verificación local", ci_local(c)[0] == 0 and bloquea(hook(c, "gh pr merge 12")))
chequear("y el mensaje enseña cómo dejar de autorizar de a uno", "/ci-modo local" in hook(c, "gh pr merge 12"))

# ---- ci.py local
c2 = proyecto("local")
chat(c2, f"/ci-modo local {PASA}")
rc, s = ci_local(c2)
chequear("ci.py local corre el comando fijado por el usuario y anota el commit verificado", rc == 0 and "verificado" in s and mh.hay_verificacion_local(c2, git(c2, "rev-parse", "HEAD")), s)
c3 = proyecto("falla")
chat(c3, f"/ci-modo local {FALLA}")
rc, s = ci_local(c3)
chequear("si las pruebas fallan no anota nada y sale con 1", rc == 1 and "FALLARON" in s and mh.cargar(c3)["ci_local"] == [], s)
(c2 / "nuevo.txt").write_text("sin commitear", encoding="utf-8")
rc, s = ci_local(c2)
chequear("con el árbol sucio no corre ni anota: lo probado no sería el commit", rc == 1 and "sin commitear" in s, s)
c4 = proyecto("sin-comando")
rc, s = ci_local(c4)
chequear("sin comando y sin pruebas detectables lo dice (el usuario lo fija en el chat)", rc == 2 and "/ci-modo local" in s, s)
c5 = proyecto("cambia")
chat(c5, f'/ci-modo local "{sys.executable}" -c "import subprocess; subprocess.run([\'git\', \'commit\', \'--allow-empty\', \'-m\', \'x\'])"')
rc, s = ci_local(c5)
chequear("si el commit cambia mientras corren las pruebas, no anota", rc == 1 and "cambió" in s and mh.cargar(c5)["ci_local"] == [], s)
chequear("quien corre ci.py local no elige el comando: no hay opción para cambiarlo", "--comando" not in (GIT / "ci.py").read_text(encoding="utf-8"))

# ---- el guardia en modo local
c6 = proyecto("guardia")
chat(c6, f"/ci-modo local {PASA}")
s = hook(c6, "gh pr merge 12", "rojo")
chequear("en modo local, con rojo y sin verificación del commit: bloquea y manda a correr ci.py local", bloquea(s) and "modo de CI local" in s and "ci.py" in s and "local" in s, s)
chequear("ese mensaje avisa que puede tardar y no manda a parar ni a preguntar", "puede tardar" in s and not re.search(r"(?i)propon[ée]|pedile|avisale|contale|preguntale|esperá|detenete|pará\b|\bparar\b", s), s)
ci_local(c6)
chequear("con la verificación local del commit, la fusión pasa aunque haya rojo", hook(c6, "gh pr merge 12", "rojo").strip() == "")
chequear("también con chequeos pendientes", hook(c6, "gh pr merge 12", "pendiente").strip() == "")
chequear("si el Pull Request tiene otro commit (por ejemplo, uno nuevo sin verificar), vuelve a bloquear", bloquea(hook(c6, "gh pr merge 12", "rojo", extra={"GH_FALSO_SHA": "0" * 40})))
chequear("si no se puede saber el commit del Pull Request, deja pasar como con las demás fallas internas", hook(c6, "gh pr merge 12", "rojo", extra={"SENIOR_GH": json.dumps([sys.executable, str(P / "no_existe.py")])}).strip() == "")
chequear("con GitHub en verde pasa siempre (también sin verificación)", hook(proyecto("verde"), "gh pr merge 12", "verde").strip() == "")
git(c6, "commit", "--allow-empty", "-q", "-m", "nuevo")
chequear("un commit nuevo local deja de estar verificado", bloquea(hook(c6, "gh pr merge 12", "rojo")))
chequear("/permitir-fusion sigue valiendo como autorización de una vez", "Autorizada" in chat(c6, "/permitir-fusion 12") and hook(c6, "gh pr merge 12", "rojo").strip() == "")

# ---- el flujo de CI recortado: se comprueba por texto (sin minutos no se puede correr)
wf = (RAIZ / ".github" / "workflows" / "pruebas.yml").read_text(encoding="utf-8")
chequear("el flujo no corre al fusionar a la rama principal (sin push)", not re.search(r"(?m)^\s*push\s*:", wf) and "pull_request:" in wf)
chequear("en cada Pull Request corre un solo trabajo: Python 3.12; la semanal suma 3.10", "fromJSON('[\"3.12\"]')" in wf and "fromJSON('[\"3.10\", \"3.12\"]')" in wf and "github.event_name == 'pull_request'" in wf)
chequear("hay corrida semanal y manual", "schedule:" in wf and "cron:" in wf and "workflow_dispatch:" in wf)
chequear("una corrida nueva del mismo PR cancela la vieja, con un grupo por referencia y sin cancelar las semanales", "group: ${{ github.workflow }}-${{ github.ref }}" in wf and "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in wf)
chequear("sin filtros de rutas: un Pull Request sin chequeos contaría como pendiente", "paths" not in wf)

# ---- explicado
ref = (GIT.parent / "references" / "ci.md").read_text(encoding="utf-8")
chequear("la referencia explica el modo local", all(x in ref.lower() for x in ("/ci-modo local", "ci.py local", "árbol sin cambios", "reemplaza")))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
