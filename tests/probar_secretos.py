"""Claves, credenciales y datos personales: el detector, `.env` con permiso, los hooks de git y el hook de Claude.

Las claves de prueba se arman en el momento con letras al azar (semilla fija): el repositorio nunca contiene una con formato real.
"""
import json
import os
import random
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
import secretos  # noqa: E402

BASE = RAIZ / ".temporal" / "proy-secretos"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def azar(n, alfabeto, semilla):
    r = random.Random(semilla)
    s = "".join(r.choice(alfabeto) for _ in range(n))
    assert not secretos.VALOR_FALSO.search(s), s
    return s


ALNUM = "abcdefghijkmnopqrstuvwyzABCDEFGHJKLMNPQRSTUVWYZ0123456789"
MAYUS = "ABCDEFGHJKLMNPQRSTUVWYZ0123456789"
TOKENS = {
    "SEC-SECRETO-AWS": "AKIA" + azar(16, MAYUS, 1),
    "SEC-SECRETO-GITHUB": "ghp_" + azar(36, ALNUM, 2),
    "SEC-SECRETO-ANTHROPIC": "sk-ant-" + azar(40, ALNUM, 3),
    "SEC-SECRETO-STRIPE": "sk_live_" + azar(24, ALNUM, 4),
    "SEC-SECRETO-SLACK": "xoxb-" + azar(12, "0123456789", 5) + "-" + azar(24, ALNUM, 6),
    "SEC-SECRETO-GOOGLE": "AIza" + azar(35, ALNUM, 7),
    "SEC-SECRETO-JWT": "eyJ" + azar(20, ALNUM, 8) + ".eyJ" + azar(20, ALNUM, 9) + "." + azar(24, ALNUM, 10),
    "SEC-SECRETO-CLAVE-PRIVADA": "-----BEGIN RSA " + "PRIVATE KEY-----",
    "SEC-SECRETO-URL": "postgres://app:" + azar(12, ALNUM, 11) + "@db.interna/app",
    "SEC-SECRETO-LITERAL": 'password = "' + azar(14, ALNUM, 12) + '"',
}
CLAVE_AWS = TOKENS["SEC-SECRETO-AWS"]

# ---------------- 1. el detector
for id_esperado, texto in TOKENS.items():
    ids = [h[0] for h in secretos.hallazgos_de_linea(f"valor = {texto}" if id_esperado != "SEC-SECRETO-LITERAL" else texto)]
    chequear(f"detecta {id_esperado}", id_esperado in ids, ids)

for placeholder in ('api_key = "your_api_key_here"', 'password = os.environ["DB_PASSWORD"]', "AKIAIOSFODNN7" + "EXAMPLE", 'token = "<tu-token>"',
                    'secret = "********"', "DB_PASSWORD=cambiar_este_valor", 'const apiKey = process.env.API_KEY;', 'password = "' + "a" * 12 + '"'):
    chequear(f"no marca el marcador {placeholder[:34]!r}", secretos.hallazgos_de_linea(placeholder) == [], secretos.hallazgos_de_linea(placeholder))

def tarjeta_con_luhn(semilla):
    """Un número de 16 dígitos que empieza con 4 y pasa el control Luhn (no es de nadie: se arma al azar)."""
    r = random.Random(semilla)
    base = "4" + "".join(r.choice("0123456789") for _ in range(14))
    for ultimo in "0123456789":
        if secretos.luhn(base + ultimo):
            return base + ultimo


TARJETA = tarjeta_con_luhn(30)
TARJETA_MAL = TARJETA[:-1] + str((int(TARJETA[-1]) + 1) % 10)
h = secretos.hallazgos_de_linea("clave = " + CLAVE_AWS)
chequear("nunca muestra el valor completo", h and CLAVE_AWS not in h[0][2] and h[0][2].startswith(CLAVE_AWS[:4]) and "(20)" in h[0][2], h)
chequear("tarjeta válida (Luhn) se detecta y se oculta", [x[0] for x in secretos.hallazgos_de_linea("tarjeta: " + TARJETA)] == ["SEC-DATO-TARJETA"]
         and secretos.hallazgos_de_linea("tarjeta: " + TARJETA)[0][2] == "dato oculto", TARJETA)
