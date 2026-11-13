import os
import subprocess
import sys
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
R0 = RAIZ / "skills"
ATAJOS = R0 / "senior" / "scripts" / "atajos.py"
VERIFICAR = R0 / "senior" / "scripts" / "verificar.py"

R = RAIZ / ".temporal" / "proy-revision"
import stat


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(R, onerror=_forzar) if R.exists() else None
R.mkdir(parents=True)
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))

env = {**os.environ, "GIT_CONFIG_GLOBAL": str(R / "nada")}


def g(*a):
    return subprocess.run(["git", *a], cwd=R, capture_output=True, text=True, encoding="utf-8", env=env)


def py(script, *a):
    p = subprocess.run([sys.executable, str(script), *a, "--raiz", str(R)] if script is not VERIFICAR else [sys.executable, str(script), *a],
                       cwd=R, capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, (p.stdout + p.stderr).strip()


g("init", "-q")
g("config", "user.name", "prueba")
g("config", "user.email", "p@x.test")
(R / "app").mkdir()
(R / "app" / "precios.py").write_text(
    "def calcular_total(items):\n    total = 0\n    for i in items:\n        total += i\n    return total\n", encoding="utf-8")
(R / "app" / "carrito.py").write_text("from precios import calcular_total\n\ndef cobrar(items):\n    return calcular_total(items)\n", encoding="utf-8")
(R / "README.md").write_text("# demo\n\nLo usan miles de usuarios a la vez.\n", encoding="utf-8")
g("add", ".")
g("commit", "-q", "-m", "inicial")

# --- atajos
(R / "app" / "carga.py").write_text(
    "# atajo: lee todo el archivo en memoria; cuándo: si pasa de 50 MB\n"
    "# atajo: sin paginación, 200 filas como máximo\n"
    "x = 1  # atajo: orden fijo; cuándo: cuando haya otro cliente\n", encoding="utf-8")
c, s = py(ATAJOS)
print("1) atajos:", c, "\n  ", s.replace("\n", "\n   "))
c, s = py(ATAJOS, "--escribir")
print("2) escribir:", (R / "docs" / "atajos.md").exists(), "| SIN DISPARADOR en el archivo:", "SIN DISPARADOR" in (R / "docs" / "atajos.md").read_text(encoding="utf-8"))
c, s = py(VERIFICAR, "deuda", "--raiz", str(R))
print("3) verificar deuda:", c, "|", [l for l in s.splitlines() if "tajos" in l][:1])

chequear("los atajos sin disparador se señalan", "SIN DISPARADOR" in (R / "docs" / "atajos.md").read_text(encoding="utf-8"))
for retirado in ("senior/scripts/texto.py", "senior/scripts/comentarios.py", "senior/scripts/impacto.py", "revisar-cambio/scripts/contexto.py", "senior-relevar/scripts/relevar.py", "senior-refactor/scripts/duplicados.py"):
    chequear(f"{retirado} ya no está en el paquete (lo hace Token Diet)", not (R0 / retirado).exists())
print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
