"""/inicializar-repositorio: del enlace o el nombre de un repositorio a una carpeta publicada, con README, descripción y topics obligatorios, sin
claves a la vista y sin forzar nada. Se prueba con un `gh` simulado y remotos que son carpetas locales (sin red)."""
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
SCRIPT = RAIZ / "skills" / "inicializar-repositorio" / "scripts" / "inicializar_repo.py"
BASE = RAIZ / ".temporal" / "proy-inicializar"
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
ENV.pop("GH_FALSO_PERMISO", None)


def estado():
    return json.loads((BASE / "gh" / "estado.json").read_text(encoding="utf-8")) if (BASE / "gh" / "estado.json").exists() else {"repos": {}}


def carpeta(nombre, archivos):
    c = BASE / nombre
    c.mkdir()
    for rel, contenido in archivos.items():
        (c / rel).parent.mkdir(parents=True, exist_ok=True)
        (c / rel).write_text(contenido, encoding="utf-8")
    return c


def correr(c, *args, env=None, anidado=True):
    # las carpetas de prueba viven dentro del repositorio de senior (en .temporal/): por eso se pide --anidado, salvo en la prueba que lo comprueba
    r = subprocess.run([sys.executable, str(SCRIPT), *args, "--raiz", str(c), *(["--anidado"] if anidado else [])], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=c, env=env or ENV)
    return r.returncode, r.stdout + r.stderr


