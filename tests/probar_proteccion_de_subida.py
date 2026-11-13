"""Protección de subida de GitHub: `secretos.py github` distingue repositorio público y privado y puede activarla; `/inicializar-repositorio` la activa en los
públicos nuevos; y Claude no puede saltear los hooks de git (`--no-verify`, `-n` de commit, `core.hooksPath`)."""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SECRETOS = RAIZ / "skills" / "senior" / "scripts" / "secretos.py"
INICIALIZAR = RAIZ / "skills" / "inicializar-repositorio" / "scripts" / "inicializar_repo.py"
HOOK = RAIZ / "skills" / "senior" / "scripts" / "hook_secretos_claude.py"
BASE = RAIZ / ".temporal" / "proy-proteccion"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
(BASE / "gh").mkdir(parents=True)
ENV = {**os.environ, "SENIOR_GH": json.dumps([sys.executable, str(RAIZ / "tests" / "gh_falso.py")]), "GH_FALSO_DIR": str(BASE / "gh"), "GIT_TERMINAL_PROMPT": "0"}
GH = [sys.executable, str(RAIZ / "tests" / "gh_falso.py")]
ESTADO = BASE / "gh" / "estado.json"


def gh(*a):
    return subprocess.run([*GH, *a], env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")


def repo_local(nombre, visibilidad):
    """Un repositorio remoto de mentira y una carpeta local cuyo origin apunta a él."""
    gh("repo", "create", f"dante-prueba/{nombre}", visibilidad)
    bare = json.loads(ESTADO.read_text(encoding="utf-8"))["repos"][f"dante-prueba/{nombre}"]["bare"]
    c = BASE / nombre
    c.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=c)
    subprocess.run(["git", "remote", "add", "origin", bare], cwd=c)
    return c


def correr(script, c, *args, env=None):
    r = subprocess.run([sys.executable, str(script), *args, "--raiz", str(c)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=c, env=env or ENV)
    return r.returncode, r.stdout + r.stderr


# 1. estado en un repositorio público (GitHub lo activa por defecto)
pub = repo_local("publico", "--public")
rc, s = correr(SECRETOS, pub, "github")
chequear("público: escaneo y protección activos, código 0", rc == 0 and "escaneo de secretos enabled; protección de subida enabled" in s, (rc, s))

# 2. público con la protección apagada: falla, sugiere el comando y --activar la enciende
est = json.loads(ESTADO.read_text(encoding="utf-8"))
est["repos"]["dante-prueba/publico"]["sin_proteccion"] = True
ESTADO.write_text(json.dumps(est), encoding="utf-8")
rc, s = correr(SECRETOS, pub, "github")
chequear("público con la protección apagada falla y propone `--activar`", rc == 1 and "--activar" in s, (rc, s))
rc, s = correr(SECRETOS, pub, "github", "--activar")
chequear("--activar la enciende y lo comprueba", rc == 0 and "Activada" in s and "protección de subida enabled" in s, (rc, s))
rc, s = correr(SECRETOS, pub, "github")
chequear("después de activarla el estado queda en verde", rc == 0, (rc, s))

# 3. privado: GitHub no la ofrece sin el servicio de pago; se dice tal cual y no es un fallo que se pueda corregir
priv = repo_local("privado", "--private")
rc, s = correr(SECRETOS, priv, "github")
chequear("privado: avisa que necesita «GitHub Secret Protection» (de pago) y no falla", rc == 0 and "Secret Protection" in s and "de pago" in s and "AVISO" in s, (rc, s))
rc, s = correr(SECRETOS, priv, "github", "--activar")
chequear("privado: --activar no activa nada y lo explica", rc == 1 and "no se activó nada" in s and "de pago" in s, (rc, s))

# 4. sin `gh` utilizable
rc, s = correr(SECRETOS, pub, "github", env={**ENV, "SENIOR_GH": json.dumps([sys.executable, "-c", "import sys; sys.exit(1)"])})
chequear("si `gh` no responde dice que no pudo consultar GitHub", rc == 1 and "No se pudo consultar GitHub" in s, (rc, s))

# 5. /inicializar-repositorio activa la protección en un repositorio público nuevo y avisa en uno privado
FLAGS = ["--descripcion", "Herramienta de ejemplo para probar la inicialización.", "--topics", "ejemplo,pruebas", "--readme", "simple", "--aplicar", "--sin-subir", "--anidado"]
for nombre, vis in (("nuevo-publico", "--publico"), ("nuevo-privado", "--privado")):
    c = BASE / nombre
    c.mkdir()
    (c / "app.py").write_text("print('hola')\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(INICIALIZAR), f"dante-prueba/{nombre}", vis, *FLAGS, "--raiz", str(c)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=c, env=ENV)
    salida = r.stdout + r.stderr
    if vis == "--publico":
        chequear("inicializar un repositorio público activa la protección de subida", "LISTO protección de subida y escaneo de secretos de GitHub activos" in salida, salida[-700:])
    else:
        chequear("inicializar uno privado avisa que no se pudo activar (de pago) y sigue", "AVISO la protección de subida de GitHub no se activó" in salida and "LISTO descripción y topics" in salida, salida[-700:])

# 6. el hook de Claude no deja saltear los hooks de git
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
espec = importlib.util.spec_from_file_location("hook_secretos_claude", HOOK)
hs = importlib.util.module_from_spec(espec)
espec.loader.exec_module(hs)
raiz = BASE / "proyecto-hook"
raiz.mkdir()
subprocess.run(["git", "init", "-q"], cwd=raiz)


def bloquea(comando):
    return hs.evaluar("Bash", {"command": comando}, str(raiz), raiz) is not None


for comando in ("git commit --no-verify -m x", "git commit -nm \"x\"", "git commit -m x -n", "git push --no-verify origin main",
                "git -c core.hooksPath=/dev/null commit -m x", "git merge --no-verify rama", "cd x && git commit -an -m y"):
    chequear(f"se bloquea: {comando}", bloquea(comando), comando)
for comando in ("git commit -m x", "git commit -m \"doc: no usar --no-verify nunca\"", "git push -n origin main", "git push origin main",
                "git log --oneline -n 5", "git commit --amend -m x", "echo --no-verify"):
    chequear(f"pasa: {comando}", not bloquea(comando), comando)
r = hs.evaluar("Bash", {"command": "git commit --no-verify -m x"}, str(raiz), raiz)
chequear("el mensaje da la alternativa y no manda a esperar al usuario", r and "no se saltean" in r[1] and "pendientes.md" in r[1] and "senior-ignore" in r[1], r)

sys.exit(1 if mal else 0)
