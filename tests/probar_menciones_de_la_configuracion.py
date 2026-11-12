"""El guardián de la configuración de los hooks bloquea cambiarla, no mencionarla: un cuerpo de heredoc, un mensaje de commit o de Pull Request
que nombra el archivo (o el script de permisos) pasa; un destino de cambio (redirección, tee, cp, mv, rm, sed -i, python que escribe) sigue bloqueado."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
HOOK = RAIZ / "skills" / "senior" / "scripts" / "hook_fuera_del_proyecto.py"
BASE = RAIZ / ".temporal" / "proy-menciones"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
BASE.mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=BASE)
CFG = ".git/senior-hooks" + ".json"   # el archivo que los hooks protegen
GT = chr(62)
PERMISOS = "permisos_hooks" + ".py"


def ver(herramienta, **entrada):
    ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(BASE), "hook_event_name": "PreToolUse"}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=BASE,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(BASE)})
    if "Traceback" in r.stderr:
        raise RuntimeError(r.stderr[-500:])
    if "deny" not in r.stdout:
        return "pasa", ""
    return ("config" if "configura" in r.stdout else "fuera"), r.stdout


def bash(comando):
    return ver("Bash", command=comando)[0]


# ---------------- lo que SIGUE bloqueado: la configuración como destino de un cambio
cambian = {
    "redirección": f"echo x {GT} {CFG}",
    "redirección doble": f"echo x {GT}{GT} {CFG}",
    "redirección con el destino entre comillas": f'echo x {GT} "{CFG}"',
    "tee": f"echo x | tee {CFG}",
    "cp hacia la configuración": f"cp otro.json {CFG}",
    "mv de la configuración": f"mv {CFG} /tmp/copia",
    "rm": f"rm {CFG}",
    "rm -f": f"rm -f {CFG}",
    "sed -i": f"sed -i 's/a/b/' {CFG}",
    "truncate": f"truncate -s 0 {CFG}",
    "dd of=": f"dd if=/dev/null of={CFG}",
    "python -c que escribe": f"python -c \"open('{CFG}','w').write('{{}}')\"",
    "python con heredoc que escribe": f"python - <<'E'\nfrom pathlib import Path\nPath('{CFG}').write_text('{{}}')\nE",
    "permisos_hooks permitir": f"python {PERMISOS} permitir /tmp",
    "permisos_hooks con la ruta entre comillas": f'python "C:/x/{PERMISOS}" limpiar',
    "permisos_hooks con --raiz": f"python {PERMISOS} --raiz . modo preguntar",
    "permisos_hooks hermanos": f"python {PERMISOS} hermanos no",
}
for desc, c in cambian.items():
    chequear(f"sigue bloqueando: {desc}", bash(c) == "config", c)
for desc, c in {"Set-Content": f"Set-Content -Path .git\\senior-hooks.json -Value x", "Remove-Item": "Remove-Item .git\\senior-hooks.json",
                "redirección": f'"x" {GT} .git\\senior-hooks.json'}.items():
    chequear(f"sigue bloqueando en PowerShell: {desc}", ver("PowerShell", command=c)[0] == "config", c)
chequear("sigue bloqueando escribirla con la herramienta Write", ver("Write", file_path=CFG, content="{}")[0] == "config")
chequear("y editarla con Edit", ver("Edit", file_path=CFG, old_string="a", new_string="b")[0] == "config")

# ---------------- lo que DEJA de bloquear: leerla o solo mencionarla
pasan = {
    "cat": f"cat {CFG}",
    "type": f"type {CFG}",
    "ls": f"ls -la {CFG}",
    "grep": f"grep modo {CFG}",
    "echo que la nombra": f'echo "ver {CFG}"',
    "permisos_hooks estado": f"python {PERMISOS} estado",
    "permisos_hooks resumen": f"python {PERMISOS} resumen",
    "permisos_hooks bloqueos": f'python "C:/x/{PERMISOS}" bloqueos',
    "cuerpo de heredoc que la nombra": f"cat {GT} .temporal/pr.md <<'EOF'\nEl estado vive en {CFG}; se cambia con {PERMISOS} permitir /tmp y {PERMISOS} limpiar.\nEOF",
    "cuerpo de Pull Request": f'gh pr create --title t --body "El archivo {CFG} guarda el modo. Se cambia con {PERMISOS} permitir <ruta>"',
    "cuerpo de PR con --body-file y heredoc": f"gh pr create --title t --body-file - <<'EOF'\nMenciona {CFG} y {PERMISOS} modo denegar\nEOF",
    "mensaje de commit con una redirección escrita": f'git commit -m "docs: se explica echo a {GT} {CFG} como ejemplo de lo que se bloquea"',
    "mensaje de commit que nombra el script": f'git commit -m "docs: {PERMISOS} permitir explicado"',
    "un for que lista el archivo": f'for f in {CFG}; do ls -la "$f"; done',
    "python que solo lo lee": f"python -c \"print(open('{CFG}').read())\"",
    "python con heredoc que solo lo lee": f"python - <<'E'\nprint(open('{CFG}').read())\nE",
}
for desc, c in pasan.items():
    chequear(f"ya no bloquea: {desc}", bash(c) == "pasa", (bash(c), c))
chequear("ni escribir un documento que la menciona", ver("Write", file_path="docs/x.md", content=f"El archivo {CFG} guarda el modo.")[0] == "pasa")

# ---------------- lo mismo vale para «nada fuera del proyecto»: el texto de un heredoc no es un comando
chequear("un cuerpo de heredoc con «echo a > /tmp/y» ya no cuenta como escribir fuera", bash(f"cat {GT} .temporal/n.md <<'EOF'\nprobá echo a {GT} /tmp/y para ver\nEOF") == "pasa")
chequear("un mensaje de commit con una redirección fuera tampoco", bash(f'git commit -m "docs: el ejemplo echo a {GT} /tmp/y se bloquea"') == "pasa")
chequear("pero un heredoc que alimenta a python con una escritura fuera sigue bloqueado", bash("python - <<'E'\nopen('/tmp/x','w').write('a')\nE") == "fuera")
chequear("y una redirección real fuera sigue bloqueada", bash(f"echo a {GT} /tmp/y") == "fuera")
chequear("también con el destino entre comillas", bash(f'echo a {GT} "/tmp/y"') == "fuera")

# ---------------- no se debilitó nada de lo anterior
chequear("un comando común pasa", bash("ls -la") == "pasa" and bash("git status") == "pasa")
chequear("el hook sigue protegido con su variable de depuración", "SENIOR_HOOK_DEPURAR" in HOOK.read_text(encoding="utf-8"))

rd = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("el README explica que mencionar la configuración no la cambia", "solo la menciona" in rd or "solo la mencionan" in rd or "solo menciona" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
