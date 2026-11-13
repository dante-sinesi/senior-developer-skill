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
HOOK = RAIZ / "skills" / "senior-relevar" / "scripts" / "hook_lectura_externa.py"
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
chequear("sin instalar: no cede y avisa cómo instalarla", not td.cede_lectura(vacio) and "no está instalada" in td.aviso(vacio) and "instalar.py install" in td.aviso(vacio), td.aviso(vacio))
ok = inicio("ok", "1.0.0")
chequear("instalada 1.0.0 con su hook: cede y no avisa", td.cede_lectura(ok) and td.aviso(ok) == "", td.estado(ok))
viejo = inicio("viejo", "0.9.2")
chequear("versión vieja: no cede y pide actualizar", not td.cede_lectura(viejo) and "anterior" in td.aviso(viejo), td.aviso(viejo))
sin_hook = inicio("sinhook", "1.0.0", hook=False)
chequear("instalada sin hook registrado: no cede y lo dice", not td.cede_lectura(sin_hook) and "hook de lectura" in td.aviso(sin_hook), td.aviso(sin_hook))
roto = inicio("roto", "1.0.0", hook=False)
(roto / ".claude" / "settings.json").write_text("{no es json", encoding="utf-8")
chequear("settings ilegible: no rompe, no cede", not td.cede_lectura(roto))
nueva = inicio("mayor", "1.10.0")
chequear("1.10.0 cuenta como mayor que 1.0.0 (no se compara como texto)", td.cede_lectura(nueva))

# 2. el hook de senior: cede con Token Diet activa y bloquea sin ella
P = BASE / "proyecto"
(P / "documentos-externos").mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=P)
pdf = P / "documentos-externos" / "manual.pdf"
pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 200)
entrada = json.dumps({"tool_name": "Read", "tool_input": {"file_path": str(pdf)}, "cwd": str(P)})
r = correr(HOOK, home=vacio, entrada=entrada)
chequear("sin Token Diet: el hook de senior bloquea la lectura directa", "deny" in r.stdout or r.returncode == 2, (r.stdout, r.stderr))
r = correr(HOOK, home=ok, entrada=entrada)
chequear("con Token Diet activa: el hook de senior no dice nada (bloquea una sola)", r.returncode == 0 and not r.stdout.strip(), (r.stdout, r.stderr))
r = correr(HOOK, home=viejo, entrada=entrada)
chequear("con Token Diet vieja: senior sigue bloqueando", "deny" in r.stdout or r.returncode == 2, (r.stdout, r.stderr))

# 3. la auditoría de senior cede la referencia
r = correr(CONSUMO, "--raiz", str(P), "--home", str(ok))
chequear("auditoría: con Token Diet instalada indica que la suya es la de referencia", "su auditoría es la de referencia" in r.stdout, r.stdout[-400:])
r = correr(CONSUMO, "--raiz", str(P), "--home", str(vacio))
chequear("auditoría: sin Token Diet no agrega la nota", "referencia" not in r.stdout, r.stdout[-400:])

# 4. el instalador avisa (no falla: la dependencia obligatoria llega al final del traspaso)
r = correr(RAIZ / "instalar.py", "--verificar", home=vacio)
chequear("instalador: sin Token Diet muestra el aviso con el comando", "Token Diet no está instalada" in r.stdout, r.stdout[-600:])
r = correr(RAIZ / "instalar.py", "--verificar", home=ok)
chequear("instalador: con Token Diet lo da por listo", "Token Diet 1.0.0 instalada" in r.stdout, r.stdout[-600:])
chequear("la guardia del estado imprime y sale con 1 si falta", correr(TD, home=vacio).returncode == 1 and correr(TD, home=ok).returncode == 0)

sys.exit(1 if mal else 0)
