import io
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
import guardia_listones as g  # noqa: E402

P = RAIZ / ".temporal" / "proy-listones"
mal = 0


def git(*a):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=P, capture_output=True, check=True)


def escribir(ruta, texto):
    f = P / ruta
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "\n" + extra))


def correr():
    h, j = g.analizar(g.leer_diff(P, "HEAD"))
    return {x[0] for x in h}, j, h


def reiniciar():
    git("checkout", "-q", "--", ".")
    git("clean", "-fdq")


import os
import stat


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(P, onerror=_forzar) if P.exists() else None
P.mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=P)
escribir("app.py", "def f(x):\n    return x + 1\n")
escribir("tests/test_app.py", "from app import f\n\n\ndef test_f():\n    assert f(1) == 2\n    assert f(2) == 3\n")
escribir("pyproject.toml", "[tool.coverage.report]\nfail_under = 85\n\n[tool.flake8]\nmax-line-length = 100\n")
escribir(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: pytest\n")
escribir(".gitleaksignore", "")
git("add", "-A")
git("commit", "-qm", "base")

ids, j, _ = correr()
chequear("sin cambios no avisa nada", ids == set() and j == 0)

# 1. umbrales
escribir("pyproject.toml", "[tool.coverage.report]\nfail_under = 60\n\n[tool.flake8]\nmax-line-length = 140\n")
ids, j, h = correr()
chequear("bajar la cobertura mínima y subir el largo de línea afloja", ids == {"LIS-UMBRAL"} and len(h) == 2, str(h))
escribir("pyproject.toml", "[tool.coverage.report]\nfail_under = 95\n\n[tool.flake8]\nmax-line-length = 80\n")
ids, j, h = correr()
chequear("endurecer los umbrales es silencioso", ids == set(), str(h))
reiniciar()

# CI que deja de bloquear
escribir(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: pytest\n        continue-on-error: true\n      - run: eslint . || true\n")
ids, j, h = correr()
chequear("continue-on-error y '|| true' en CI", ids == {"LIS-CONFIG-FLOJA"} and len(h) == 2, str(h))
reiniciar()

# 2. tests más fáciles
escribir("tests/test_app.py", "import pytest\nfrom app import f\n\n\n@pytest.mark.skip\ndef test_f():\n    assert f(1) == 2\n    assert f(2) == 3\n")
ids, j, h = correr()
chequear("test salteado", "LIS-TEST-SALTADO" in ids, str(h))
escribir("tests/test_app.py", "from app import f\n\n\ndef test_f():\n    assert f(1) == 2\n")
ids, j, h = correr()
chequear("assert que desaparece", "LIS-ASSERT-MENOS" in ids, str(h))
escribir("tests/test_app.py", "from app import f\n\n\ndef test_f():\n    assert f(1) == 2\n    assert f(5) == 6\n    assert f(2) == 3\n")
ids, j, h = correr()
chequear("más asserts no avisa", ids == set(), str(h))
reiniciar()
(P / "tests" / "test_app.py").unlink()
ids, j, h = correr()
chequear("test borrado", "LIS-TEST-BORRADO" in ids, str(h))
reiniciar()

# 3. silenciados
escribir("app.py", "def f(x):  # noqa: C901\n    return x + 1  # type: ignore\n")
ids, j, h = correr()
chequear("noqa y type: ignore", ids == {"LIS-SILENCIO"} and len(h) == 2, str(h))
escribir("app.py", "def f(x):  # noqa: C901 motivo: complejidad heredada, ver deuda\n    # motivo: la biblioteca no tiene tipos\n    return x + 1  # type: ignore\n")
ids, j, h = correr()
chequear("con motivo escrito queda justificado", ids == set() and j == 2, str((ids, j)))
reiniciar()
escribir(".gitleaksignore", "clave-de-prueba\n")
ids, j, h = correr()
chequear("línea nueva en archivo de exclusión", "LIS-EXCLUSION" in ids, str(h))
reiniciar()

# 4. a medias
escribir("app.py", "def f(x):\n    raise NotImplementedError\n\n\ndef g():\n    try:\n        f(1)\n    except Exception:\n        pass\n    # TODO arreglar\n")
ids, j, h = correr()
chequear("stub, except: pass y TODO", {"LIS-A-MEDIAS", "LIS-PENDIENTE"} <= ids, str(h))
reiniciar()

# 5. excepciones
escribir("app.py", "# atajo: sin validar el formato; cuándo: antes de abrir a clientes\ndef f(x):\n    return x\n")
ids, j, h = correr()
chequear("atajo nuevo", "LIS-EXCEPCION" in ids, str(h))
reiniciar()

# archivo nuevo sin seguimiento
escribir("nuevo.js", "// eslint-disable-next-line\nconst a = 1;\n")
ids, j, h = correr()
chequear("archivo nuevo sin seguimiento también se mira", "LIS-SILENCIO" in ids, str(h))
reiniciar()

# documentación no cuenta
escribir("NOTAS.md", "Usar `# noqa` solo con motivo. TODO: nada.\n")
ids, j, h = correr()
chequear("la documentación no cuenta", ids == set(), str(h))
reiniciar()

# informe
lineas = g.informe(h, 0)
chequear("informe sin avisos es una línea", g.informe([], 0) == ["Listones: sin controles aflojados."])
escribir("app.py", "def f(x):  # noqa\n    return x\n")
_, _, h = correr()
chequear("informe con avisos trae archivo, línea y cómo justificar", "motivo" in g.informe(h, 0)[0] and "app.py:1" in g.informe(h, 0)[1])
reiniciar()

# integración con verificar.py
import verificar  # noqa: E402


class A:
    base = "HEAD"


escribir("app.py", "def f(x):  # noqa\n    return x\n")
lin, ok = verificar.chequeo_listones(P, A())
chequear("verificar.py lo incluye y falla", (not ok) and "Listones" in lin[0], str(lin))
reiniciar()
lin, ok = verificar.chequeo_listones(P, A())
chequear("verificar.py en orden", ok, str(lin))
chequear("está registrado en CHEQUEOS", "listones" in verificar.CHEQUEOS)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
