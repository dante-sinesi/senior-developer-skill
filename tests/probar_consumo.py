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
sys.path.insert(0, str(RAIZ / "skills" / "auditar-consumo" / "scripts"))
sys.path.insert(0, str(RAIZ / "skills" / "senior-memoria" / "scripts"))
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
import consumo  # noqa: E402
import indexar_docs  # noqa: E402
import verificar  # noqa: E402

BASE = RAIZ / ".temporal" / "proy-consumo"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def escribir(ruta, texto):
    f = Path(ruta)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


# ---------- 1. auditoría de consumo con un «home» de mentira ----------
if BASE.exists():
    shutil.rmtree(BASE, onerror=_forzar)
HOME = BASE / "home"
PROY = BASE / "proyecto"
escribir(HOME / ".claude" / "skills" / "chica" / "SKILL.md", "---\nname: chica\ndescription: Hace algo corto.\n---\n\n# Chica\n\nCuerpo corto.\n")
escribir(HOME / ".claude" / "skills" / "larga" / "SKILL.md",
         "---\nname: larga\ndescription: " + "Descripción larguísima. " * 50 + "\n---\n\n# Larga\n\n" + "linea de cuerpo con texto repetido para pesar\n" * 700)
escribir(HOME / ".claude" / "skills" / "larga" / "references" / "detalle.md", "x" * 4000)
escribir(HOME / ".claude" / "skills" / "sinskill" / "otra.txt", "no es una skill")
escribir(HOME / ".claude" / "CLAUDE.md", "y" * 12000)
escribir(PROY / "CLAUDE.md", "z" * 800)
escribir(PROY / "docs" / "ESTADO.md", "e" * 8000)
mem = HOME / ".claude" / "projects" / consumo.re.sub(r"[^A-Za-z0-9]", "-", str(PROY.resolve())) / "memory"
escribir(mem / "MEMORY.md", "\n".join(f"- [m{i}](m{i}.md) — nota" for i in range(230)))
escribir(mem / "m1.md", "memoria " * 100)
escribir(HOME / ".claude" / "settings.json", json.dumps({
    "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "a"}, {"type": "command", "command": "b"}]}]},
    "permissions": {"allow": ["Bash(ls)", "Read"]}, "mcpServers": {"s1": {}, "s2": {}}}))
escribir(PROY / ".mcp.json", json.dumps({"mcpServers": {"s3": {}, "s4": {}}}))

r = consumo.auditar(PROY.resolve(), HOME.resolve())
nombres = {s["nombre"] for s in r["skills"]}
chequear("lee las skills con SKILL.md y salta lo que no lo es", nombres == {"chica", "larga"}, nombres)
larga = next(s for s in r["skills"] if s["nombre"] == "larga")
chica = next(s for s in r["skills"] if s["nombre"] == "chica")
chequear("separa lo fijo (descripción) de lo que se paga al activarse (cuerpo)", larga["fijo_tokens"] > chica["fijo_tokens"] and larga["cuerpo_tokens"] > 5000, larga)
chequear("cuenta las líneas del cuerpo y los references aparte", larga["cuerpo_lineas"] >= 700 and larga["references"] == 1 and larga["references_tokens"] >= 1000, larga)
chequear("suma los CLAUDE.md del usuario y del proyecto", r["fijo"]["instrucciones"] == consumo.tokens(12000) + consumo.tokens(800), r["fijo"])
chequear("encuentra la memoria del proyecto por su ruta", r["memoria"] and r["memoria"]["indice_lineas"] == 230 and r["memoria"]["archivos"] == 1, r["memoria"])
chequear("el consumo fijo incluye ESTADO.md", r["fijo"]["estado"] == consumo.tokens(8000), r["fijo"])
chequear("cuenta hooks, permisos y servidores MCP (sin repetir)", r["ajustes"]["hooks"] == 2 and r["ajustes"]["permisos"] == 2 and r["ajustes"]["servidores_mcp"] == ["s1", "s2", "s3", "s4"], r["ajustes"])
h = " | ".join(r["hallazgos"])
chequear("avisa la descripción de más de 800 caracteres", "descripción de «larga»" in h, h)
chequear("avisa el cuerpo grande", "cuerpo de «larga»" in h and "references/" in h, h)
chequear("avisa los CLAUDE.md largos", "CLAUDE.md suman" in h, h)
chequear("avisa el índice de memoria pasado de 200 líneas", "230 líneas" in h, h)
chequear("avisa ESTADO.md largo", "ESTADO.md pesa" in h, h)
chequear("avisa más de 3 servidores MCP y dice que su costo no se mide", "4 servidores MCP" in h and "no se mide" in h, h)
lineas = consumo.resumen(r)
chequear("el resumen es corto y aclara lo que no mide", len(lineas) <= 20 and "No se mide" in lineas[-1], len(lineas))