def git(c, *args):
    r = subprocess.run(["git", *args], cwd=c, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def listado(c):
    return sorted(p.relative_to(c).as_posix() for p in c.rglob("*") if p.is_file())


FLAGS = ["--descripcion", "Herramienta de ejemplo para probar la inicialización.", "--topics", "ejemplo,pruebas", "--readme", "simple"]
CLAVE = "AKIA" + "QWERTYUIOPASDFGH"

# ---------------- 1. interpretar el repositorio (enlace, dueño/nombre, nombre)
espec = importlib.util.spec_from_file_location("ir", SCRIPT)
ir = importlib.util.module_from_spec(espec)
espec.loader.exec_module(ir)
for texto, esperado in (("https://github.com/dante-sinesi/token-diet-skill", ("dante-sinesi", "token-diet-skill")),
                        ("https://github.com/dante-sinesi/token-diet-skill.git", ("dante-sinesi", "token-diet-skill")),
                        ("https://github.com/dante-sinesi/token-diet-skill/", ("dante-sinesi", "token-diet-skill")),
                        ("git@github.com:dante-sinesi/token-diet-skill.git", ("dante-sinesi", "token-diet-skill")),
                        ("dante-sinesi/token-diet-skill", ("dante-sinesi", "token-diet-skill")),
                        ("token-diet-skill", ("yo", "token-diet-skill")), ("  mi.repo_1  ", ("yo", "mi.repo_1")), ("no es un repo", None), ("a/b/c", None)):
    chequear(f"se entiende «{texto.strip()}»", ir.interpretar_repo(texto, "yo") == esperado, ir.interpretar_repo(texto, "yo"))

# ---------------- 1b. una carpeta dentro de otro repositorio no se toma por uno propio
h = carpeta("h", {"q.py": "q = 1\n"})
rc, s = correr(h, "anidada", "--privado", *FLAGS, "--aplicar", anidado=False)
chequear("dentro de otro repositorio bloquea y nunca commitea en el de afuera", rc == 1 and "dentro del repositorio de Git" in s and "--anidado" in s and not (h / ".git").exists()
         and not (h / "README.md").exists(), s)
rc, s = correr(h, "anidada", "--privado", *FLAGS)
chequear("con --anidado el plan sigue y lo avisa", rc == 0 and "con --anidado se crea uno propio" in s, s)

# ---------------- 2. el plan no escribe nada y dice qué falta
a = carpeta("a", {"app.py": "print('hola')\n", "util.py": "x = 1\n", "notas.txt": "apuntes\n", ".env": "TOKEN=valor-de-prueba-123\n"})  # senior-ignore: SEC-LOG-SENSIBLE motivo: valor falso de prueba
antes = listado(a)
rc, s = correr(a, "demo")
chequear("sin visibilidad, descripción ni topics bloquea y lo dice", rc == 1 and "BLOQUEA" in s and "--publico" in s and "descripción y los topics son obligatorios" in s, s)
chequear("y bloquea porque falta elegir el tipo de README (simple o con tarjetas), con la orientación por visibilidad",
         "elegir el tipo de README" in s and "--readme simple" in s and "--readme tarjetas" in s and "privados suelen" in s, s)
chequear("propone los topics que se deducen solos", "python" in s, s)
chequear("el plan no escribió nada (ni .git ni README)", listado(a) == antes and not (a / ".git").exists(), listado(a))
rc, s = correr(a, "demo", "--privado", *FLAGS)
chequear("con todo indicado, el plan queda listo y sigue sin escribir", rc == 0 and "Resultado: listo" in s and "crear dante-prueba/demo" in s and listado(a) == antes, s)
chequear("el plan no cuenta como secreto lo que el .gitignore va a dejar afuera (.env)", "SECRETO" not in s, s)

# ---------------- 3. aplicar sobre un repositorio nuevo
rc, s = correr(a, "demo", "--privado", *FLAGS, "--aplicar")
chequear("aplicar termina bien", rc == 0 and "Resultado: todo listo." in s, s)
chequear("quedó en main con dos commits en español y Conventional Commits", git(a, "branch", "--show-current") == "main"
         and git(a, "log", "--format=%s").splitlines() == ["chore: agrega el contenido existente", "chore: inicializa el repositorio"], git(a, "log", "--format=%s"))
chequear("la identidad es local y de la sesión de GitHub", git(a, "config", "--local", "user.name") == "dante-prueba" and git(a, "config", "--local", "user.email") == "4242+dante-prueba@users.noreply.github.com")
chequear("autor y committer son solo el usuario, y ningún mensaje tiene rastro de Claude ni coautores",
         set(git(a, "log", "--format=%an|%cn").splitlines()) == {"dante-prueba|dante-prueba"} and not any(x in git(a, "log", "--format=%B").lower() for x in ("co-author", "claude", "anthropic")))
chequear("creó el README con la descripción y lo que contiene la carpeta", (a / "README.md").exists() and "Herramienta de ejemplo" in (a / "README.md").read_text(encoding="utf-8")
         and "`app.py`" in (a / "README.md").read_text(encoding="utf-8"))
ignore = (a / ".gitignore").read_text(encoding="utf-8")
chequear("el .gitignore tiene lo común y los archivos de secretos", "__pycache__/" in ignore and ".env" in ignore and "*.pem" in ignore, ignore)
chequear("el .env NO se subió", ".env" not in git(a, "ls-files").splitlines() and "app.py" in git(a, "ls-files").splitlines())
chequear("instaló los hooks de Git", all((a / ".git" / "hooks" / h).exists() for h in ("pre-commit", "commit-msg", "pre-push")))
repo = estado()["repos"].get("dante-prueba/demo", {})
chequear("el repositorio se creó privado, con la descripción y los topics (los dados y los deducidos)", repo.get("privado") is True and repo.get("descripcion", "").startswith("Herramienta de ejemplo")
         and {"ejemplo", "pruebas", "python"} <= set(repo.get("topics", [])), repo)
chequear("se subió: el remoto tiene el mismo último commit", git(repo.get("bare", "."), "rev-parse", "main") == git(a, "rev-parse", "HEAD"), repo)
chequear("el árbol quedó limpio y verificado", git(a, "status", "--porcelain") == "" and "árbol limpio" in s, s)

# ---------------- 4. repetirlo no duplica nada
n = git(a, "rev-list", "--count", "HEAD")
rc, s = correr(a, "demo", "--privado", *FLAGS, "--aplicar")
chequear("repetir no agrega commits ni rompe nada", rc == 0 and git(a, "rev-list", "--count", "HEAD") == n and git(repo["bare"], "rev-parse", "main") == git(a, "rev-parse", "HEAD"), s)

# ---------------- 5. claves a la vista: no se hace nada
b = carpeta("b", {"config.py": f"K = '{CLAVE}'\n", "app.py": "x = 1\n"})
rc, s = correr(b, "con-clave", "--privado", *FLAGS)
chequear("con una clave a la vista el plan bloquea y la muestra sin el valor completo", rc == 1 and "SECRETO SEC-SECRETO-AWS config.py" in s and CLAVE not in s, s)
rc, s = correr(b, "con-clave", "--privado", *FLAGS, "--aplicar")
chequear("y aplicar no hace nada: ni .git, ni repositorio, ni README", rc == 1 and "no se hizo nada" in s and not (b / ".git").exists() and not (b / "README.md").exists()
         and "dante-prueba/con-clave" not in estado()["repos"], s)

# ---------------- 6. repositorio que ya existe y está vacío (por enlace)
subprocess.run([sys.executable, str(RAIZ / "tests" / "gh_falso.py"), "repo", "create", "dante-prueba/ya-existe", "--public"], env=ENV, check=True, capture_output=True)
c = carpeta("c", {"datos.md": "# Datos\n"})
rc, s = correr(c, "https://github.com/dante-prueba/ya-existe", *FLAGS, "--aplicar")
bare = estado()["repos"]["dante-prueba/ya-existe"]["bare"]
chequear("con un enlace a un repositorio vacío existente, no lo crea y sube", rc == 0 and "repositorio existente" in s and git(bare, "rev-parse", "main") == git(c, "rev-parse", "HEAD"), s)
chequear("y deja su visibilidad como estaba (no pregunta ni cambia)", estado()["repos"]["dante-prueba/ya-existe"]["privado"] is False)

# ---------------- 7. remoto con contenido y carpeta que no es repositorio: no se mezclan
subprocess.run([sys.executable, str(RAIZ / "tests" / "gh_falso.py"), "repo", "create", "dante-prueba/con-historia", "--private"], env=ENV, check=True, capture_output=True)
otro = carpeta("otro", {"x.txt": "x\n"})
bare2 = estado()["repos"]["dante-prueba/con-historia"]["bare"]
for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"], ["config", "user.email", "t@x.test"], ["add", "-A"], ["commit", "-q", "-m", "x", "--no-verify"],
            ["push", "-q", bare2, "main"]):
    git(otro, *cmd)
