"""Segunda capa del guardián de escrituras: un script guardado en un archivo se analiza antes de guardarlo (Write/Edit) y antes de ejecutarlo
(`python x.py`, `node x.js`, `bash x.sh`, `powershell -File x.ps1`), con las mismas reglas que el código que viaja en el comando."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
HOOK = RAIZ / "skills" / "senior" / "scripts" / "hook_fuera_del_proyecto.py"
BASE = RAIZ / ".temporal" / "proy-guardian-scripts"
mal = 0
AFUERA = "C:/Users/otro/Desktop/salida.txt"


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
BASE.mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=BASE)
ENV = {**os.environ, "SENIOR_HOOK_DEPURAR": "1", "CLAUDE_PROJECT_DIR": str(BASE)}
ENV.pop("SENIOR_LECTURA_DIRECTA", None)


def hook(herramienta, **entrada):
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": herramienta, "tool_input": entrada, "cwd": str(BASE)}),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    s = r.stdout + r.stderr
    if r.returncode == 2 or '"deny"' in s or "permissionDecision" in s and "deny" in s:
        return "deniega", s
    return "pasa", s


def script(nombre, texto):
    (BASE / nombre).write_text(texto, encoding="utf-8")
    return nombre


# 1. ejecutar un script guardado que escribe a una ruta literal fuera del proyecto
script("malo.py", f"with open('{AFUERA}', 'w') as f:\n    f.write('x')\n")
script("malo.js", f"require('fs').writeFileSync('{AFUERA}', 'x')\n")
script("malo.sh", f"echo hola > {AFUERA}\n")
script("malo.ps1", f"Set-Content -Path {AFUERA} -Value hola\n")
script("bueno.py", "with open('salida.txt', 'w') as f:\n    f.write('x')\nwith open('" + AFUERA + "') as g:\n    g.read()\n")
for comando, esperado in (("python malo.py", "deniega"), ("python3 -X utf8 malo.py", "deniega"), ("node malo.js", "deniega"), ("bash malo.sh", "deniega"),
                          ("powershell -File malo.ps1", "deniega"), ("cd . && python malo.py", "deniega"),
                          ("python bueno.py", "pasa"), ("python inexistente.py", "pasa"), ("python -m unittest", "pasa")):
    r, s = hook("Bash", command=comando)
    chequear(f"{comando} → {esperado}", r == esperado, s[:200])

# 2. guardar un script con esa escritura (Write y Edit); un archivo que no es de código no se analiza
r, s = hook("Write", file_path=str(BASE / "nuevo.py"), content=f"open('{AFUERA}', 'w').write('x')\n")
chequear("Write de un script que escribe fuera del proyecto se deniega", r == "deniega", s[:200])
r, s = hook("Edit", file_path=str(BASE / "bueno.py"), old_string="x", new_string=f"open('{AFUERA}', 'a').write('y')")
chequear("Edit que agrega esa escritura a un script se deniega", r == "deniega", s[:200])
r, s = hook("Write", file_path=str(BASE / "notas.md"), content=f"En un ejemplo: open('{AFUERA}', 'w')\n")
chequear("un Markdown que menciona la ruta no se analiza", r == "pasa", s[:200])
r, s = hook("Write", file_path=str(BASE / "ok.py"), content="open('salida.txt', 'w').write('x')\n")
chequear("Write de un script que escribe dentro del proyecto pasa", r == "pasa", s[:200])
r, s = hook("Write", file_path=str(BASE / "leer.py"), content=f"print(open('{AFUERA}').read())\n")
chequear("leer una ruta externa desde un script es legítimo y pasa", r == "pasa", s[:200])

# 3. la marca con motivo declara que el archivo solo muestra rutas de ejemplo
script("ejemplo.py", f"# senior-ignore: ESCRIBE-AFUERA motivo: muestra rutas de ejemplo\nopen('{AFUERA}', 'w')\n")
r, s = hook("Bash", command="python ejemplo.py")
chequear("un script con la marca y su motivo no se analiza", r == "pasa", s[:200])
r, s = hook("Edit", file_path=str(BASE / "ejemplo.py"), old_string="x", new_string=f"open('{AFUERA}', 'w')")
chequear("editar un archivo que ya tiene la marca tampoco", r == "pasa", s[:200])
script("sin_motivo.py", f"# senior-ignore: ESCRIBE-AFUERA\nopen('{AFUERA}', 'w')\n")
r, s = hook("Bash", command="python sin_motivo.py")
chequear("la marca sin motivo no vale", r == "deniega", s[:200])

# 4. el mensaje da la alternativa y no manda a esperar
r, s = hook("Bash", command="python malo.py")
chequear("el mensaje manda a rehacerlo dentro del proyecto y no pregunta", ".temporal" in s and "dentro del proyecto" in s, s[:300])

# 5. nada de lo que ya tiene este repositorio queda marcado por error
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
import hook_fuera_del_proyecto as hf  # noqa: E402
marcados = [str(p.relative_to(RAIZ)) for p in list(RAIZ.glob("skills/**/*.py")) + list(RAIZ.glob("tests/*.py")) + [RAIZ / "instalar.py"]
            if hf.literales_de_script(p.read_text(encoding="utf-8", errors="replace"), p.suffix)]
chequear("ningún script de este paquete queda marcado por error", not marcados, marcados)

sys.exit(1 if mal else 0)
