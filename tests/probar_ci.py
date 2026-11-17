"""ci.py (senior-git): mirar los chequeos de un Pull Request, armar el flujo de CI de un proyecto y revisar el que ya tiene. Con un `gh` simulado, sin red."""
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
SCRIPT = RAIZ / "skills" / "senior-git" / "scripts" / "ci.py"
sys.path.insert(0, str(SCRIPT.parent))
import ci  # noqa: E402

P = RAIZ / ".temporal" / "proy-ci"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def correr(*args, cwd=None, env=None):
    e = {**os.environ, "SENIOR_GH": json.dumps([sys.executable, str(RAIZ / "tests" / "gh_falso.py")]), "GH_FALSO_DIR": str(P / "gh"), **(env or {})}
    r = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
    return r.returncode, r.stdout + r.stderr


def proyecto(nombre, archivos, rama="main"):
    c = P / nombre
    c.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", rama], cwd=c, check=True)
    for rel, texto in archivos.items():
        (c / rel).parent.mkdir(parents=True, exist_ok=True)
        (c / rel).write_text(texto, encoding="utf-8")
    return c


if P.exists():
    shutil.rmtree(P, onerror=_forzar)
(P / "gh").mkdir(parents=True)

FLUJO_PR = "name: Pruebas\non:\n  pull_request:\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python -m pytest\n"

# ---- estado
c_ci = proyecto("con-ci", {".github/workflows/ci.yml": FLUJO_PR})
c_sin = proyecto("sin-ci", {"app.py": "x = 1\n"})
for modo, codigo, texto in (("verde", 0, "2 de 2 en verde"), ("rojo", 1, "FALLA pruebas"), ("pendiente", 2, "pendiente pruebas")):
    rc, s = correr("estado", "--raiz", str(c_ci), env={"GH_FALSO_CHECKS": modo})
    chequear(f"estado con chequeos «{modo}» sale con {codigo} y lo cuenta", rc == codigo and texto in s, s)
chequear("con rojos avisa que no se fusione sin hablar con el usuario", "NO fusionar sin hablar con el usuario" in correr("estado", "--raiz", str(c_ci), env={"GH_FALSO_CHECKS": "rojo"})[1])
rc, s = correr("estado", "--raiz", str(c_ci), env={"GH_FALSO_CHECKS": "ninguno"})
chequear("sin chequeos pero con flujos de Pull Request: son pendientes (todavía no arrancaron), no verde", rc == 2 and "No fusionar todavía" in s, s)
rc, s = correr("estado", "--raiz", str(c_sin), env={"GH_FALSO_CHECKS": "ninguno"})
chequear("sin chequeos y sin flujos: no hay nada que esperar, y sugiere generar uno", rc == 0 and "ci.py generar" in s, s)
rc, s = correr("estado", "--raiz", str(c_ci), env={"SENIOR_GH": json.dumps([sys.executable, str(P / "no_existe.py")])})
chequear("si gh falla, no se da por verde: sale con 3 (no se pudo saber) y dice que lo decide el usuario", rc == 3 and "decide él" in s, s)
chequear("un flujo comentado no cuenta como CI de Pull Request", not ci.tiene_ci_en_pr(proyecto("comentado", {".github/workflows/x.yml": "# on:\n#   pull_request:\non:\n  push:\n"})))
chequear("resumir: un chequeo salteado cuenta como verde y uno cancelado frena",
         ci.resumir([{"name": "a", "bucket": "pass"}, {"name": "b", "bucket": "skipping"}])[1] == 0 and ci.resumir([{"name": "a", "bucket": "pass"}, {"name": "b", "bucket": "cancel"}])[1] == 2)