d = carpeta("d", {"y.txt": "y\n"})
rc, s = correr(d, "con-historia", *FLAGS, "--aplicar")
chequear("un remoto con contenido y una carpeta sin Git: bloquea y no toca nada", rc == 1 and "no se mezclan" in s and not (d / ".git").exists(), s)

# ---------------- 8. un origin distinto no se cambia
e = carpeta("e", {"z.txt": "z\n"})
git(e, "init", "-q", "-b", "main")
git(e, "remote", "add", "origin", "https://github.com/alguien/otro-repo.git")
rc, s = correr(e, "demo2", "--privado", *FLAGS)
chequear("un origin distinto bloquea", rc == 1 and "`origin` distinto" in s, s)

# ---------------- 9. sin subir, permiso, descripción inválida
f = carpeta("f", {"w.py": "w = 1\n"})
rc, s = correr(f, "solo-local", "--privado", *FLAGS, "--aplicar", "--sin-subir")
chequear("--sin-subir hace todo menos el push", rc == 0 and git(f, "rev-list", "--count", "HEAD") == "2" and git(estado()["repos"]["dante-prueba/solo-local"]["bare"], "rev-list", "-n", "1", "--all") == "", s)
g = carpeta("g", {"v.py": "v = 1\n"})
rc, s = correr(g, "sin-permiso", "--privado", *FLAGS, env={**ENV, "GH_FALSO_PERMISO": "READ"}) if False else (0, "")
subprocess.run([sys.executable, str(RAIZ / "tests" / "gh_falso.py"), "repo", "create", "dante-prueba/solo-lectura", "--private"], env=ENV, check=True, capture_output=True)
rc, s = correr(g, "solo-lectura", *FLAGS, env={**ENV, "GH_FALSO_PERMISO": "READ"})
chequear("sin permiso para escribir bloquea", rc == 1 and "permiso «READ»" in s, s)
rc, s = correr(g, "malo", "--privado", "--descripcion", "Escribime a alguien@correo.test", "--topics", "ejemplo")
chequear("una descripción con un correo no es válida", rc == 1 and "no válidos" in s, s)
rc, s = correr(g, "malo", "--privado", "--publico", *FLAGS)
chequear("público y privado a la vez no se acepta", rc != 0, s)
rc, s = correr(g, "malo", "--privado", *FLAGS, env={k: v for k, v in ENV.items() if k != "SENIOR_GH"} | {"SENIOR_GH": json.dumps([sys.executable, "-c", "import sys; sys.exit(1)"])})
chequear("sin sesión de GitHub bloquea y lo explica", rc == 1 and "no hay sesión de GitHub" in s, s)

