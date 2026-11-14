import io
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SK = RAIZ / "skills"
sys.path.insert(0, str(SK / "senior" / "scripts"))
import modo_hooks as mh  # noqa: E402

FUERA = SK / "senior" / "scripts" / "hook_fuera_del_proyecto.py"
PROT = SK / "senior" / "scripts" / "hook_archivos_protegidos.py"
PERM = SK / "senior" / "scripts" / "permisos_hooks.py"
BASE = RAIZ / ".temporal" / "proy-hooks"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def crear(nombre, con_git=True):
    p = BASE / nombre
    p.mkdir(parents=True)
    if con_git:
        subprocess.run(["git", "init", "-q"], cwd=p)
    return p


def hook(script, proyecto, herramienta, **entrada):
    datos = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(proyecto)}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proyecto)}
    p = subprocess.run([sys.executable, "-X", "utf8", str(script)], input=json.dumps(datos), capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode == 2:
        return "bloquea", p.stderr
    if '"deny"' in p.stdout:
        return "deniega", json.loads(p.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    if '"ask"' in p.stdout:
        return "pregunta", json.loads(p.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    return "pasa", ""


def cli(proyecto, *a):
    p = subprocess.run([sys.executable, "-X", "utf8", str(PERM), *a, "--raiz", str(proyecto)], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


if BASE.exists():
    shutil.rmtree(BASE, onerror=_forzar)
BASE.mkdir(parents=True)
A = crear("a")
SCRATCH = r"C:\Users\Dante\AppData\Local\Temp\claude\773e6baf51fa85c4\bff3d5b0\scratchpad\limpiar_consulta.py"

# ---------- el caso que se reportó: por defecto NO interrumpe
r, msg = hook(FUERA, A, "Write", file_path=SCRATCH)
chequear("escribir en la carpeta de trabajo del entorno se deniega sin preguntar", r == "deniega", (r, msg))
chequear("el motivo trae la ruta exacta para rehacerlo dentro del proyecto", "limpiar_consulta.py" in msg and (A / ".temporal" / "limpiar_consulta.py").as_posix() in msg and "rehacé exactamente lo mismo" in msg, msg)
chequear("el motivo le dice a Claude qué hacer: .temporal, anotar el pendiente y seguir", "No es una pregunta" in msg and ".temporal/" in msg and "docs/pendientes.md" in msg and "seguí sin ese paso" in msg and "/permitir" in msg, msg)
chequear("por defecto el modo es denegar", mh.cargar(A)["modo"] == "denegar")
d = mh.cargar(A)
chequear("lo bloqueado queda registrado dentro de .git del proyecto", (A / ".git" / "senior-hooks.json").exists() and len(d["bloqueos"]) == 1 and "limpiar_consulta.py" in d["bloqueos"][0]["detalle"], d)
hook(FUERA, A, "Write", file_path=SCRATCH)
chequear("el mismo bloqueo no se repite en el registro", len(mh.cargar(A)["bloqueos"]) == 1)
r, _ = hook(FUERA, A, "Bash", command="echo hola > /tmp/a.txt")
chequear("una redirección afuera también se deniega", r == "deniega")
r, _ = hook(FUERA, A, "Write", file_path=str(A / ".temporal" / "limpiar_consulta.py"))
chequear("escribir dentro del proyecto pasa", r == "pasa")
r, _ = hook(FUERA, A, "Write", file_path=str(Path.home() / ".claude" / "projects" / "p" / "memory" / "a.md"))
chequear("la memoria de Claude sigue permitida", r == "pasa")

# ---------- modo preguntar: el comportamiento anterior
rc, s = cli(A, "modo", "preguntar")
r, msg = hook(FUERA, A, "Write", file_path=SCRATCH)
chequear("en modo preguntar vuelve a preguntar en la interfaz", rc == 0 and r == "pregunta" and "¿Autorizás" in msg, (r, msg))
cli(A, "modo", "denegar")

# ---------- autorización previa del usuario
FUERA_DIR = BASE / "xampp-htdocs"
FUERA_DIR.mkdir()
r, _ = hook(FUERA, A, "Write", file_path=str(FUERA_DIR / "demo" / "index.php"))
chequear("sin autorización previa, una carpeta de otro programa se deniega", r == "deniega")
rc, s = cli(A, "permitir", str(FUERA_DIR), "--motivo", "servidor local")
chequear("el usuario autoriza la carpeta de antemano", rc == 0 and "Autorizada" in s, s)
r, _ = hook(FUERA, A, "Write", file_path=str(FUERA_DIR / "demo" / "index.php"))
chequear("lo que está dentro de la carpeta autorizada pasa", r == "pasa")
r, _ = hook(FUERA, A, "Bash", command=f'mkdir -p "{FUERA_DIR.as_posix()}/otra"')
chequear("también con comandos de shell", r == "pasa")
r, _ = hook(FUERA, A, "Write", file_path=str(BASE / "otra-carpeta" / "x.php"))
chequear("una carpeta vecina no autorizada se sigue denegando", r == "deniega")
rc, s = cli(A, "estado")
chequear("estado muestra el modo, lo autorizado y los bloqueos", "Modo: denegar" in s and "servidor local" in s and "Bloqueos:" in s, s)
rc, s = cli(A, "bloqueos")
chequear("bloqueos lista lo que se denegó", "limpiar_consulta.py" in s and "escritura fuera del proyecto" in s, s)
rc, s = cli(A, "quitar", str(FUERA_DIR))
r, _ = hook(FUERA, A, "Write", file_path=str(FUERA_DIR / "demo" / "index.php"))
chequear("quitar la autorización la revoca", "Quitada" in s and r == "deniega")
rc, s = cli(A, "limpiar")
chequear("limpiar vacía el registro", len(mh.cargar(A)["bloqueos"]) == 0)

# ---------- Claude no puede autorizarse solo (ni en modo preguntar)
for modo in ("denegar", "preguntar"):
    cli(A, "modo", modo)
    r1, m1 = hook(FUERA, A, "Bash", command=f"python {PERM.as_posix()} permitir C:/Users")
    r2, _ = hook(FUERA, A, "Bash", command=f"python {PERM.as_posix()} modo preguntar --raiz .")
    r3, _ = hook(FUERA, A, "Write", file_path=str(A / ".git" / "senior-hooks.json"))
    r4, _ = hook(FUERA, A, "Bash", command="echo '{}' > .git/senior-hooks.json")
    r5, _ = hook(FUERA, A, "PowerShell", command="Set-Content .git/senior-hooks.json '{}'")
    chequear(f"modo {modo}: permitir, cambiar el modo y escribir la configuración se deniegan siempre", {r1, r2, r3, r4, r5} == {"deniega"}, (r1, r2, r3, r4, r5))
r, _ = hook(FUERA, A, "Bash", command=f"python {PERM.as_posix()} estado")
chequear("mirar el estado (solo lectura) sí se puede", r == "pasa")
chequear("el motivo explica que lo configura el usuario y cómo", "no se pueden cambiar desde Claude" in m1 and "/permitir" in m1, m1)
cli(A, "modo", "denegar")

# ---------- archivos protegidos
r, msg = hook(PROT, A, "Write", file_path=".env")
chequear("editar un .env se deniega sin preguntar y explica la vía correcta", r == "deniega" and "No es una pregunta" in msg and "pendientes.md" in msg, (r, msg))
r, _ = hook(PROT, A, "Edit", file_path="package-lock.json")
chequear("un archivo de bloqueo se deniega", r == "deniega")
r, _ = hook(PROT, A, "Write", file_path="src/app.py")
chequear("un archivo común pasa", r == "pasa")
cli(A, "modo", "preguntar")
r, _ = hook(PROT, A, "Write", file_path=".env")
chequear("en modo preguntar el .env vuelve a preguntar", r == "pregunta")
cli(A, "modo", "denegar")
cli(A, "permitir", ".env", "--motivo", "archivo de pruebas")
r, _ = hook(PROT, A, "Write", file_path=".env")
r2, _ = hook(PROT, A, "Write", file_path=".env.production")
chequear("un archivo protegido autorizado de antemano pasa y los demás no", r == "pasa" and r2 == "deniega", (r, r2))
r, _ = hook(PROT, A, "Edit", file_path=".env.local")
chequear("una ruta relativa se resuelve contra el proyecto", r == "deniega")

# ---------- robustez
B = crear("b", con_git=False)
r, _ = hook(FUERA, B, "Write", file_path=SCRATCH)
chequear("un proyecto sin git también se protege y guarda su configuración en .temporal", r == "deniega" and (B / ".temporal" / "senior-hooks.json").exists())
(A / ".git" / "senior-hooks.json").write_text("esto no es json", encoding="utf-8")
chequear("una configuración rota vuelve a los valores por defecto", mh.cargar(A)["modo"] == "denegar" and mh.cargar(A)["permitidos"] == [])
r, _ = hook(FUERA, A, "Write", file_path=SCRATCH)
chequear("y el hook sigue funcionando con ella", r == "deniega")
p = subprocess.run([sys.executable, str(FUERA)], input="no es json", capture_output=True, text=True)
chequear("una entrada rota deja pasar", p.returncode == 0 and p.stdout.strip() == "")
chequear("la respuesta tiene la forma que espera Claude Code", json.loads(mh.respuesta(A, "x", "d", "¿?", "haz algo."))["hookSpecificOutput"]["hookEventName"] == "PreToolUse")

# ---------- documentación
sk = (SK / "senior" / "SKILL.md").read_text(encoding="utf-8") + ((SK / "senior" / "references" / "metodo-completo.md").read_text(encoding="utf-8"))
rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
cm = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
chequear("senior explica los dos modos y que no se interrumpe", "permisos_hooks.py" in sk and "sin interrumpir" in sk)
chequear("el README lo explica", "permisos_hooks.py" in rd and "sin supervisión" in rd)
chequear("CLAUDE.md del repositorio lo dice", "permisos_hooks.py" in cm or "no interrumpe" in cm)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
