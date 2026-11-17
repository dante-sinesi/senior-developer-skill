"""El guardia de fusión con CI (hook_fusion_ci.py): no se fusiona un Pull Request con chequeos sin verde, salvo que el usuario lo autorice desde el chat. Con un `gh` simulado."""
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
import hook_fusion_ci as hf  # noqa: E402
import modo_hooks as mh  # noqa: E402

P = RAIZ / ".temporal" / "proy-fusion"
mal = 0
FLUJO = "on:\n  pull_request:\njobs:\n  t:\n    steps:\n      - run: pytest\n"


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def proyecto(nombre, con_ci=True):
    c = P / nombre
    c.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=c, check=True)
    if con_ci:
        (c / ".github" / "workflows").mkdir(parents=True)
        (c / ".github" / "workflows" / "ci.yml").write_text(FLUJO, encoding="utf-8")
    (c / "_gh").mkdir()
    return c


def entorno(c, modo="verde", extra=None):
    return {**os.environ, "CLAUDE_PROJECT_DIR": str(c), "SENIOR_GH": json.dumps([sys.executable, str(RAIZ / "tests" / "gh_falso.py")]), "GH_FALSO_DIR": str(c / "_gh"),
            "GH_FALSO_CHECKS": modo, **(extra or {})}


def hook(c, comando, modo="verde", herramienta="Bash", script=None, extra=None):
    """(código, salida) del hook (suelto o por el despachador) para un comando."""
    entrada = json.dumps({"tool_name": herramienta, "tool_input": {"command": comando}, "cwd": str(c)})
    r = subprocess.run([sys.executable, str(script or GIT / "hook_fusion_ci.py")], input=entrada, capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno(c, modo, extra))
    return r.returncode, r.stdout + r.stderr


def bloquea(salida):
    try:
        return json.loads(salida)["hookSpecificOutput"]["permissionDecision"] == "deny"
    except (ValueError, KeyError):
        return False


def chat(c, texto):
    entrada = json.dumps({"prompt": texto, "cwd": str(c)})
    r = subprocess.run([sys.executable, str(SENIOR / "hook_permisos_chat.py")], input=entrada, capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno(c))
    return r.stdout


if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)

# ---- reconocer las fusiones de un comando
chequear("reconoce `gh pr merge 12 --squash`", hf.fusiones_de("gh pr merge 12 --squash --delete-branch") == [{"objetivo": "12", "repo": None, "auto": False}])
chequear("reconoce gh.exe, una URL y --auto", hf.fusiones_de("gh.exe pr merge https://github.com/o/r/pull/12 --auto")[0] == {"objetivo": "https://github.com/o/r/pull/12", "repo": None, "auto": True})
chequear("reconoce -R antes o después y una rama", hf.fusiones_de("gh -R o/r pr merge feat/x")[0] == {"objetivo": "feat/x", "repo": "o/r", "auto": False}
         and hf.fusiones_de("gh pr merge 7 --repo o/r")[0]["repo"] == "o/r")
chequear("sin número es el Pull Request de la rama actual", hf.fusiones_de("gh pr merge --admin")[0]["objetivo"] is None)
chequear("ve cada fusión de un comando compuesto, y no se confunde con el texto de un mensaje", len(hf.fusiones_de("cd x && gh pr merge 12; gh pr merge 13 -b \"cuerpo largo\"")) == 2
         and hf.fusiones_de("git commit -m \"docs: gh pr merge 12\"") == [] and hf.fusiones_de("echo gh pr merge 12") == [] and hf.fusiones_de("git merge main") == [])
chequear("el valor de --body no se toma por el Pull Request", hf.fusiones_de("gh pr merge -b \"mensaje\" 12")[0]["objetivo"] == "12")
chequear("el número sale de un número o de una URL", hf.numero_de("12") == "12" and hf.numero_de("https://github.com/o/r/pull/34") == "34" and hf.numero_de("feat/x") is None and hf.numero_de(None) is None)

