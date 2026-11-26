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
CONSUMO = RAIZ / "skills" / "auditar-consumo" / "scripts" / "consumo.py"
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
ok = inicio("ok", "1.0.2")
chequear("instalada 1.0.2 con su hook: cede y no avisa", td.estado(ok)["al_dia"] and td.aviso(ok) == "", td.estado(ok))
viejo = inicio("viejo", "0.9.2")
chequear("versión vieja: no cede y pide actualizar", "anterior" in td.aviso(viejo), td.aviso(viejo))
v100 = inicio("v100", "1.0.0")
chequear("1.0.0 es anterior a la mínima (1.0.2): no cede y pide actualizar", "anterior" in td.aviso(v100), td.aviso(v100))
sin_hook = inicio("sinhook", "1.0.2", hook=False)
chequear("instalada sin hook registrado: no cede y lo dice", "hook de lectura" in td.aviso(sin_hook), td.aviso(sin_hook))
roto = inicio("roto", "1.0.2", hook=False)
(roto / ".claude" / "settings.json").write_text("{no es json", encoding="utf-8")
chequear("settings ilegible: no rompe y no cuenta el hook", not td.estado(roto)["hook_lectura"])
nueva = inicio("mayor", "1.10.0")
chequear("1.10.0 cuenta como mayor que 1.0.2 (no se compara como texto)", td.estado(nueva)["al_dia"])

# 2. senior ya no trae ni conversor ni hook de lectura: la lectura de PDF es de Token Diet
for retirado in ("senior-relevar/scripts/hook_lectura_externa.py", "senior-relevar/scripts/convertir_fuentes.py"):
    chequear(f"{retirado} ya no está en el paquete (lo hace Token Diet)", not (RAIZ / "skills" / retirado).exists())

P = BASE / "proyecto"
P.mkdir(parents=True, exist_ok=True)

# 3. la auditoría de senior cede la referencia
r = correr(CONSUMO, "--raiz", str(P), "--home", str(ok))
chequear("auditoría: con Token Diet instalada indica que la suya es la de referencia", "su auditoría es la de referencia" in r.stdout, r.stdout[-400:])
r = correr(CONSUMO, "--raiz", str(P), "--home", str(vacio))
chequear("auditoría: sin Token Diet no agrega la nota", "referencia" not in r.stdout, r.stdout[-400:])

# 4. el instalador avisa (no falla: la dependencia obligatoria llega al final del traspaso)
r = correr(RAIZ / "instalar.py", "--verificar", home=vacio)
chequear("instalador: sin Token Diet muestra el aviso con el comando", "Token Diet no está instalada" in r.stdout, r.stdout[-600:])
r = correr(RAIZ / "instalar.py", "--verificar", home=ok)
chequear("instalador: con Token Diet lo da por listo", "Token Diet 1.0.2 instalada" in r.stdout, r.stdout[-600:])
chequear("la guardia del estado imprime y sale con 1 si falta", correr(TD, home=vacio).returncode == 1 and correr(TD, home=ok).returncode == 0)

# 6. el aviso al abrir la sesión: una sola vez por proyecto, sin obligar a nada
CARGAR = RAIZ / "skills" / "senior-docs" / "scripts" / "cargar_estado.py"
Q = BASE / "proyecto-aviso"
Q.mkdir(parents=True, exist_ok=True)
subprocess.run(["git", "init", "-q"], cwd=Q)
r1 = correr(CARGAR, "--raiz", str(Q), home=vacio)
r2 = correr(CARGAR, "--raiz", str(Q), home=vacio)
chequear("sin Token Diet, al abrir la sesión avisa que es opcional y que senior sigue", "Token Diet (opcional)" in r1.stdout and "senior sigue funcionando" in r1.stdout, r1.stdout[-300:])
chequear("el aviso sale una sola vez por proyecto", "Token Diet (opcional)" not in r2.stdout, r2.stdout[-300:])
Q2 = BASE / "proyecto-con"
Q2.mkdir(parents=True, exist_ok=True)
subprocess.run(["git", "init", "-q"], cwd=Q2)
chequear("con Token Diet no dice nada", "Token Diet (opcional)" not in correr(CARGAR, "--raiz", str(Q2), home=ok).stdout)
sk = (RAIZ / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8")
chequear("la skill senior declara que Token Diet es recomendada y no obligatoria y que la lectura de PDF es suya", "recomendada y no obligatoria" in sk and "lee los PDF" in sk and "todo funciona igual" in sk)

# 7. al migrar los hooks sueltos, el hook de lectura de Token Diet (mismo nombre de archivo) no se toca
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
