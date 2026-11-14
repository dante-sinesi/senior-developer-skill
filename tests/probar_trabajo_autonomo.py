"""Trabajo autónomo: el script hace cumplir lo que el texto promete. Rama auto/ propia, punto de guardado solo con tests en verde, alto tras tres fallos seguidos,
bloqueos que se anotan sin esperar, informe al cerrar, y nada que suba, fusione o toque main."""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SCRIPT = RAIZ / "skills" / "trabajo-autonomo" / "scripts" / "autonomo.py"
BASE = RAIZ / ".temporal" / "proy-autonomo"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
BASE.mkdir(parents=True)


def git(c, *a):
    r = subprocess.run(["git", *a], cwd=c, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout + r.stderr).strip()


def auto(c, *a):
    r = subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(c), *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def repo(nombre, sucio=False):
    c = BASE / nombre
    c.mkdir()
    git(c, "init", "-q", "-b", "main")
    git(c, "config", "user.name", "prueba")
    git(c, "config", "user.email", "p@x.test")
    (c / ".gitignore").write_text(".temporal/\n", encoding="utf-8")
    (c / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    git(c, "add", "-A")
    git(c, "commit", "-q", "-m", "chore: base")
    if sucio:
        (c / "app.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    return c


VERDE = f'"{sys.executable}" -c "import sys; sys.exit(0)"'
ROJO = f'"{sys.executable}" -c "import sys; sys.exit(1)"'

# 1. iniciar
c = repo("a")
rc, s = auto(c, "iniciar", "Mi Tema!", "--comando-tests", VERDE, "--max-puntos", "3")
rama = git(c, "branch", "--show-current")
chequear("iniciar crea la rama auto/<tema>-<fecha> y la deja activa", rc == 0 and rama.startswith("auto/mi-tema-"), (rc, s, rama))
chequear("crea el plan con criterios de terminado en .temporal/autonomo/", (c / ".temporal" / "autonomo" / "mi-tema" / "plan.md").exists() and "Criterios de terminado" in (c / ".temporal" / "autonomo" / "mi-tema" / "plan.md").read_text(encoding="utf-8"))
chequear("dice qué está autorizado y qué no", "No autorizado: push, PR, fusión" in s, s)
rc2, s2 = auto(c, "iniciar", "otro")
chequear("no deja iniciar una segunda sesión activa", rc2 == 1 and "ya hay una sesión autónoma activa" in s2, s2)
sucio = repo("b", sucio=True)
rc, s = auto(sucio, "iniciar", "tema")
chequear("se niega a iniciar con cambios sin commitear (no mezcla lo del usuario)", rc == 1 and "cambios sin commitear" in s and git(sucio, "branch", "--show-current") == "main", (rc, s))

# 2. punto de guardado
(c / "app.py").write_text("def f():\n    return 10\n", encoding="utf-8")
rc, s = auto(c, "punto", "feat(app): devuelve diez")
chequear("el punto guarda un commit local con tests en verde", rc == 0 and "Punto de guardado 1/3" in s and "feat(app): devuelve diez" in git(c, "log", "--oneline", "-1"), (rc, s))
chequear("el commit queda en la rama auto/ y main no cambia", git(c, "rev-parse", "main") != git(c, "rev-parse", "HEAD") and git(c, "log", "--oneline", "main", "-1").endswith("chore: base"))
(c / "app.py").write_text("def f():\n    return 11\n", encoding="utf-8")
rc, s = auto(c, "punto", "arreglé algo")
chequear("rechaza un mensaje que no es Conventional Commits", rc == 1 and "Conventional Commits" in s, s)
rc, s = auto(c, "punto", "fix(app): devuelve once")
chequear("acepta un mensaje convencional", rc == 0, s)
rc, s = auto(c, "punto", "fix(app): sin cambios")
chequear("sin cambios no hace nada", rc == 1 and "no hay cambios" in s, s)

# 3. tests en rojo: no se guarda, y a los tres fallos seguidos avisa ALTO
d = repo("c")
auto(d, "iniciar", "rojo", "--comando-tests", ROJO)
(d / "app.py").write_text("def f():\n    return 99\n", encoding="utf-8")
antes = git(d, "rev-parse", "HEAD")
for i in (1, 2, 3):
    rc, s = auto(d, "punto", "feat(app): intento")
chequear("con tests en rojo no se guarda ningún punto", git(d, "rev-parse", "HEAD") == antes and rc == 1 and "Tests en rojo" in s, s)
chequear("a los tres fallos seguidos avisa ALTO y manda a anotar un bloqueo", "ALTO" in s and "bloqueo" in s, s)
rc, s = auto(d, "estado")
chequear("el estado también avisa que hay que parar", "ALTO" in s and "3 fallos seguidos" in s, s)

# 4. bloqueo: se anota en docs/pendientes.md y no espera
rc, s = auto(d, "bloqueo", "¿Redondeo hacia arriba o al más cercano?", "--opciones", "arriba | cercano", "--recomendacion", "al más cercano: es lo habitual")
pend = (d / "docs" / "pendientes.md").read_text(encoding="utf-8") if (d / "docs" / "pendientes.md").exists() else ""
chequear("un bloqueo se anota con pregunta, opciones y recomendación", rc == 0 and "Redondeo hacia arriba" in pend and "Opciones: arriba | cercano" in pend and "Recomendación: al más cercano" in pend, pend)
chequear("el mensaje manda a seguir con otro paso sin esperar", "No se espera" in s and "otro paso" in s, s)
rc, s = auto(d, "estado")
chequear("un bloqueo reinicia la cuenta de fallos seguidos", "0 fallos seguidos" in s and "1 bloqueos" in s, s)

# 5. límite de puntos
rc, s = auto(c, "punto", "fix(app): uno más")
(c / "app.py").write_text("def f():\n    return 12\n", encoding="utf-8")
rc, s = auto(c, "punto", "fix(app): otro")
(c / "app.py").write_text("def f():\n    return 13\n", encoding="utf-8")
rc, s = auto(c, "punto", "fix(app): y otro")
chequear("al llegar al máximo de puntos se niega y manda a cerrar", rc == 1 and "máximo de 3" in s, s)

# 6. no guarda fuera de la rama de la sesión
git(c, "checkout", "-q", "--", "app.py")
git(c, "switch", "-q", "main")
(c / "app.py").write_text("def f():\n    return 77\n", encoding="utf-8")
rc, s = auto(c, "punto", "fix(app): desde main")
chequear("no hace puntos de guardado desde main ni desde otra rama", rc == 1 and "solo se hacen en la rama auto/" in s and "77" in (c / "app.py").read_text(encoding="utf-8"), s)
git(c, "checkout", "-q", "--", "app.py")
git(c, "switch", "-q", rama)

# 7. cerrar: informe y nada subido
rc, s = auto(c, "cerrar")
informe = (c / ".temporal" / "autonomo" / "mi-tema" / "informe.md").read_text(encoding="utf-8") if (c / ".temporal" / "autonomo" / "mi-tema" / "informe.md").exists() else ""
chequear("cerrar escribe el informe con commits, criterios, bloqueos y cómo revisarlo", rc == 0 and all(x in informe for x in ("Qué se hizo", "Criterios de terminado", "Bloqueos", "Cómo revisarlo", "feat(app): devuelve diez")), informe[:300])
chequear("el informe aclara que no se subió, abrió ni fusionó nada", "Nada de eso se hizo" in informe and "push" in informe)
chequear("cerrar deja la sesión inactiva", not (c / ".temporal" / "autonomo" / "ACTIVO").exists() and "No hay una sesión" in auto(c, "estado")[1])

# 8. el script no tiene ninguna operación que suba, fusione o reescriba
fuente = SCRIPT.read_text(encoding="utf-8")
chequear("el script no contiene push, merge, rebase, reset, tag ni --force", not any(x in fuente for x in ('"push"', '"merge"', '"rebase"', '"reset"', '"tag"', "--force", "--amend", "--no-verify")))

# 9. la skill: solo con el comando y con la autorización escrita
sk = (RAIZ / "skills" / "trabajo-autonomo" / "SKILL.md").read_text(encoding="utf-8")
chequear("la skill no se activa sola (disable-model-invocation)", "disable-model-invocation: true" in sk.split("---")[1])
chequear("la skill declara la autorización exacta y lo que no cubre", "## Autorización (exacta y acotada)" in sk and "No cubre" in sk and "push, Pull Request, fusión" in sk)
chequear("la skill manda a no esperar al usuario ante un bloqueo", "no se pregunta y no se espera" in sk)

sys.exit(1 if mal else 0)