# ---------------- 9b. README con tarjetas SVG: se pregunta, el estilo lo elige el usuario y se genera
TEMA = {"nombre": "Horno", "composicion": "dividida", "colores": {"fondo": "#2B1810", "titulo": "#FFE9C7", "texto": "#F2C9A0", "acento": "#FF8A3D"},
        "tipografia": {"familia": "Georgia, serif"}, "sombra_titulo": "#7A3A12",
        "decoracion": {"fondo_svg": '<circle cx="650" cy="150" r="120" fill="#3D2216"/>'}}
TEMA_MALO = {**TEMA, "colores": {**TEMA["colores"], "titulo": "#3A2418"}}
(BASE / "estilo.json").write_text(json.dumps(TEMA, ensure_ascii=False), encoding="utf-8")
(BASE / "estilo-malo.json").write_text(json.dumps(TEMA_MALO, ensure_ascii=False), encoding="utf-8")
DESC = "Sistema de pedidos para una panadería artesanal."
k = carpeta("k", {"main.py": "x = 1\n", "util.py": "y = 2\n"})
BASEK = ["panaderia-lumbre", "--publico", "--descripcion", DESC, "--topics", "panaderia,pedidos"]
rc, s = correr(k, *BASEK)
chequear("sin elegir el tipo de README el plan bloquea", rc == 1 and "elegir el tipo de README" in s, s)
rc, s = correr(k, *BASEK, "--readme", "tarjetas")
chequear("con tarjetas y sin estilo bloquea: el diseñador propone tres y el usuario elige", rc == 1 and "necesita el estilo elegido" in s and "tres" in s, s)
rc, s = correr(k, *BASEK, "--readme", "tarjetas", "--estilo", str(BASE / "estilo-malo.json"))
chequear("un estilo con poco contraste bloquea antes de escribir nada", rc == 1 and "no son válidos" in s and "contraste" in s, s)
rc, s = correr(k, *BASEK, "--readme", "tarjetas", "--estilo", str(BASE / "no-existe.json"))
chequear("un estilo que no existe bloquea", rc == 1 and "no existe el estilo" in s, s)
antes = listado(k)
rc, s = correr(k, *BASEK, "--readme", "tarjetas", "--estilo", str(BASE / "estilo.json"))
chequear("con el estilo elegido el plan queda listo y no escribe nada", rc == 0 and "con tarjetas SVG" in s and listado(k) == antes, s)
rc, s = correr(k, *BASEK, "--readme", "tarjetas", "--estilo", str(BASE / "estilo.json"), "--aplicar")
readme_k = (k / "README.md").read_text(encoding="utf-8") if (k / "README.md").exists() else ""
chequear("aplicar con tarjetas termina bien", rc == 0 and "README.md con tarjetas SVG" in s, s)
chequear("el README empieza con la portada centrada y su pie de foto, y sigue con la descripción",
         readme_k.startswith('<p align="center"><img src="docs/img/portada.svg" alt="panaderia lumbre" width="760"><br><sub>Portada de panaderia lumbre:') and DESC in readme_k.split("</p>", 1)[1], readme_k[:300])