# proyecto limpio y chico
LIMPIO = BASE / "limpio"
H2 = BASE / "home2"
escribir(H2 / ".claude" / "skills" / "chica" / "SKILL.md", "---\nname: chica\ndescription: Hace algo corto.\n---\n\nCuerpo.\n")
escribir(LIMPIO / "app.py", "x = 1\n")
r2 = consumo.auditar(LIMPIO.resolve(), H2.resolve())
chequear("un proyecto chico no tiene hallazgos", r2["hallazgos"] == [] and r2["memoria"] is None, r2["hallazgos"])

# línea de comandos, JSON, salida a archivo y rechazo de salir del proyecto
def cli(*a):
    p = subprocess.run([sys.executable, "-X", "utf8", str(RAIZ / "skills" / "auditar-consumo" / "scripts" / "consumo.py"), *a],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


rc, s = cli("--raiz", str(PROY), "--home", str(HOME))
chequear("CLI: con hallazgos sale con 1 y muestra el consumo fijo", rc == 1 and "Consumo fijo" in s, s[:200])
rc, s = cli("--raiz", str(LIMPIO), "--home", str(H2))
chequear("CLI: sin hallazgos sale con 0", rc == 0 and "Sin hallazgos" in s, s)
rc, s = cli("--raiz", str(PROY), "--home", str(HOME), "--json")
chequear("CLI: --json es JSON válido", json.loads(s)["fijo"]["total"] > 0)
rc, s = cli("--raiz", str(PROY), "--home", str(HOME), "--salida", ".temporal/consumo.md")
md = (PROY / ".temporal" / "consumo.md").read_text(encoding="utf-8") if (PROY / ".temporal" / "consumo.md").exists() else ""
chequear("CLI: --salida escribe el informe dentro del proyecto", "## Skills" in md and "| larga |" in md, s)
rc, s = cli("--raiz", str(PROY), "--home", str(HOME), "--salida", str(BASE.parent / "fuera.md"))
chequear("CLI: --salida fuera del proyecto se rechaza", rc != 0 and "dentro del proyecto" in s, s)
chequear("el script no modifica nada del proyecto auditado", not (PROY / "docs" / "INDEX.md").exists())

# ---------- 2. consultar muestra los tokens ----------
D = BASE / "con-docs"
escribir(D / "docs" / "requisitos" / "negocio" / "RN-001.md",
         "---\nid: RN-001\ntipo: requisito\ntitulo: Descuento por volumen\nresumen: Descuento\ntags: [descuento]\n---\n\n" + "texto " * 400)
indexar_docs.cmd_indexar(D, D / "docs")
salida = io.StringIO()
real = sys.stdout
sys.stdout = salida
indexar_docs.cmd_consultar(D / "docs", "descuento")
sys.stdout = real
s = salida.getvalue()
chequear("consultar indica los tokens aproximados de abrir el documento", "tokens al abrirlo" in s and "RN-001" in s, s)
indice = (D / "docs" / "INDEX.md").read_text(encoding="utf-8")
chequear("el índice generado no lleva esos números (sigue siendo determinista)", "tokens al abrirlo" not in indice)
chequear("un símbolo no se mide", indexar_docs.tokens_al_abrir(D, {"tipo": "simbolo", "ruta": "x.py"}) is None)
chequear("sin raíz no se mide", indexar_docs.tokens_al_abrir(None, {"tipo": "requisito", "ruta": "x"}) is None)

# ---------- 3. hook de archivos protegidos ----------
HOOK = RAIZ / "skills" / "senior" / "scripts" / "hook_archivos_protegidos.py"


def hook(herramienta, **entrada):
    datos = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(RAIZ)}
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(datos), capture_output=True, text=True, encoding="utf-8")
    return "pregunta" if ('"ask"' in p.stdout or '"deny"' in p.stdout) else "pasa"