# ---- generar
py = proyecto("py", {"tests/probar_a.py": "import unittest\n", "requirements.txt": "requests\n"})
rc, s = correr("generar", "--raiz", str(py))
chequear("generar sin --aplicar muestra el plan y no escribe nada", rc == 0 and "nada escrito todavía" in s and "python -m unittest discover" in s and not (py / ".github").exists(), s)
rc, s = correr("generar", "--raiz", str(py), "--aplicar")
flujo = (py / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8") if (py / ".github" / "workflows" / "ci.yml").exists() else ""
chequear("con --aplicar escribe el flujo: Pull Request, permisos de solo lectura, versiones fijas y las pruebas",
         rc == 0 and "pull_request:" in flujo and "contents: read" in flujo and "actions/checkout@v4" in flujo and "pip install -r requirements.txt" in flujo
         and "python -m unittest discover -s tests -t ." in flujo, flujo)
rc, s = correr("generar", "--raiz", str(py), "--aplicar")
chequear("nunca pisa un flujo existente", rc == 1 and "no se pisa" in s, s)
chequear("el flujo generado pasa su propia auditoría", correr("auditar", "--raiz", str(py))[0] == 0)
pt = proyecto("pytest", {"tests/test_a.py": "def test_a(): pass\n", "pyproject.toml": "[tool.pytest.ini_options]\n"})
correr("generar", "--raiz", str(pt), "--aplicar")
chequear("con pytest declarado usa pytest", "python -m pytest" in (pt / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
nodo = proyecto("nodo", {"package.json": json.dumps({"scripts": {"test": "jest"}}), "package-lock.json": "{}"})
php = proyecto("php", {"composer.json": json.dumps({"require-dev": {"phpunit/phpunit": "^10"}})})
rc, s = correr("generar", "--raiz", str(nodo), "--aplicar")
chequear("Node con script test: npm ci y npm test", rc == 0 and "npm ci" in (nodo / ".github/workflows/ci.yml").read_text(encoding="utf-8") and "npm test" in (nodo / ".github/workflows/ci.yml").read_text(encoding="utf-8"), s)
rc, s = correr("generar", "--raiz", str(php), "--aplicar")
chequear("PHP con phpunit en require-dev", rc == 0 and "vendor/bin/phpunit" in (php / ".github/workflows/ci.yml").read_text(encoding="utf-8"), s)
multi = proyecto("multi", {"package.json": json.dumps({"scripts": {"test": "jest"}}), "tests/probar_a.py": "import unittest\n"})
correr("generar", "--raiz", str(multi), "--aplicar")
fm = (multi / ".github/workflows/ci.yml").read_text(encoding="utf-8")
chequear("con dos lenguajes arma un trabajo por cada uno", "  python:" in fm and "  node:" in fm, fm)
sin_test = proyecto("sin-test", {"package.json": json.dumps({"scripts": {"test": "echo \"Error: no test specified\" && exit 1"}})})
rc, s = correr("generar", "--raiz", str(sin_test), "--aplicar")
chequear("sin una forma real de correr pruebas no escribe nada y sale con error (un CI vacío da falsa seguridad)", rc == 1 and "no se escribe ningún flujo" in s and not (sin_test / ".github").exists(), s)
mas = proyecto("master", {"tests/probar_a.py": "import unittest\n"}, rama="master")
correr("generar", "--raiz", str(mas), "--aplicar", "--os", "windows-latest")
fz = (mas / ".github/workflows/ci.yml").read_text(encoding="utf-8")
chequear("detecta la rama principal (master) y respeta --os", "branches: [master]" in fz and "windows-latest" in fz, fz)
ya = proyecto("ya-tiene", {"tests/probar_a.py": "import unittest\n", ".github/workflows/otro.yml": FLUJO_PR})
rc, s = correr("generar", "--raiz", str(ya), "--aplicar")
chequear("si ya hay un flujo que corre pruebas, manda a auditar y no agrega otro", rc == 1 and "auditar" in s and not (ya / ".github/workflows/ci.yml").exists(), s)

# ---- auditar
malo = proyecto("malo", {".github/workflows/ci.yml": "on:\n  push:\njobs:\n  a:\n    steps:\n      - uses: acme/accion@master\n      - run: echo hola\n        continue-on-error: true\n      - run: pytest || true\n"})
rc, s = correr("auditar", "--raiz", str(malo))
chequear("auditar marca: sin disparo en Pull Request, continue-on-error, || true y acción por rama móvil", rc == 1 and all(x in s for x in ("no se dispara en Pull Request", "continue-on-error", "|| true", "@master")), s)
com = proyecto("comentarios", {".github/workflows/ci.yml": FLUJO_PR + "      # - run: pytest || true\n      # continue-on-error: true\n"})
chequear("auditar ignora las líneas comentadas", correr("auditar", "--raiz", str(com))[0] == 0, correr("auditar", "--raiz", str(com))[1])
sinp = proyecto("sin-pruebas", {".github/workflows/ci.yml": "on:\n  pull_request:\njobs:\n  a:\n    steps:\n      - run: echo hola\n"})
chequear("auditar avisa de un flujo que no corre pruebas", "no corre pruebas" in correr("auditar", "--raiz", str(sinp))[1])
chequear("auditar sin flujos lo dice y sugiere generar", "ci.py generar" in correr("auditar", "--raiz", str(c_sin))[1])

# ---- el método lo cablea
sk = (RAIZ / "skills" / "senior-git" / "SKILL.md").read_text(encoding="utf-8")
ref_ci = (RAIZ / "skills" / "senior-git" / "references" / "ci.md").read_text(encoding="utf-8")
mc = (RAIZ / "skills" / "senior" / "references" / "metodo-completo.md").read_text(encoding="utf-8")
chequear("senior-git manda a mirar los chequeos antes de proponer una fusión y explica generar y auditar", all(x in sk.lower() for x in ("ci.py estado", "ci.py generar", "ci.py auditar", "antes de proponer fusionar")) and "references/ci.md" in sk and "ci.py generar" in ref_ci, sk[:100])
chequear("el método completo lo repite en el paso de la fusión", "ci.py estado" in mc)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