# ---- las decisiones
c = proyecto("a")
rc, s = hook(c, "gh pr merge 12 --squash", "rojo")
chequear("con un chequeo en rojo bloquea", rc == 0 and bloquea(s) and "BLOQUEADO por senior (fusión con CI)" in s, s)
chequear("el bloqueo dice qué falla y cómo se autoriza, y manda a anotar el pendiente y seguir", "FALLA pruebas" in s and "/permitir-fusion 12" in s and "docs/pendientes.md" in s and "seguí con otra tarea" in s, s)
chequear("ningún mensaje del guardia manda a parar, preguntar ni esperar al usuario", not re.search(r"(?i)propon[ée]|pedile|avisale|contale|preguntale|esperá|detenete|pará\b|\bparar\b", s), s)
rc, s = hook(c, "gh pr merge 12", "pendiente")
chequear("con chequeos pendientes bloquea", bloquea(s), s)
rc, s = hook(c, "gh pr merge 12", "verde")
chequear("con todo en verde deja pasar", rc == 0 and s.strip() == "", s)
rc, s = hook(c, "gh pr merge 12", "ninguno")
chequear("sin chequeos pero con flujos de Pull Request (todavía no arrancaron): bloquea", bloquea(s), s)
c_sin = proyecto("sin-ci", con_ci=False)
rc, s = hook(c_sin, "gh pr merge 12", "ninguno")
chequear("sin chequeos y sin flujos de CI: pasa", rc == 0 and s.strip() == "", s)
rc, s = hook(c, "gh pr merge 12", "rojo", extra={"SENIOR_GH": json.dumps([sys.executable, str(P / "no_existe.py")])})
chequear("si gh falla y no se puede saber, deja pasar (una falla de red no traba todas las fusiones)", rc == 0 and s.strip() == "", s)
rc, s = hook(c, "gh pr merge 12 --auto", "pendiente")
chequear("con --auto y pendientes pasa: GitHub fusiona solo cuando pasan los chequeos", rc == 0 and s.strip() == "", s)
chequear("con --auto y un chequeo en rojo bloquea", bloquea(hook(c, "gh pr merge 12 --auto", "rojo")[1]))
chequear("con --admin y un chequeo en rojo bloquea", bloquea(hook(c, "gh pr merge 12 --admin", "rojo")[1]))
chequear("en un comando compuesto, si alguna fusión no pasa se bloquea", bloquea(hook(c, "echo ok && gh pr merge 12 && gh pr merge 13", "rojo")[1]))
chequear("PowerShell también", bloquea(hook(c, "gh pr merge 12", "rojo", herramienta="PowerShell")[1]))
chequear("otra herramienta o un `git merge` pasan sin mirar nada", hook(c, "gh pr merge 12", "rojo", herramienta="Read")[1].strip() == "" and hook(c, "git merge main", "rojo")[1].strip() == "")
chequear("queda registrado en los bloqueos del proyecto", any(b["hook"] == "fusión con CI" for b in mh.cargar(c)["bloqueos"]))

# ---- la autorización del usuario: una sola vez y por Pull Request
c2 = proyecto("autoriza")
chequear("solo el usuario autoriza: /permitir-fusion 12 queda en la configuración", "Autorizada una vez" in chat(c2, "/permitir-fusion 12") and mh.cargar(c2)["fusiones"] == ["12"])
rc, s = hook(c2, "gh pr merge 13", "rojo")
chequear("la autorización de un número no sirve para otro Pull Request", bloquea(s), s)
rc, s = hook(c2, "gh pr merge 12", "rojo")
chequear("con la autorización la fusión pasa aunque haya rojo", rc == 0 and s.strip() == "", s)
chequear("y se gastó: la segunda vez vuelve a bloquear", bloquea(hook(c2, "gh pr merge 12", "rojo")[1]) and mh.cargar(c2)["fusiones"] == [])
chat(c2, "/permitir-fusion 12")
rc, s = hook(c2, "gh pr merge 12", "verde")
chequear("un Pull Request en verde no gasta la autorización", s.strip() == "" and mh.cargar(c2)["fusiones"] == ["12"])
c3 = proyecto("actual")
chat(c3, "/permitir-fusion")
chequear("sin número vale para el Pull Request de la rama actual", hook(c3, "gh pr merge --squash", "rojo")[1].strip() == "" and mh.cargar(c3)["fusiones"] == [])
chequear("un número que no es número se rechaza", "Falta el número" in chat(c3, "/permitir-fusion doce") and mh.cargar(c3)["fusiones"] == [])
chequear("/permisos cuenta las fusiones autorizadas", "Fusiones autorizadas una vez" in (chat(c2, "/permitir-fusion 5") + chat(c2, "/permisos")))

# ---- Claude no puede autorizarse solo: editar la configuración está bloqueado
cfg = c2 / ".git" / "senior-hooks.json"
entrada = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(cfg), "content": "{\"fusiones\": [\"1\"]}"}, "cwd": str(c2)})
r = subprocess.run([sys.executable, str(SENIOR / "hook_senior.py")], input=entrada, capture_output=True, text=True, encoding="utf-8", env=entorno(c2))
chequear("escribir la configuración con una herramienta de Claude se bloquea (también el campo nuevo)", bloquea(r.stdout) or r.returncode == 2, r.stdout + r.stderr)

# ---- modo preguntar y despachador
c4 = proyecto("pregunta")
d = mh.cargar(c4)
d["modo"] = "preguntar"
mh.guardar(c4, d)
rc, s = hook(c4, "gh pr merge 12", "rojo")
chequear("en modo preguntar pregunta al usuario en la interfaz", json.loads(s)["hookSpecificOutput"]["permissionDecision"] == "ask" and "¿Autorizás esta fusión?" in s, s)
c5 = proyecto("despachador")
rc, s = hook(c5, "gh pr merge 12", "rojo", script=SENIOR / "hook_senior.py")
chequear("el despachador corre este control con los demás", bloquea(s) and "fusión con CI" in s, s)
chequear("el despachador lo declara", "hook_fusion_ci.py" in (SENIOR / "hook_senior.py").read_text(encoding="utf-8"))

# ---- explicado
sk = (GIT.parent / "SKILL.md").read_text(encoding="utf-8")
chequear("senior-git explica el guardia y cómo se autoriza", "/permitir-fusion" in sk and "hook_fusion_ci" in sk, sk[:80])

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