chequear("un número de 16 dígitos que no pasa Luhn no es tarjeta", secretos.hallazgos_de_linea("pedido " + TARJETA_MAL) == [], TARJETA_MAL)
chequear("un número con dígitos repetidos (1111…) no se toma por tarjeta", secretos.hallazgos_de_linea("id 4111 1111 1111 1111") == [])
chequear("documento de identidad", [x[0] for x in secretos.hallazgos_de_linea("DN" + "I: 30.123.456")] == ["SEC-DATO-DOCUMENTO"])
chequear("senior-ignore en la misma línea", secretos.hallazgos_de_linea("clave = " + CLAVE_AWS + "  # senior-ignore: SEC-SECRETO-AWS clave de ejemplo de la documentación") == [])
chequear("senior-ignore en la línea anterior", secretos.hallazgos_de_linea("clave = " + CLAVE_AWS, "# senior-ignore: SEC-SECRETO-AWS motivo") == [])
chequear("un senior-ignore de otro ID no la descarta", secretos.hallazgos_de_linea("clave = " + CLAVE_AWS + " # senior-ignore: SEC-SECRETO-GITHUB") != [])

# archivos
for ruta, ok in ((".env", True), ("app/.env.production", True), (".env.example", False), (".env.sample", False), ("claves/servidor.pem", True), ("id_rsa", True),
                 ("id_rsa.pub", False), ("config/credentials.json", True), ("infra/terraform.tfstate", True), ("datos/clientes.sqlite", True), ("README.md", False)):
    chequear(f"archivo {ruta}: {'se marca' if ok else 'pasa'}", bool(secretos.hallazgos_de_ruta(ruta)) == ok)
sql = "\n".join(f"INSERT INTO clientes VALUES ({i}, 'a');" for i in range(25))
csv = "\n".join(f"{i},persona{i}@correo.test" for i in range(60))
chequear("un .sql con 25 INSERT es un volcado", any(x["id"] == "SEC-DATO-VOLCADO" for x in secretos.escanear_texto("db/copia.sql", sql)))
chequear("un .sql con pocos INSERT no", not secretos.escanear_texto("db/semilla.sql", "INSERT INTO t VALUES (1);\nINSERT INTO t VALUES (2);"))
chequear("un .csv con 60 correos es una lista de personas", any(x["id"] == "SEC-DATO-VOLCADO" for x in secretos.escanear_texto("datos/lista.csv", csv)))

