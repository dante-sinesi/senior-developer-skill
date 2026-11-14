"""/permisos explica cada regla y /cerrar-sesion resume los bloqueos."""
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

P = RAIZ / ".temporal" / "proy-resumen"
mal = 0


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


def correr(script, *args, entrada=None):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], input=entrada, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(P)})
    return r.returncode, r.stdout + r.stderr


# sin nada registrado
rc, s = correr("permisos_hooks.py", "estado", "--raiz", str(P))
chequear("el estado nombra cada hook, qué frena y cómo se autoriza", all(n in s for n, _, _ in modo_hooks.REGLAS) and s.count("Autorización:") == len(modo_hooks.REGLAS), s)
chequear("el estado dice el modo en palabras", "Modo: denegar" in s and "no interrumpe" in s, s)
chequear("sin permisos ni bloqueos lo dice", "Autorizado de antemano: nada." in s and "Bloqueos: ninguno." in s, s)

# con permisos y bloqueos
modo_hooks.permitir_ruta(P, ".env", "estructurar las variables")
modo_hooks.registrar_bloqueo(P, "escritura fuera del proyecto", "se intentó crear algo fuera del proyecto: /tmp/x")
modo_hooks.registrar_bloqueo(P, "secretos", "se intentó leer .env")
rc, s = correr("permisos_hooks.py", "estado", "--raiz", str(P))
chequear("el estado muestra la ruta autorizada con su motivo y su fecha", ".env" in s and "estructurar las variables" in s and "20" in s.split("Autorizado de antemano:")[1][:200], s)
chequear("el estado resume los bloqueos agrupados por hook", "Bloqueos: 2 distintos." in s and "[escritura fuera del proyecto]" in s and "[secretos]" in s, s)

rc, s = correr("permisos_hooks.py", "resumen", "--raiz", str(P))
chequear("resumen agrupa por hook y propone autorizar de antemano", "[escritura fuera del proyecto]" in s and "[secretos]" in s and "/permitir" in s, s)
chequear("el resumen es un aviso: no manda a parar ni a esperar a nadie", "ALTO" not in s and "No lo reintentes" not in s and "esperar" not in s, s)
rc, s = correr("permisos_hooks.py", "resumen", "--raiz", str(P), "--desde", "2999-01-01 00:00")
chequear("resumen --desde filtra por fecha", "ninguno desde 2999-01-01 00:00" in s, s)

# /permisos en el chat
ev = {"prompt": "/permisos", "cwd": str(P)}
rc, s = correr("hook_permisos_chat.py", entrada=json.dumps(ev))
ctx = json.loads(s)["hookSpecificOutput"]["additionalContext"]
chequear("/permisos le pide a Claude mostrar la explicación completa", "Mostrale al usuario" in ctx and "Qué frena cada hook" in ctx and "Confirmalo en una línea" not in ctx, ctx)
rc, s = correr("hook_permisos_chat.py", entrada=json.dumps({"prompt": "/hooks-hermanos no", "cwd": str(P)}))
ctx = json.loads(s)["hookSpecificOutput"]["additionalContext"]
chequear("los demás comandos siguen pidiendo una línea de confirmación", "Confirmalo en una línea" in ctx, ctx)

# Claude puede leer el resumen pero no limpiar el registro
HOOK = SCRIPTS / "hook_fuera_del_proyecto.py"


def hook(comando):
    ev = {"tool_name": "Bash", "tool_input": {"command": comando}, "cwd": str(P), "hook_event_name": "PreToolUse"}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=P,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(P)})
    return "deniega" if "deny" in r.stdout else "pasa"


ph = f'python "{SCRIPTS / "permisos_hooks.py"}"'
chequear("Claude puede correr resumen, bloqueos y estado", all(hook(f"{ph} {c}") == "pasa" for c in ("resumen", "bloqueos", "estado")))
chequear("Claude no puede limpiar el registro ni autorizar", hook(f"{ph} limpiar") == "deniega" and hook(f"{ph} permitir /tmp") == "deniega")

# documentación
cs = (RAIZ / "skills" / "cerrar-sesion" / "SKILL.md").read_text(encoding="utf-8")
chequear("/cerrar-sesion corre el resumen, propone autorizar y aclara que no interrumpe", "permisos_hooks.py resumen" in cs and "/permitir" in cs and "no interrumpe el trabajo" in cs)
rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el README explica /permisos y el resumen de /cerrar-sesion", "`/permisos`" in rd and "resumen" in rd and "/cerrar-sesion" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
