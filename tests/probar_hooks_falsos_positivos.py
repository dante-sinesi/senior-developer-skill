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
LECT = SK / "senior-relevar" / "scripts" / "hook_lectura_externa.py"
CHAT = SK / "senior" / "scripts" / "hook_permisos_chat.py"
BASE = RAIZ / ".temporal" / "proy-falsos"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def repo(nombre, git=True):
    p = BASE / "carpeta de trabajo" / nombre
    p.mkdir(parents=True)
    if git:
        subprocess.run(["git", "init", "-q"], cwd=p)
    return p


def hook(script, proyecto, herramienta, cwd=None, **entrada):
    datos = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(cwd or proyecto)}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proyecto), "GIT_CEILING_DIRECTORIES": str(BASE)}
    p = subprocess.run([sys.executable, "-X", "utf8", str(script)], input=json.dumps(datos), capture_output=True, text=True, encoding="utf-8", env=env)
    if p.returncode == 2:
        return "bloquea", p.stderr
    if '"deny"' in p.stdout:
        return "deniega", json.loads(p.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    if '"ask"' in p.stdout:
        return "pregunta", ""
    return "pasa", ""


def chat(proyecto, prompt):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(proyecto)}
    p = subprocess.run([sys.executable, "-X", "utf8", str(CHAT)], input=json.dumps({"prompt": prompt, "cwd": str(proyecto)}), capture_output=True,
                       text=True, encoding="utf-8", env=env)
    if not p.stdout.strip():
        return None
    return json.loads(p.stdout)["hookSpecificOutput"]


if BASE.exists():
    shutil.rmtree(BASE, onerror=_forzar)
BASE.mkdir(parents=True)
A = repo("balatro")
B = repo("dsinesi")
SIN_GIT = repo("carpeta-suelta", git=False)
AFUERA = BASE / "otra-carpeta"
AFUERA.mkdir()

# ---------- lo que se bloqueaba por error (registro real del otro proyecto)
r, _ = hook(FUERA, A, "Bash", command="S=.temporal/muestras; mkdir -p $S; cp a.html $S/m2.html")
chequear("una variable del propio comando que apunta adentro ($S/m2.html) pasa", r == "pasa", r)
r, _ = hook(FUERA, A, "Bash", command="S=.temporal/m; D=$S/dos; cp a $D/m2.html")
chequear("variables encadenadas ($D desde $S) pasan", r == "pasa", r)
r, _ = hook(FUERA, A, "Bash", command=f'D="{AFUERA.as_posix()}/x"; cp a $D/m2.html')
chequear("una variable que resuelve a una carpeta de afuera se sigue denegando", r == "deniega", r)
r, _ = hook(FUERA, A, "Bash", command="cp a.html $CARPETA_QUE_NO_SE_DEFINIO/m2.html")
chequear("una variable que no se puede resolver no se juzga (deja pasar)", r == "pasa", r)
r, _ = hook(FUERA, A, "PowerShell", command='$d = ".temporal\\fuentes"; Invoke-WebRequest https://x.test/f.woff2 -OutFile $d\\chakra-petch-400.woff2')
chequear("PowerShell: $d asignada dentro del proyecto pasa", r == "pasa", r)
r, _ = hook(FUERA, A, "PowerShell", command="New-Item $env:TEMP\\carpeta -ItemType Directory")
chequear("$env:TEMP sigue siendo «afuera»", r == "deniega", r)
r, _ = hook(FUERA, A, "Bash", command="cp a.html %TEMP%\\m2.html")
chequear("%TEMP% sigue siendo «afuera»", r == "deniega", r)
r, _ = hook(FUERA, A, "PowerShell", command="Set-Content $env:ALGO_PROPIO\\a.txt 'x'")
chequear("una variable de entorno desconocida no se juzga", r == "pasa", r)

# ---------- el directorio de trabajo es otro repositorio (nombres relativos)
r, _ = hook(FUERA, A, "Bash", cwd=B, command="curl -o chakra-petch-400.woff2 https://x.test/f.woff2")
chequear("un nombre relativo con el directorio de trabajo en otro repositorio de la sesión pasa", r == "pasa", r)
r, _ = hook(FUERA, A, "Bash", cwd=AFUERA, command="curl -o descarga.bin https://x.test/f.bin")
chequear("un nombre relativo con el directorio de trabajo en una carpeta que no es proyecto se sigue denegando", r == "deniega", r)