# ---------------- 2. .gitignore
shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
G = BASE / "gitignore"
G.mkdir(parents=True)
(G / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
faltan = secretos.gitignore_faltante(G)
chequear("el .gitignore sin secretos señala lo que falta", ".env" in faltan and "*.pem" in faltan and "node_modules/" not in faltan)
secretos.completar_gitignore(G)
texto = (G / ".gitignore").read_text(encoding="utf-8")
chequear("completarlo conserva lo que había y agrega el bloque", texto.startswith("node_modules/") and ".env.*" in texto and "!.env.example" in texto)
chequear("completarlo dos veces no duplica", secretos.completar_gitignore(G) == [] and texto == (G / ".gitignore").read_text(encoding="utf-8"))

# ---------------- 3. .env con permiso: estructura y declarar sin ver valores
E = BASE / "env"
E.mkdir()
VALOR_SECRETO = azar(20, ALNUM, 20)
(E / ".env").write_text(f"DB_HOST=localhost\nDB_PASSWORD={VALOR_SECRETO}\nVACIA=\n", encoding="utf-8")


def correr(script, *args, cwd=E, env=None):
    r = subprocess.run([sys.executable, str(script), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, **(env or {}), "SENIOR_HOOK_DEPURAR": "1"})
    return r.returncode, (r.stdout + r.stderr)


ENV = SCRIPTS / "env_gestion.py"
subprocess.run(["git", "init", "-q"], cwd=E)
rc, s = correr(ENV, "estructura", "--raiz", str(E))
chequear("estructura lista los nombres con el valor oculto", "DB_PASSWORD = ***" in s and "VACIA = (vacía)" in s and "DB_HOST = ***" in s, s)
chequear("estructura nunca imprime un valor", VALOR_SECRETO not in s and "localhost" not in s, s)
rc, s = correr(ENV, "declarar", "API_TOKEN", "STRIPE_KEY", "--comentario", "pagos", "--raiz", str(E))
ej = (E / ".env.example").read_text(encoding="utf-8") if (E / ".env.example").exists() else ""
chequear("declarar agrega a .env.example con un valor falso", "API_TOKEN=cambiar_este_valor" in ej and "# pagos" in ej, ej)
env_antes = (E / ".env").read_text(encoding="utf-8")
chequear("sin permiso no toca .env y le dice a Claude qué proponer", env_antes == f"DB_HOST=localhost\nDB_PASSWORD={VALOR_SECRETO}\nVACIA=\n" and "/permitir .env" in s, s)
modo_hooks.permitir_ruta(E, ".env", "prueba")
rc, s = correr(ENV, "declarar", "API_TOKEN", "NUEVA_VARIABLE", "--raiz", str(E))
env_despues = (E / ".env").read_text(encoding="utf-8")
chequear("con permiso agrega la variable a .env sin valor y conserva lo anterior",
         env_despues.startswith(env_antes) and "NUEVA_VARIABLE=\n" in env_despues and "API_TOKEN=\n" in env_despues, env_despues)
rc, s = correr(ENV, "declarar", "1mala", "--raiz", str(E))
chequear("rechaza nombres inválidos", rc == 1 and "inválidos" in s, s)
chequear("declarar tampoco imprime valores", VALOR_SECRETO not in s)

# ---------------- 4. hooks de git: pre-commit y pre-push
GUARDIA = RAIZ / "skills" / "senior-git" / "scripts" / "guardia_autoria.py"
R = BASE / "repo"
REMOTO = BASE / "remoto.git"
R.mkdir()


def g(*a, cwd=R):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr)


g("init", "-q", "-b", "principal")
g("config", "user.name", "prueba")
g("config", "user.email", "p@x.test")
g("init", "-q", "--bare", str(REMOTO), cwd=BASE)
g("remote", "add", "origen", str(REMOTO))
rc, s = correr(GUARDIA, "instalar", "--raiz", str(R), cwd=R)
hooks = R / ".git" / "hooks"
chequear("instalar crea pre-commit, commit-msg, pre-push y la copia de secretos", all((hooks / n).exists() for n in ("pre-commit", "commit-msg", "pre-push", "senior_secretos.py")), s)
(R / "app.py").write_text("print('hola')\n", encoding="utf-8")
g("add", "app.py")
rc, s = g("commit", "-m", "feat: primera versión")
chequear("un commit limpio pasa", rc == 0, s)
(R / "config.py").write_text("AWS = '" + CLAVE_AWS + "'\n", encoding="utf-8")
g("add", "config.py")
rc, s = g("commit", "-m", "feat: configuración")
chequear("pre-commit frena una clave en el código", rc != 0 and "SEC-SECRETO-AWS" in s and "config.py:1" in s, s)
chequear("el mensaje del pre-commit no muestra la clave completa", CLAVE_AWS not in s, s)
chequear("el mensaje dice cómo resolverlo (.env y rotar)", ".env" in s and "rotar" in s, s)
g("reset", "-q")
(R / ".env").write_text("TOKEN=algo\n", encoding="utf-8")
g("add", "-f", ".env")
rc, s = g("commit", "-m", "chore: env")
chequear("pre-commit frena un .env aunque se fuerce con git add -f", rc != 0 and "SEC-ARCHIVO-ENV" in s, s)
g("reset", "-q")
(R / ".env").unlink()
(R / "config.py").write_text("AWS = os.environ['AWS_KEY']\n", encoding="utf-8")
g("add", "config.py")
rc, s = g("commit", "-m", "feat: configuración desde el entorno")
chequear("leer la clave de una variable de entorno pasa", rc == 0, s)