chequear("guardó el estilo elegido, la portada como datos y el SVG generado", all((k / f).exists() for f in ("docs/tarjetas/estilo.json", "docs/tarjetas/portada.json", "docs/img/portada.svg")))
chequear("todo eso quedó commiteado (los SVG no se hacen a mano: se regeneran desde los JSON)", {"README.md", "docs/tarjetas/estilo.json", "docs/tarjetas/portada.json", "docs/img/portada.svg"} <= set(git(k, "ls-files").splitlines()))
svg_k = (k / "docs" / "img" / "portada.svg").read_text(encoding="utf-8")
chequear("el SVG tiene su descripción accesible y el estilo elegido", "<desc>" in svg_k and "panaderia lumbre" in svg_k.lower() and "#2B1810" in svg_k, svg_k[:200])
r2 = subprocess.run([sys.executable, str(RAIZ / "skills" / "senior-docs" / "scripts" / "readme_tarjetas.py"), "verificar", "--raiz", str(k)], capture_output=True, text=True, encoding="utf-8", errors="replace")
chequear("readme_tarjetas.py verificar da todo al día", r2.returncode == 0 and "1 al día" in r2.stdout, r2.stdout + r2.stderr)
chequear("la descripción y los topics también quedaron en GitHub", estado()["repos"]["dante-prueba/panaderia-lumbre"]["descripcion"] == DESC)
meta = importlib.util.spec_from_file_location("rm", RAIZ / "skills" / "senior-git" / "scripts" / "repo_meta.py")
rm = importlib.util.module_from_spec(meta)
meta.loader.exec_module(rm)
chequear("un README sin título (empieza con la portada) igual aporta su presentación a repo_meta", DESC in rm.presentacion(k)[1], rm.presentacion(k))
m = carpeta("m", {"README.md": "# Ya tenía\n\nUn README propio.\n", "q.py": "q = 1\n", "r.py": "r = 2\n"})
rc, s = correr(m, "ya-tenia", "--publico", "--descripcion", DESC, "--topics", "ejemplo", "--readme", "tarjetas", "--estilo", str(BASE / "estilo.json"), "--aplicar")
chequear("si ya hay README no se toca y no se generan tarjetas", rc == 0 and "no se toca" in s and (m / "README.md").read_text(encoding="utf-8") == "# Ya tenía\n\nUn README propio.\n" and not (m / "docs" / "img").exists(), s)

# ---------------- 10. documentación y empaquetado
sk = (RAIZ / "skills" / "inicializar-repositorio" / "SKILL.md").read_text(encoding="utf-8")
chequear("el comando tiene su SKILL.md con nombre y descripción", sk.startswith("---\nname: inicializar-repositorio\ndescription:") and "/inicializar-repositorio" in sk)
chequear("la skill explica la autorización y lo que no hace", "Invocar este comando es el pedido" in sk and "Forzar un push" in sk and "obligatorios" in sk)
chequear("la skill manda a preguntar el tipo de README y a que el diseñador proponga tres estilos", "README simple" in sk and "tarjetas SVG" in sk and "tres estilos" in sk and "tarjetas-readme.md" in sk)
rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el README lo explica", "`inicializar-repositorio`" in rd and "/inicializar-repositorio" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
