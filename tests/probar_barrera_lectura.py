#!/usr/bin/env python3
"""La barrera de lectura: en un proyecto con docs/ESTADO.md no se edita código sin haber leído antes el estado y los requisitos."""
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
DESPACHADOR = RAIZ / "skills" / "senior" / "scripts" / "hook_senior.py"
BARRERA = RAIZ / "skills" / "senior" / "scripts" / "hook_lectura_previa.py"
CHAT = RAIZ / "skills" / "senior" / "scripts" / "hook_permisos_chat.py"
CARGAR = RAIZ / "skills" / "senior-docs" / "scripts" / "cargar_estado.py"
BASE = RAIZ / ".temporal" / "proy-barrera"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def escribir(ruta, texto="x\n"):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")


def proyecto(nombre, *documentos):
    p = BASE / nombre
    p.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=p, check=True)
    for d in ("docs/ESTADO.md", *documentos):
        escribir(p / d, f"# {d}\n")
    escribir(p / "src" / "a.py", "x = 1\n")
    return p


def correr(script, datos, sesion_en=None, *args):
    entorno = {**os.environ, "CLAUDE_PROJECT_DIR": str(sesion_en or BASE), "SENIOR_TOKEN_DIET_HOME": str(BASE / "casa"), "USERPROFILE": str(BASE / "casa")}
    r = subprocess.run([sys.executable, str(script), *args], input=(datos if isinstance(datos, str) else json.dumps(datos)).encode("utf-8"),
                       capture_output=True, env=entorno, cwd=BASE, timeout=120)
    return r.returncode, r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")


def llamar(herramienta, archivo, sesion="s1", agente=None, sesion_en=None, script=DESPACHADOR):
    campo = "notebook_path" if herramienta == "NotebookEdit" else "file_path"
    entrada = {campo: str(archivo)}
    if herramienta == "Write":
        entrada["content"] = "y = 2\n"
    datos = {"session_id": sesion, "tool_name": herramienta, "tool_input": entrada, "cwd": str(sesion_en or BASE), "hook_event_name": "PreToolUse"}
    if agente:
        datos["agent_id"] = agente
    return correr(script, datos, sesion_en)


def decision(resultado):
    codigo, salida, error = resultado
    if "Traceback" in error:
        raise RuntimeError(error[-600:])
    if not salida.strip():
        return "pasa", ""
    h = json.loads(salida)["hookSpecificOutput"]
    return h.get("permissionDecision", "pasa"), h.get("permissionDecisionReason") or h.get("additionalContext", "")


def edita(p, ruta="src/a.py", **kw):
    return decision(llamar(kw.pop("herramienta", "Edit"), p / ruta, **kw))


def lee(p, ruta, **kw):
    return decision(llamar("Read", p / ruta, **kw))


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
(BASE / "casa").mkdir(parents=True)

# 1. solo estado
p = proyecto("simple")
d, razon = edita(p)
chequear("editar sin leer el estado se bloquea", d == "deny", (d, razon))
chequear("el mensaje dice qué leer, con qué herramienta y que no espere a nadie",
         (p / "docs" / "ESTADO.md").as_posix() in razon and "herramienta Read" in razon and "esperar" in razon, razon)
chequear("Write y NotebookEdit también", edita(p, "src/nuevo.ts", herramienta="Write")[0] == "deny" and edita(p, "src/n.ipynb", herramienta="NotebookEdit")[0] == "deny")
chequear("leer el estado pasa", lee(p, "docs/ESTADO.md")[0] == "pasa")
chequear("y entonces se puede editar", edita(p)[0] == "pasa", edita(p))
chequear("un subagente tiene que leer por su cuenta", edita(p, agente="ag1")[0] == "deny")
lee(p, "docs/ESTADO.md", agente="ag1")
chequear("después de leer, el subagente edita", edita(p, agente="ag1")[0] == "pasa")
chequear("otra sesión tiene que leer", edita(p, sesion="s2")[0] == "deny")
estado = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=p, capture_output=True, text=True).stdout
chequear("las marcas de lectura no ensucian el repositorio", "senior-lecturas" not in estado, estado)

