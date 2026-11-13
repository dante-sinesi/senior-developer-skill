"""Token Diet como dependencia: se detecta (instalada, versión, hook registrado), el hook de lectura de senior cede cuando el de Token Diet está activo,
sigue bloqueando cuando no, y el instalador y la auditoría lo mencionan."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
TD = RAIZ / "skills" / "senior" / "scripts" / "token_diet.py"
BASE = RAIZ / ".temporal" / "proy-token-diet"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None


def inicio(nombre, version=None, hook=True):
    """Una carpeta de inicio falsa con (o sin) Token Diet instalada."""
    h = BASE / nombre
    (h / ".claude" / "skills" / "token-diet").mkdir(parents=True)
    if version:
        (h / ".claude" / "skills" / "token-diet" / ".install.json").write_text(json.dumps({"version": version, "files": {}, "hooks": []}), encoding="utf-8")
    if hook:
        cmd = f'python "{(h / ".claude" / "skills" / "token-diet" / "scripts").as_posix()}/hook_lectura_externa.py"'
        (h / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Read|Grep", "hooks": [{"type": "command", "command": cmd}]}]}}), encoding="utf-8")
    return h


def correr(script, *args, home=None, entrada=None):
    env = dict(os.environ, SENIOR_TOKEN_DIET_HOME=str(home)) if home else dict(os.environ)
    env.pop("SENIOR_LECTURA_DIRECTA", None)
    return subprocess.run([sys.executable, str(script), *args], input=entrada, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


# 1. detección
import importlib.util
espec = importlib.util.spec_from_file_location("token_diet", TD)
td = importlib.util.module_from_spec(espec)
espec.loader.exec_module(td)
vacio = inicio("vacio")
chequear("sin instalar: no cede y avisa cómo instalarla", "no está instalada" in td.aviso(vacio) and "instalar.py install" in td.aviso(vacio), td.aviso(vacio))
ok = inicio("ok", "1.0.0")
chequear("instalada 1.0.0 con su hook: cede y no avisa", td.estado(ok)["hook_lectura"] and td.aviso(ok) == "", td.estado(ok))
viejo = inicio("viejo", "0.9.2")
chequear("versión vieja: no cede y pide actualizar", "anterior" in td.aviso(viejo), td.aviso(viejo))
sin_hook = inicio("sinhook", "1.0.0", hook=False)
chequear("instalada sin hook registrado: no cede y lo dice", "hook de lectura" in td.aviso(sin_hook), td.aviso(sin_hook))
roto = inicio("roto", "1.0.0", hook=False)
(roto / ".claude" / "settings.json").write_text("{no es json", encoding="utf-8")
chequear("settings ilegible: no rompe y no cuenta el hook", not td.estado(roto)["hook_lectura"])
nueva = inicio("mayor", "1.10.0")
chequear("1.10.0 cuenta como mayor que 1.0.0 (no se compara como texto)", td.estado(nueva)["al_dia"])

# 2. el hook de lectura ya no es de senior: no queda ningún script de lectura de documentos en el paquete
import subprocess as _sp
for retirado in ("senior-relevar/scripts/hook_lectura_externa.py", "senior-relevar/scripts/convertir_fuentes.py", "senior-diseno/scripts/capturar.py"):
    chequear(f"{retirado} ya no está en el paquete (lo hace Token Diet)", not (RAIZ / "skills" / retirado).exists())

P = BASE / "proyecto"
P.mkdir(parents=True, exist_ok=True)

# 3. la auditoría de consumo tampoco es de senior
chequear("consumo.py y la skill auditar-consumo ya no están en el paquete (los trae Token Diet)", not (RAIZ / "skills" / "auditar-consumo").exists())

# 4. el instalador avisa (no falla: la dependencia obligatoria llega al final del traspaso)
r = correr(RAIZ / "instalar.py", "--verificar", home=vacio)
chequear("instalador: sin Token Diet muestra el aviso con el comando", "Token Diet no está instalada" in r.stdout, r.stdout[-600:])
r = correr(RAIZ / "instalar.py", "--verificar", home=ok)
chequear("instalador: con Token Diet lo da por listo", "Token Diet 1.0.0 instalada" in r.stdout, r.stdout[-600:])
chequear("la guardia del estado imprime y sale con 1 si falta", correr(TD, home=vacio).returncode == 1 and correr(TD, home=ok).returncode == 0)

# 5. las capturas del diseño las saca Token Diet: sin ella, el mensaje dice cómo instalarla
(P / "p.html").write_text("<!doctype html><title>x</title><p>hola</p>", encoding="utf-8")
DISENO = RAIZ / "skills" / "senior-diseno" / "scripts" / "revisar_diseno.py"
r = correr(DISENO, "base", str(P / "p.html"), "--capturas", home=vacio)
chequear("--capturas sin Token Diet dice que no está instalada y cómo instalarla", "Token Diet no está instalada" in r.stdout and "instalar.py install" in r.stdout, r.stdout[-400:])
VERIF = RAIZ / "skills" / "senior" / "scripts" / "verificar.py"
chequear("verificar.py ya no ofrece el chequeo de fuentes (es de Token Diet)", "chequeo_fuentes" not in VERIF.read_text(encoding="utf-8"))

# 6. al migrar los hooks sueltos, el hook de lectura de Token Diet (mismo nombre de archivo) no se toca
import json as _json
spec = importlib.util.spec_from_file_location("guardia", RAIZ / "skills" / "senior-git" / "scripts" / "guardia_autoria.py")
guardia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardia)
td_cmd = 'python "C:/Users/x/.claude/skills/token-diet/scripts/hook_lectura_externa.py"'
sr_cmd = 'python "C:/Users/x/.claude/skills/senior-relevar/scripts/hook_lectura_externa.py"'
ajustes = {"hooks": {"PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": td_cmd}, {"type": "command", "command": sr_cmd}]}]}}
sacados = guardia.sacar_sueltos(ajustes)
quedan = [h["command"] for g in ajustes["hooks"]["PreToolUse"] for h in g["hooks"]]
chequear("migrar sueltos saca el hook viejo de senior y deja el de Token Diet", sacados == 1 and quedan == [td_cmd], (sacados, quedan))
chequear("con backslashes de Windows también se reconoce el de Token Diet", not guardia.es_suelto(td_cmd.replace("/", chr(92))))

sys.exit(1 if mal else 0)
