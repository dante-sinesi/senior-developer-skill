#!/usr/bin/env python3
"""La barrera de documentación: `gh pr create` en un proyecto mediano o grande no pasa si cambia código sin tocar la documentación."""
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
CHAT = RAIZ / "skills" / "senior" / "scripts" / "hook_permisos_chat.py"
BASE = RAIZ / ".temporal" / "proy-docs-pr"
P = BASE / "p"
LINEA = "Documentación: sin cambios porque solo se corrige un cálculo ya descrito"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def git(*args):
    subprocess.run(["git", "-c", "user.name=x", "-c", "user.email=x@example.com", "-c", "core.hooksPath=/dev/null", *args], cwd=P, check=True, capture_output=True)


def escribir(ruta, texto):
    f = P / ruta
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


def preparar(escala="grande"):
    shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
    P.mkdir(parents=True)
    git("init", "-q", "-b", "main")
    escribir("docs/ESTADO.md", f"# Estado\n\n**Escala del proyecto:** {escala}\n" if escala else "# Estado\n")
    escribir("docs/requisitos/funcional/RF-001.md", "# RF-001\n")
    escribir("src/cobro.py", "def total(x):\n    return x\n")
    git("add", "-A")
    git("commit", "-qm", "chore: base")


def rama(nombre, archivos, mensaje="cambio", commitear=True):
    git("checkout", "-q", "main")
    git("checkout", "-q", "-B", nombre)
    for ruta, texto in archivos.items():
        escribir(ruta, texto)
    if commitear:
        git("add", "-A")
        git("commit", "-qm", mensaje)


def correr(script, datos):
    entorno = {**os.environ, "CLAUDE_PROJECT_DIR": str(P), "SENIOR_TOKEN_DIET_HOME": str(BASE / "casa"), "SENIOR_HOOK_DEPURAR": "1"}
    r = subprocess.run([sys.executable, str(script)], input=json.dumps(datos).encode("utf-8"), capture_output=True, env=entorno, cwd=BASE, timeout=120)
    salida, error = r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")
    if "Traceback" in error:
        raise RuntimeError(error[-800:])
    return r.returncode, salida, error


def pr(comando, herramienta="Bash", cwd=None):
    codigo, salida, error = correr(DESPACHADOR, {"tool_name": herramienta, "tool_input": {"command": comando}, "cwd": str(cwd or P), "session_id": "s", "hook_event_name": "PreToolUse"})
    if codigo == 2:
        return "deny", error
    if not salida.strip():
        return "pasa", ""
    h = json.loads(salida)["hookSpecificOutput"]
    return h.get("permissionDecision", "pasa"), h.get("permissionDecisionReason") or h.get("additionalContext", "")


def crear(titulo, cuerpo="Qué cambia", extra=""):
    return pr(f'gh pr create --title "{titulo}" --body "{cuerpo}" {extra}')


CAMBIO = {"src/cobro.py": "def total(x):\n    return x * 2\n"}

preparar()
rama("f", CAMBIO, "feat: duplica")
d, r = crear("feat(cobro): duplica el total")
chequear("un feat sin documentación se bloquea", d == "deny" and "src/cobro.py" in r and "docs/requisitos" in r, (d, r))
chequear("el mensaje no manda a esperar y nombra la autorización del usuario", "/permitir-sin-docs" in r and "esperá" not in r, r)
chequear("la línea de justificación no salva a un feat", crear("feat: duplica", LINEA)[0] == "deny")
chequear("también con PowerShell, con gh.exe y después de otro comando", pr('git push; gh.exe pr create -t "feat: x" -b "y"', "PowerShell")[0] == "deny")
chequear("con `cd` desde otra carpeta se mira ese proyecto", pr(f'cd "{P.as_posix()}" && gh pr create -t "feat: x" -b "y"', cwd=BASE)[0] == "deny")
chequear("sin --title manda el tipo de los commits", pr("gh pr create --fill")[0] == "deny")
chequear("otro comando de gh no se mira", pr("gh pr view 3")[0] == "pasa" and pr("gh pr list")[0] == "pasa")

for carpeta in ("requisitos/funcional", "casos-de-uso", "secuencias", "decisiones", "diagramas"):
    rama("doc", {**CAMBIO, f"docs/{carpeta}/nuevo.md": "# nuevo\n"}, "feat: con docs")
    chequear(f"pasa si la rama toca docs/{carpeta}", crear("feat: con docs")[0] == "pasa", crear("feat: con docs"))
rama("estado", {**CAMBIO, "docs/ESTADO.md": "# Estado\n\n**Escala del proyecto:** grande\n\nhecho\n"}, "feat: solo estado")
chequear("tocar solo ESTADO no alcanza", crear("feat: solo estado")[0] == "deny")