# una clave agregada y borrada después sigue en el historial: el pre-push mira commit por commit
(R / "viejo.py").write_text("K = '" + TOKENS["SEC-SECRETO-GITHUB"] + "'\n", encoding="utf-8")
g("add", "viejo.py")
rc, s = g("commit", "--no-verify", "-m", "feat: agrega algo (se salta el pre-commit)")
chequear("(preparación) --no-verify salta el pre-commit", rc == 0, s)
(R / "viejo.py").write_text("K = None\n", encoding="utf-8")
g("add", "viejo.py")
g("commit", "-q", "-m", "fix: quita la clave")
rc, s = g("push", "origen", "principal")
chequear("pre-push frena aunque la clave ya no esté en el último commit", rc != 0 and "PUSH BLOQUEADO" in s and "SEC-SECRETO-GITHUB" in s, s)
chequear("el mensaje del pre-push no muestra la clave", TOKENS["SEC-SECRETO-GITHUB"] not in s, s)
chequear("el mensaje del pre-push dice que viaja en el historial", "historial" in s, s)
g("reset", "-q", "--hard", "HEAD~2")
rc, s = g("push", "origen", "principal")
chequear("sin la clave en el historial el push pasa", rc == 0, s)

# verificar.py secretos
VER = SCRIPTS / "verificar.py"
(R / "extra.py").write_text("T = '" + TOKENS["SEC-SECRETO-STRIPE"] + "'\n", encoding="utf-8")
rc, s = correr(VER, "secretos", "--raiz", str(R), cwd=R)
chequear("verificar.py secretos marca la clave y la falta de .gitignore", "SEC-SECRETO-STRIPE" in s and ".gitignore" in s and TOKENS["SEC-SECRETO-STRIPE"] not in s, s)
(R / "extra.py").unlink()
secretos.completar_gitignore(R)
rc, s = correr(VER, "secretos", "--raiz", str(R), cwd=R)
chequear("con el repositorio limpio y el .gitignore completo, pasa", "sin claves" in s and "AVISO" not in s, s)
(R / "estado.py").write_text("x = 1\n", encoding="utf-8")
g("add", "-f", "-A")
g("rm", "-q", "--cached", "-r", ".")
(R / "datos.sqlite").write_bytes(b"SQLite format 3\x00" + b"\x00" * 50)
g("add", "-f", "datos.sqlite")
rc, s = correr(SCRIPTS / "secretos.py", "todo", "--raiz", str(R), cwd=R)
chequear("un archivo secreto ya versionado se señala como tal", "ya versionado" in s and "datos.sqlite" in s, s)
g("rm", "-q", "--cached", "datos.sqlite")

# ---------------- 5. hook de Claude
P = BASE / "claude"
P.mkdir()
g("init", "-q", cwd=P)
(P / ".gitignore").write_text("local/\n.env\n", encoding="utf-8")
(P / ".env").write_text("TOKEN=secreto\n", encoding="utf-8")
(P / ".env.example").write_text("TOKEN=cambiar_este_valor\n", encoding="utf-8")
HOOK_S = SCRIPTS / "hook_secretos_claude.py"
HOOK_P = SCRIPTS / "hook_archivos_protegidos.py"