# ---------- proyectos hermanos
r, _ = hook(FUERA, A, "Write", file_path=str(B / "propuestas" / "relevo-visual" / "alt-c-mesa-pulida.html"))
chequear("escribir en un proyecto hermano (otro repositorio de la misma carpeta) pasa", r == "pasa", r)
r, _ = hook(FUERA, A, "Write", file_path=str(SIN_GIT / "x.html"))
chequear("una carpeta hermana que no es un repositorio se sigue denegando", r == "deniega", r)
r, _ = hook(FUERA, A, "Write", file_path=str(AFUERA / "x.html"))
chequear("una carpeta de afuera, no hermana, se sigue denegando", r == "deniega", r)
chequear("los hermanos están permitidos por defecto", mh.cargar(A)["hermanos"] is True)
chequear("proyecto_hermano reconoce el repositorio por la ruta aunque el archivo todavía no exista", mh.proyecto_hermano(A, B / "nueva" / "carpeta" / "x.txt"))
chequear("y no se confunde con el propio proyecto", not mh.proyecto_hermano(A, A / "x.txt"))
datos = mh.cargar(A)
datos["hermanos"] = False
mh.guardar(A, datos)
r, _ = hook(FUERA, A, "Write", file_path=str(B / "x.html"))
chequear("con «hermanos no» vuelve a denegar", r == "deniega", r)
datos["hermanos"] = True
mh.guardar(A, datos)

# ---------- leer la configuración está permitido; cambiarla no
CONF = ".git/" + mh.NOMBRE
for nombre, cmd in (("cat", f"cat {CONF}"), ("type", f"type {CONF}"), ("head", f"head -20 {CONF}"), ("grep", f"grep bloqueos {CONF}"),
                    ("tubería con jq", f"cat {CONF} | jq .modo"), ("python permisos estado", "python permisos_hooks.py estado"),
                    ("python permisos bloqueos", "python permisos_hooks.py bloqueos")):
    r, _ = hook(FUERA, A, "Bash", command=cmd)
    chequear(f"leer la configuración con «{nombre}» pasa", r == "pasa", r)
r, _ = hook(FUERA, A, "PowerShell", command=f"Get-Content {CONF}")
chequear("leerla con Get-Content pasa", r == "pasa", r)
for nombre, cmd in (("redirección", f"echo '{{}}' > {CONF}"), ("sed -i", f"sed -i s/a/b/ {CONF}"), ("cp", f"cp otra.json {CONF}"), ("permitir", "python permisos_hooks.py permitir C:/x/y"),
                    ("modo", "python permisos_hooks.py modo preguntar"), ("hermanos", "python permisos_hooks.py hermanos no"), ("limpiar", "python permisos_hooks.py limpiar"),
                    ("leer y borrar en un solo comando", f"cat {CONF}; rm {CONF}")):
    r, msg = hook(FUERA, A, "Bash", command=cmd)
    chequear(f"cambiarla con «{nombre}» se deniega", r == "deniega", (r, msg))
r, msg = hook(FUERA, A, "Write", file_path=str(A / ".git" / mh.NOMBRE))
chequear("escribirla con Write se deniega y el mensaje ofrece la vía del chat", r == "deniega" and "/permitir" in msg, msg)

# ---------- una imagen que no se puede medir ya no frena el trabajo
chica = A / "r_fold.png"
chica.write_bytes(b"esto no es una imagen" * 10)
grande = A / "r_proy.png"
grande.write_bytes(b"esto tampoco " * 20000)
r, _ = hook(LECT, A, "Read", file_path=str(chica))
chequear("una imagen chica que no se puede medir se lee", r == "pasa", r)
r, msg = hook(LECT, A, "Read", file_path=str(grande))
chequear("una grande que no se puede medir se bloquea con el comando para reducirla (no pregunta)", r == "bloquea" and "convertir_fuentes.py" in msg and "--importar" in msg, (r, msg))