# 2. con índice o requisitos hace falta además uno de ellos
q = proyecto("conreq", "docs/INDEX.md", "docs/requisitos/funcional/RF-001.md", "docs/casos-de-uso/CU-01.md")
lee(q, "docs/ESTADO.md")
d, razon = edita(q)
chequear("con requisitos, el estado solo no alcanza", d == "deny" and "INDEX.md" in razon and "ESTADO.md" not in razon, (d, razon))
for i, doc in enumerate(("docs/INDEX.md", "docs/requisitos/funcional/RF-001.md", "docs/casos-de-uso/CU-01.md")):
    lee(q, "docs/ESTADO.md", sesion=f"r{i}")
    lee(q, doc, sesion=f"r{i}")
    chequear(f"alcanza con el estado y {doc}", edita(q, sesion=f"r{i}")[0] == "pasa")
v = proyecto("vacios")
escribir(v / "docs" / "requisitos" / "funcional" / ".gitkeep", "")
lee(v, "docs/ESTADO.md")
chequear("las carpetas de requisitos vacías no se exigen", edita(v)[0] == "pasa")

# 3. lo que no alcanza
for ruta in ("docs/ESTADO.md", "docs/diagramas/clases.md", "tests/test_a.py", "src/a.test.js", "src/a_test.go", ".temporal/x.py", "README.md", "datos.json"):
    chequear(f"no bloquea {ruta}", edita(p, ruta, sesion="libre")[0] == "pasa")
sin = BASE / "sin-metodo"
escribir(sin / "src" / "a.py")
chequear("un proyecto sin docs/ESTADO.md no se toca", edita(sin, sesion="libre")[0] == "pasa" and not (sin / ".temporal").exists())

# 4. compactar y limpiar borran las marcas; retomar no
for fuente, esperado in (("resume", "pasa"), ("compact", "deny"), ("clear", "deny")):
    lee(p, "docs/ESTADO.md", sesion="c1")
    correr(CARGAR, {"session_id": "c1", "source": fuente, "cwd": str(p)}, p, "--hook")
    chequear(f"después de «{fuente}», editar {esperado}", edita(p, sesion="c1")[0] == esperado)
lee(p, "docs/ESTADO.md", sesion="c2")
lee(p, "docs/ESTADO.md", sesion="c2", agente="hijo")
lee(p, "docs/ESTADO.md", sesion="c20")
correr(CARGAR, {"session_id": "c2", "source": "compact", "cwd": str(BASE)}, BASE, "--hook")
chequear("una sesión abierta por encima del proyecto también las borra, con las de sus subagentes",
         edita(p, sesion="c2")[0] == "deny" and edita(p, sesion="c2", agente="hijo")[0] == "deny")
chequear("sin borrar las de otra sesión de nombre parecido", edita(p, sesion="c20")[0] == "pasa")

# 5. el usuario puede dejarlo en aviso
r = correr(CHAT, {"prompt": "/docs-modo aviso", "cwd": str(p)}, p)
chequear("/docs-modo aviso se aplica desde el chat", "aviso" in r[1], r)
d, texto = edita(p, sesion="m1", sesion_en=p)
chequear("en modo aviso deja pasar y lo dice", d == "pasa" and "ESTADO.md" in texto, (d, texto))
chequear("una sola vez por sesión", edita(p, sesion="m1", sesion_en=p) == ("pasa", ""))
chequear("el aviso puesto en la sesión abierta por encima también vale", (correr(CHAT, {"prompt": "/docs-modo aviso", "cwd": str(BASE)}, BASE), edita(q, sesion="m2"))[1][0] == "pasa")
correr(CHAT, {"prompt": "/docs-modo exigir", "cwd": str(BASE)}, BASE)
correr(CHAT, {"prompt": "/docs-modo exigir", "cwd": str(p)}, p)
chequear("/docs-modo exigir vuelve a bloquear", edita(p, sesion="m3", sesion_en=p)[0] == "deny")
r = correr(CHAT, {"prompt": "/docs-modo cualquiera", "cwd": str(p)}, p)
chequear("un modo inválido se explica", "exigir o aviso" in r[1], r[1])

# 6. ante la duda, deja pasar
chequear("sin sesión no bloquea", edita(p, sesion="")[0] == "pasa")
for nombre, datos in (("basura", "no es json"), ("lista", "[1]"), ("sin ruta", {"session_id": "z", "tool_name": "Edit", "tool_input": {}})):
    codigo, salida, error = correr(BARRERA, datos)
    chequear(f"entrada {nombre}: no frena", codigo == 0 and not salida.strip() and "Traceback" not in error, (codigo, salida, error[-200:]))

shutil.rmtree(BASE, onerror=_forzar)
print("\nfallos:", mal)
sys.exit(1 if mal else 0)