def hook(script, herramienta, **entrada):
    ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(P), "hook_event_name": "PreToolUse"}
    r = subprocess.run([sys.executable, str(script)], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", cwd=P,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(P)})
    if "Traceback" in r.stderr:
        raise RuntimeError(r.stderr[-500:])
    return ("deniega" if "deny" in r.stdout else "pasa"), r.stdout


GT = chr(62)
casos = [
    ("escribir una clave en el código", "Write", dict(file_path="app.py", content="K = '" + CLAVE_AWS + "'\n"), "deniega"),
    ("editar para poner una clave", "Edit", dict(file_path="app.py", old_string="a", new_string="K = '" + CLAVE_AWS + "'"), "deniega"),
    ("escribir un dato personal en el código", "Write", dict(file_path="datos.py", content="# DN" + "I: 30.123.456\n"), "deniega"),
    ("escribir un marcador de posición", "Write", dict(file_path="app.py", content="K = os.environ['AWS_KEY']\n"), "pasa"),
    ("escribir la clave en .temporal/ (git lo ignora)", "Write", dict(file_path=".temporal/x.py", content="K = '" + CLAVE_AWS + "'\n"), "pasa"),
    ("escribir la clave en una carpeta que .gitignore excluye", "Write", dict(file_path="local/x.py", content="K = '" + CLAVE_AWS + "'\n"), "pasa"),
    ("escribir una clave con senior-ignore", "Write", dict(file_path="doc.md", content="K = " + CLAVE_AWS + "  # senior-ignore: SEC-SECRETO-AWS ejemplo de la documentación\n"), "pasa"),
    ("leer .env", "Read", dict(file_path=".env"), "deniega"),
    ("leer .env con Grep", "Grep", dict(pattern="TOKEN", path=".env"), "deniega"),
    ("leer .env.example", "Read", dict(file_path=".env.example"), "pasa"),
    ("leer app.py", "Read", dict(file_path="app.py"), "pasa"),
    ("cat .env", "Bash", dict(command="cat .env"), "deniega"),
    ("type .env en PowerShell", "PowerShell", dict(command="type .env"), "deniega"),
    ("Get-Content de un .env", "PowerShell", dict(command="Get-Content .\\.env"), "deniega"),
    ("grep dentro de .env", "Bash", dict(command="grep TOKEN .env"), "deniega"),
    ("cat de .env.example", "Bash", dict(command="cat .env.example"), "pasa"),
    ("ls", "Bash", dict(command="ls -la"), "pasa"),
    ("agregar a .env con una redirección", "Bash", dict(command="echo NUEVA=1 " + GT * 2 + " .env"), "deniega"),
    ("sed -i sobre .env", "Bash", dict(command="sed -i 's/a/b/' .env"), "deniega"),
    ("declarar con env_gestion.py", "Bash", dict(command=f"python \"{ENV}\" declarar NUEVA_VARIABLE"), "pasa"),
    ("git add .env", "Bash", dict(command="git add .env"), "deniega"),
    ("git add -f de cualquier cosa", "Bash", dict(command="git add -f build/salida.js"), "deniega"),
    ("git add de un archivo común", "Bash", dict(command="git add src/app.py README.md"), "pasa"),
    ("git add -A", "Bash", dict(command="git add -A"), "pasa"),
    ("git commit con una clave en el mensaje", "Bash", dict(command=f"git commit -m \"usa la clave {TOKENS['SEC-SECRETO-GITHUB']}\""), "deniega"),
    ("git commit con un mensaje normal", "Bash", dict(command="git commit -m \"feat: nueva pantalla\""), "pasa"),
    ("gh pr create con una clave en el cuerpo", "Bash", dict(command=f"gh pr create --body \"token {TOKENS['SEC-SECRETO-GITHUB']}\""), "deniega"),
]
for desc, h, entrada, esperado in casos:
    r, salida = hook(HOOK_S, h, **entrada)
    chequear(f"hook: {desc}", r == esperado, salida)

r, s = hook(HOOK_S, "Write", file_path="app.py", content="K = '" + CLAVE_AWS + "'\n")
chequear("el bloqueo explica la salida: variable de entorno, env_gestion y senior-ignore",
         "variable de entorno" in s and "env_gestion.py" in s and "senior-ignore" in s and CLAVE_AWS not in s, s)
r, s = hook(HOOK_S, "Read", file_path=".env")
chequear("el bloqueo de lectura propone el camino: estructura, proponerle al usuario y /permitir", "estructura" in s and "/permitir" in s and "no podés" in s, s)
r, s = hook(HOOK_P, "Write", file_path=".env", content="A=1\n")
chequear("escribir .env sin permiso: el hook de protegidos lo frena y propone declarar o pedir permiso", r == "deniega" and "env_gestion.py" in s and "/permitir" in s, s)
bl = json.loads((P / ".git" / "senior-hooks.json").read_text(encoding="utf-8"))["bloqueos"] if (P / ".git" / "senior-hooks.json").exists() else []
chequear("lo bloqueado queda registrado para el usuario", any(b["hook"] == "secretos" for b in bl), bl)

# con el permiso del usuario (`/permitir .env` escrito en el chat), Claude puede leer y modificar .env
ev = {"prompt": "/permitir .env -- necesito que Claude estructure las variables", "cwd": str(P)}
r = subprocess.run([sys.executable, str(SCRIPTS / "hook_permisos_chat.py")], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=P, env={**os.environ, "CLAUDE_PROJECT_DIR": str(P)})
chequear("/permitir .env escrito en el chat autoriza el archivo", modo_hooks.esta_permitido(P, P / ".env") and "Autorizada" in r.stdout, r.stdout + r.stderr)
for desc, script, h, entrada in (("leer .env", HOOK_S, "Read", dict(file_path=".env")),
                                 ("cat .env", HOOK_S, "Bash", dict(command="cat .env")),
                                 ("agregar a .env con una redirección", HOOK_S, "Bash", dict(command="echo NUEVA=1 " + GT * 2 + " .env")),
                                 ("escribir .env", HOOK_P, "Write", dict(file_path=".env", content="A=1\n")),
                                 ("editar .env", HOOK_P, "Edit", dict(file_path=".env", old_string="a", new_string="b"))):
    r, s = hook(script, h, **entrada)
    chequear(f"con /permitir .env: {desc}", r == "pasa", s)
r, s = hook(HOOK_S, "Read", file_path="id_rsa")
chequear("el permiso de .env no abre las demás claves", r == "deniega", s)

# ---------------- 6. el hook está registrado y la documentación lo explica
sys.path.insert(0, str(RAIZ / "skills" / "senior-git" / "scripts"))
import guardia_autoria  # noqa: E402
reg = [h for h in guardia_autoria.HOOKS_CLAUDE if h["script"] == "hook_secretos_claude.py"]
chequear("la guardia mantiene registrado el hook de secretos para leer, escribir y ejecutar", len(reg) == 1 and all(t in reg[0]["matcher"] for t in ("Read", "Write", "Edit", "Bash", "PowerShell")))
chequear("el hook de secretos existe donde lo busca la guardia", guardia_autoria.ruta_hook_claude(reg[0]).exists())

sk = (RAIZ / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8")
rd = (RAIZ / "README.md").read_text(encoding="utf-8")
cm = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
chequear("senior tiene el principio 18 con el permiso para .env y la propuesta", "18. **Ninguna clave" in sk and "/permitir .env" in sk and "env_gestion.py" in sk and "references/secretos.md" in sk)
chequear("existe la referencia de secretos", (RAIZ / "skills" / "senior" / "references" / "secretos.md").exists())
chequear("el README explica las cuatro capas, el permiso de .env y la rotación", "## Secretos y datos sensibles" in rd and "/permitir .env" in rd and "se rota" in rd and "pre-commit" in rd)
chequear("CLAUDE.md del repositorio lo dice", "/permitir .env" in cm and "env_gestion.py" in cm)
chequear("el flujo de GitHub escanea el repositorio", "secretos.py todo" in (RAIZ / ".github" / "workflows" / "pruebas.yml").read_text(encoding="utf-8"))
chequear("adoptar-proyecto completa el .gitignore", "secretos.py" in (RAIZ / "skills" / "adoptar-proyecto" / "scripts" / "plan_adopcion.py").read_text(encoding="utf-8")
         and "3c. **Secretos.**" in (RAIZ / "skills" / "adoptar-proyecto" / "SKILL.md").read_text(encoding="utf-8"))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