CASOS = [
    ("Write .env", "Write", {"file_path": "app/.env"}, "pregunta"),
    ("Edit .env.production", "Edit", {"file_path": "/x/.env.production"}, "pregunta"),
    (".env.example es plantilla", "Write", {"file_path": ".env.example"}, "pasa"),
    (".env.sample es plantilla", "Write", {"file_path": ".env.sample"}, "pasa"),
    ("clave privada", "Write", {"file_path": "certs/server.pem"}, "pregunta"),
    ("id_rsa", "Edit", {"file_path": r"C:\Users\x\.ssh\id_rsa"}, "pregunta"),
    ("interior de .git", "Edit", {"file_path": ".git/config"}, "pregunta"),
    (".gitignore no es interior de .git", "Edit", {"file_path": ".gitignore"}, "pasa"),
    (".github no es .git", "Write", {"file_path": ".github/workflows/ci.yml"}, "pasa"),
    ("package-lock.json", "Edit", {"file_path": "package-lock.json"}, "pregunta"),
    ("composer.lock", "Write", {"file_path": "c:/p/composer.lock"}, "pregunta"),
    ("poetry.lock", "Edit", {"file_path": "poetry.lock"}, "pregunta"),
    ("package.json sí se edita", "Edit", {"file_path": "package.json"}, "pasa"),
    ("código común", "Write", {"file_path": "src/app.py"}, "pasa"),
    ("README", "Edit", {"file_path": "README.md"}, "pasa"),
    ("NotebookEdit de un notebook común", "NotebookEdit", {"notebook_path": "a.ipynb"}, "pasa"),
    ("dentro de .temporal no molesta", "Write", {"file_path": ".temporal/muestra/.env"}, "pasa"),
    ("Bash no lo ve este hook", "Bash", {"command": "echo x > .env"}, "pasa"),
    ("Read de un .env no pregunta (lo cubre otra regla)", "Read", {"file_path": ".env"}, "pasa"),
    ("sin ruta", "Write", {}, "pasa"),
]
for nombre, h_, e, esperado in CASOS:
    r_ = hook(h_, **e)
    chequear(f"hook: {nombre}", r_ == esperado, f"dio {r_}")
p = subprocess.run([sys.executable, str(HOOK)], input="esto no es json", capture_output=True, text=True)
chequear("hook: una entrada rota deja pasar", p.returncode == 0 and p.stdout.strip() == "")

sys.path.insert(0, str(RAIZ / "skills" / "senior-git" / "scripts"))
import guardia_autoria  # noqa: E402

chequear("hook registrado en HOOKS_CLAUDE con el matcher correcto", any(
    h_["script"] == "hook_archivos_protegidos.py" and h_["matcher"] == "Write|Edit|NotebookEdit" for h_ in guardia_autoria.HOOKS_CLAUDE))
chequear("el script del hook existe donde lo busca la guardia", guardia_autoria.ruta_hook_claude(
    next(h_ for h_ in guardia_autoria.HOOKS_CLAUDE if h_["script"] == "hook_archivos_protegidos.py")).exists())

# ---------- 4. regla de dos fallas y documentación ----------
senior = (RAIZ / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8")
cerrar = (RAIZ / "skills" / "cerrar-sesion" / "SKILL.md").read_text(encoding="utf-8")
readme = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("principio 17: dos fallas, barrera, y la decide el usuario", "17. **Una regla que falló dos veces" in senior and "solo se arma si el usuario dice que sí" in senior)
chequear("si el usuario dice que no, queda anotado y no se vuelve a ofrecer", "docs/pendientes.md" in senior.split("17. **")[1].split("\n")[0] and "no volver a ofrecerla" in senior)
chequear("es un punto de control", "Armar una barrera" in senior)
chequear("cerrar-sesion lo comunica y no arma nada sin respuesta", "2e. **Reglas que fallaron dos veces**" in cerrar and "No se arma nada sin su respuesta" in cerrar)
chequear("senior enlaza tokens.md y auditar-consumo", "references/tokens.md" in senior and "`auditar-consumo`" in senior)
chequear("tokens.md existe y tiene lo esencial", all(x in (RAIZ / "skills" / "senior" / "references" / "tokens.md").read_text(encoding="utf-8") for x in ("Qué se paga", "Salidas de comandos", "auditar-consumo")))
chequear("el README lo explica", "auditar-consumo" in readme and "hook_archivos_protegidos" in readme and "Cuando una regla falla dos veces" in readme and "cinco hooks globales" in readme)
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(readme) == [])
chequear("memoria: lo costoso de redescubrir y los tokens en consultar", "costoso de redescubrir" in (RAIZ / "skills" / "senior-memoria" / "SKILL.md").read_text(encoding="utf-8")
         and "tokens aproximados" in (RAIZ / "skills" / "senior-memoria" / "SKILL.md").read_text(encoding="utf-8"))
chequear("la skill nueva tiene nombre y descripción", (RAIZ / "skills" / "auditar-consumo" / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: auditar-consumo\ndescription: "))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