rama("fix", CAMBIO, "fix: cálculo")
for tipo in ("fix", "refactor", "perf", "test", "chore", "style"):
    chequear(f"{tipo} con la línea pasa", crear(f"{tipo}: ajuste", f"Qué cambia\n\n{LINEA}")[0] == "pasa")
d, r = crear("fix: cálculo")
chequear("fix sin la línea se bloquea y la pide", d == "deny" and "Documentación: sin cambios porque" in r, (d, r))
chequear("la línea sin motivo no vale", crear("fix: cálculo", "Documentación: sin cambios porque")[0] == "deny")
escribir(".temporal/cuerpo.md", f"## Qué cambia\n\n{LINEA}\n")
chequear("la línea puede venir en --body-file", pr('gh pr create --title "fix: cálculo" --body-file .temporal/cuerpo.md')[0] == "pasa")
rama("sintipo", CAMBIO, "ajusta el calculo")
d, r = crear("Ajusta el cálculo")
chequear("si no se puede saber el tipo, pasa y lo dice", d == "pasa" and "tipo" in r, (d, r))

# lo que agrega superficie nueva no se salva con ninguna etiqueta
rama("nuevo", {"src/recibo.py": "def recibo():\n    return 1\n"}, "fix: recibo")
d, r = crear("fix: recibo", LINEA)
chequear("un archivo de código nuevo invalida la excepción", d == "deny" and "src/recibo.py" in r, (d, r))
for nombre, texto in (("ruta de express", "app.post('/cobros', cobrar)\n"), ("ruta de laravel", "Route::get('/cobros', [C::class, 'x']);\n"),
                      ("ruta de flask", "@app.route('/cobros')\n"), ("pantalla", '<Route path="/cobros" element={<C/>} />\n'), ("comando", "sub.add_parser('cobrar')\n")):
    rama("superficie", {"src/cobro.py": "def total(x):\n    return x\n" + texto}, "fix: x")
    chequear(f"agregar una {nombre} invalida la excepción", crear("fix: x", LINEA)[0] == "deny", crear("fix: x", LINEA))
rama("pruebas", {"tests/test_cobro.py": "def test_a():\n    pass\n", "README.md": "# x\n", "docs/pendientes.md": "- [ ] a\n"}, "test: cubre")
chequear("sin cambios de código (solo tests y texto) pasa sin línea", crear("test: cubre")[0] == "pasa" and crear("feat: solo texto")[0] == "pasa")

# `git commit` en el mismo comando: se mira lo que está por commitearse
rama("sin-commit", CAMBIO, commitear=False)
chequear("si el commit va en el mismo comando, cuenta lo que está sin commitear",
         pr('git add -A && git commit -m "feat: x" && gh pr create -t "feat: x" -b "y"')[0] == "deny")
git("checkout", "-q", "--", ".")

# alcance: escala, método y fallas
rama("f", CAMBIO, "feat: duplica")
d, r = crear("feat: x", extra="--base no-existe")
chequear("si no se puede determinar el diff, pasa y lo dice", d == "pasa" and "diff" in r, (d, r))

# autorizaciones del usuario
correr(CHAT, {"prompt": "/permitir-sin-docs", "cwd": str(P)})
chequear("/permitir-sin-docs deja pasar una vez", crear("feat: x")[0] == "pasa")
chequear("y se gasta", crear("feat: x")[0] == "deny")
correr(CHAT, {"prompt": "/permitir-sin-docs", "cwd": str(P)})
rama("doc", {**CAMBIO, "docs/casos-de-uso/CU.md": "# CU\n"}, "feat: con docs")
crear("feat: con docs")
rama("f", CAMBIO, "feat: duplica")
chequear("no se gasta en un PR que igual pasaba", crear("feat: x")[0] == "pasa")
correr(CHAT, {"prompt": "/docs-modo aviso", "cwd": str(P)})
d, r = crear("feat: x")
chequear("/docs-modo aviso deja pasar y lo advierte", d == "pasa" and "documentación" in r, (d, r))

for escala, esperado in (("mediano", "deny"), ("pequeño", "pasa"), ("", "pasa")):
    preparar(escala)
    rama("f", CAMBIO, "feat: duplica")
    chequear(f"escala «{escala or 'sin declarar'}»: {esperado}", crear("feat: x")[0] == esperado)
preparar()
(P / "docs" / "ESTADO.md").unlink()
git("commit", "-qam", "chore: sin estado")
rama("f", CAMBIO, "feat: duplica")
chequear("un proyecto sin docs/ESTADO.md no se toca", crear("feat: x") == ("pasa", ""))

shutil.rmtree(BASE, onerror=_forzar)
print("\nfallos:", mal)
sys.exit(1 if mal else 0)