# ---------- autorizar desde el chat, sin terminal ni sesión nueva
C = repo("xampp-proyecto")
XAMPP = BASE / "xampp htdocs" / "demo"
XAMPP.mkdir(parents=True)
r, _ = hook(FUERA, C, "Write", file_path=str(XAMPP / "index.php"))
chequear("antes de autorizar, la carpeta de otro programa se deniega", r == "deniega", r)
sal = chat(C, f'Hola, necesito que uses el servidor local.\n/permitir "{XAMPP.parent.as_posix()}" -- servidor local de pruebas\nGracias')
chequear("/permitir en el chat responde con contexto para Claude", sal and sal["hookEventName"] == "UserPromptSubmit" and "Autorizada de antemano" in sal["additionalContext"], sal)
r, _ = hook(FUERA, C, "Write", file_path=str(XAMPP / "index.php"))
chequear("después de /permitir, la ruta (con espacios y subcarpetas) pasa", r == "pasa", r)
chequear("el motivo quedó guardado", any("servidor local de pruebas" in str(p) for p in mh.cargar(C)["permitidos"]), mh.cargar(C))
sal = chat(C, f"/permitir {XAMPP.parent.as_posix()}")
chequear("repetir no duplica", "Ya estaba autorizada" in sal["additionalContext"] and len(mh.cargar(C)["permitidos"]) == 1, sal)
sal = chat(C, "/permitir C:\\")
chequear("una raíz de disco no se autoriza", "demasiado amplia" in sal["additionalContext"], sal)
sal = chat(C, f"/permitir {Path.home().as_posix()}")
chequear("la carpeta del usuario no se autoriza", "demasiado amplia" in sal["additionalContext"], sal)
sal = chat(C, "/permitir")
chequear("sin ruta lo dice", "Falta la ruta" in sal["additionalContext"], sal)
sal = chat(C, "/hooks-modo preguntar")
r, _ = hook(FUERA, C, "Write", file_path=str(AFUERA / "x.html"))
chequear("/hooks-modo preguntar cambia el modo", "preguntar" in sal["additionalContext"] and r == "pregunta", (sal, r))
chat(C, "/hooks-modo denegar")
sal = chat(C, "/hooks-hermanos no")
r, _ = hook(FUERA, C, "Write", file_path=str(B / "x.html"))
chequear("/hooks-hermanos no desactiva los proyectos hermanos", "no permitidos" in sal["additionalContext"] and r == "deniega", (sal, r))
chat(C, "/hooks-hermanos si")
sal = chat(C, "/permisos")
chequear("/permisos resume el modo, lo autorizado y los bloqueos", "Modo: denegar" in sal["additionalContext"] and "xampp htdocs" in sal["additionalContext"] and "Últimos bloqueos" in sal["additionalContext"], sal)
sal = chat(C, f'/quitar-permiso "{XAMPP.parent.as_posix()}"')
r, _ = hook(FUERA, C, "Write", file_path=str(XAMPP / "index.php"))
chequear("/quitar-permiso lo revoca", "quitado" in sal["additionalContext"].lower() and r == "deniega", (sal, r))
chequear("un mensaje común no dispara nada", chat(C, "Quiero que hagas un cambio en el README, sin /permitir ninguno") is None)
sal = chat(C, "/permitir ../hermana-relativa")
chequear("una ruta relativa se resuelve contra el proyecto", sal and "hermana-relativa" in sal["additionalContext"], sal)
p = subprocess.run([sys.executable, str(CHAT)], input="no es json", capture_output=True, text=True)
chequear("una entrada rota deja pasar el mensaje", p.returncode == 0 and p.stdout.strip() == "")

# ---------- el hook del chat queda registrado como evento propio, sin tocar los demás
FALSO = BASE / "home-falso"
(FALSO / ".claude").mkdir(parents=True)
(FALSO / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "otro"}]}]}, "model": "x"}), encoding="utf-8")
env = {**os.environ, "USERPROFILE": str(FALSO), "HOME": str(FALSO)}
codigo = ("import sys, json; sys.path.insert(0, r'" + str(SK / "senior-git" / "scripts") + "'); import guardia_autoria as g; "
          "print(json.dumps(g.asegurar_claude(False)[0], ensure_ascii=False))")
p = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo], capture_output=True, text=True, encoding="utf-8", env=env)
ajustes = json.loads((FALSO / ".claude" / "settings.json").read_text(encoding="utf-8"))
grupos = ajustes["hooks"].get("UserPromptSubmit", [])
chequear("la guardia registra el hook del chat en UserPromptSubmit, sin matcher", len(grupos) == 1 and "matcher" not in grupos[0] and "hook_permisos_chat.py" in grupos[0]["hooks"][0]["command"], (p.stdout, p.stderr, ajustes))
chequear("y conserva lo que ya había (otro hook y otros ajustes)", ajustes["model"] == "x" and any(h["command"] == "otro" for g_ in ajustes["hooks"]["PreToolUse"] for h in g_["hooks"]))
chequear("los hooks de PreToolUse siguen en su evento", sum("hook_" in h["command"] for g_ in ajustes["hooks"]["PreToolUse"] for h in g_["hooks"]) >= 4)
p = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo], capture_output=True, text=True, encoding="utf-8", env=env)
ajustes2 = json.loads((FALSO / ".claude" / "settings.json").read_text(encoding="utf-8"))
chequear("repetir no lo duplica", len(ajustes2["hooks"]["UserPromptSubmit"]) == 1)

# ---------- documentación
sk = (SK / "senior" / "SKILL.md").read_text(encoding="utf-8")
rd = (RAIZ / "README.md").read_text(encoding="utf-8")
cm = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
chequear("senior explica /permitir, los proyectos hermanos y que se puede leer la configuración", "/permitir" in sk and "hermano" in sk and "leer" in sk)
chequear("el README lo explica", "/permitir" in rd and "proyectos hermanos" in rd)
chequear("CLAUDE.md del repositorio lo dice", "/permitir" in cm)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
