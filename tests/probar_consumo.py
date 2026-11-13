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
sys.path.insert(0, str(RAIZ / "skills" / "senior-memoria" / "scripts"))
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
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


# ---------- 2. el índice de senior es la trazabilidad; consultar por términos es de Token Diet ----------
D = BASE / "con-docs"
escribir(D / "docs" / "requisitos" / "negocio" / "RN-001.md",
         "---\nid: RN-001\ntipo: requisito\ntitulo: Descuento por volumen\nresumen: Descuento\ntags: [descuento]\n---\n\n" + "texto " * 400)
indexar_docs.cmd_indexar(D, D / "docs")
salida = io.StringIO()
real = sys.stdout
sys.stdout = salida
indexar_docs.cmd_vecinos(D / "docs", "RN-001")
sys.stdout = real
s = salida.getvalue()
chequear("vecinos indica los tokens aproximados de abrir el documento", "tokens al abrirlo" in s and "RN-001" in s, s)
indice = (D / "docs" / "INDEX.md").read_text(encoding="utf-8")
chequear("el índice generado no lleva esos números (sigue siendo determinista)", "tokens al abrirlo" not in indice)
chequear("un símbolo no se mide", indexar_docs.tokens_al_abrir(D, {"tipo": "simbolo", "ruta": "x.py"}) is None)
chequear("sin raíz no se mide", indexar_docs.tokens_al_abrir(None, {"tipo": "requisito", "ruta": "x"}) is None)
chequear("consultar por términos ya no es de senior (lo hace Token Diet)", not hasattr(indexar_docs, "cmd_consultar"))

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

chequear("el hook de archivos protegidos corre dentro del despachador registrado, para Write, Edit y NotebookEdit", any(
    h_["script"] == "hook_senior.py" and all(t in h_["matcher"] for t in ("Write", "Edit", "NotebookEdit")) for h_ in guardia_autoria.HOOKS_CLAUDE)
    and any(s == "hook_archivos_protegidos.py" and {"Write", "Edit", "NotebookEdit"} <= t for _, s, t in __import__("hook_senior").HOOKS))
chequear("el script del despachador existe donde lo busca la guardia", guardia_autoria.ruta_hook_claude(
    next(h_ for h_ in guardia_autoria.HOOKS_CLAUDE if h_["script"] == "hook_senior.py")).exists())

# ---------- 4. regla de dos fallas y documentación ----------
senior = (RAIZ / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8")
cerrar = (RAIZ / "skills" / "cerrar-sesion" / "SKILL.md").read_text(encoding="utf-8")
readme = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("principio 17: dos fallas, barrera, y la decide el usuario", "17. **Una regla que falló dos veces" in senior and "solo se arma si el usuario dice que sí" in senior)
chequear("si el usuario dice que no, queda anotado y no se vuelve a ofrecer", "docs/pendientes.md" in senior.split("17. **")[1].split("\n")[0] and "no volver a ofrecerla" in senior)
chequear("es un punto de control", "Armar una barrera" in senior)
chequear("cerrar-sesion lo comunica y no arma nada sin respuesta", "2e. **Reglas que fallaron dos veces**" in cerrar and "No se arma nada sin su respuesta" in cerrar)
chequear("senior apunta a la guía de Token Diet y ya no trae la suya", "references/tokens.md` de Token Diet" in senior and not (RAIZ / "skills" / "senior" / "references" / "tokens.md").exists())
chequear("el README lo explica", "hook_archivos_protegidos" in readme and "Cuando una regla falla dos veces" in readme and "dos hooks globales" in readme)
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(readme) == [])
chequear("memoria: lo costoso de redescubrir y los tokens en consultar", "costoso de redescubrir" in (RAIZ / "skills" / "senior-memoria" / "SKILL.md").read_text(encoding="utf-8")
         and "tokens aproximados" in (RAIZ / "skills" / "senior-memoria" / "SKILL.md").read_text(encoding="utf-8"))
chequear("la skill de auditoría ya no está en el paquete (la tiene Token Diet)", not (RAIZ / "skills" / "auditar-consumo").exists() and "`auditar-consumo`" not in readme)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
