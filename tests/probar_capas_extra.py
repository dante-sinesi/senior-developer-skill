"""La segunda capa de «nada fuera del proyecto»: capas_extra.py informa qué tiene activo Claude Code y qué conviene, sin tocar ningún ajuste."""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SCRIPT = RAIZ / "skills" / "senior" / "scripts" / "capas_extra.py"
sys.path.insert(0, str(SCRIPT.parent))
import capas_extra as ce  # noqa: E402

mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def texto(*args):
    return "\n".join(ce.evaluar(*args))


# 1. Windows nativo sin nada activado
t = texto([{}, {}, {}], "windows", None)
chequear("Windows nativo: dice que el sandbox no existe y que hay que usar WSL2", "no existe en Windows nativo" in t and "WSL2" in t, t)
chequear("ofrece activar blockWritesOutsideWorkingDirectories con el fragmento exacto y su costo", '"blockWritesOutsideWorkingDirectories": true' in t and "/permitir" in t and "/add-dir" in t, t)
chequear("sin poder leer la versión, avisa el mínimo (2.1.314)", "2.1.314" in t, t)
chequear("aclara que las reglas deny de Bash no son una frontera", "deny" in t and "no son una frontera" in t, t)
chequear("deja claro que solo informa", "los cambia el usuario, no Claude" in t, t)
chequear("no ofrece el fragmento del sandbox donde no existe", '"sandbox"' not in t.split("sandbox`: no existe")[0].split("blockWrites")[-1] and '"failIfUnavailable"' not in t, t)

# 2. versiones
t = texto([{}, {}, {}], "windows", (2, 1, 300))
chequear("una versión vieja de Claude Code dice que hay que actualizar primero", "2.1.300" in t and "actualizarlo primero" in t, t)
t = texto([{}, {}, {}], "windows", (2, 1, 320))
chequear("una versión suficiente no pide actualizar", "actualizarlo primero" not in t and "no se pudo leer" not in t, t)

# 3. macOS y Linux con el sandbox sin activar
for so in ("macos", "linux", "wsl2"):
    t = texto([{}, {}, {}], so, (2, 1, 320))
    chequear(f"{so}: ofrece activar el sandbox con el fragmento exacto", '"enabled": true' in t and '"failIfUnavailable": true' in t and '"allowUnsandboxedCommands": false' in t, t)

# 4. todo activado
t = texto([{"permissions": {"blockWritesOutsideWorkingDirectories": True}, "sandbox": {"enabled": True}}], "macos", (2, 1, 320))
chequear("con las dos capas activas lo dice y no ofrece fragmentos", "blockWritesOutsideWorkingDirectories`: ACTIVO" in t and "`sandbox`: ACTIVO" in t and '"enabled": true' not in t, t)
t = texto([{"sandbox": {"enabled": True}}], "windows", (2, 1, 320))
chequear("un sandbox «activado» en Windows nativo se denuncia como inexistente", "figura activado, pero en Windows nativo no existe" in t and "SIN restricción" in t, t)

# 5. precedencia: el archivo más específico manda
chequear("el ajuste del proyecto manda sobre el del usuario", ce.valor([{"sandbox": {"enabled": False}}, {"sandbox": {"enabled": True}}], ("sandbox", "enabled")) is False)
chequear("si el más específico no lo define, vale el siguiente", ce.valor([{}, {"sandbox": {"enabled": True}}], ("sandbox", "enabled")) is True)
chequear("un ajuste ausente es None", ce.valor([{}, {}], ("sandbox", "enabled")) is None)
chequear("un JSON roto o inexistente se toma como vacío", ce.leer_json(RAIZ / "no-existe.json") == {})

# 6. de punta a punta: lee los ajustes del usuario y no los toca
BASE = RAIZ / ".temporal" / "proy-capas"
shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
(BASE / "casa" / ".claude").mkdir(parents=True)
(BASE / "proyecto").mkdir()
ajustes = BASE / "casa" / ".claude" / "settings.json"
ajustes.write_text(json.dumps({"permissions": {"blockWritesOutsideWorkingDirectories": True}}), encoding="utf-8")
antes = hashlib.sha256(ajustes.read_bytes()).hexdigest()
r = subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(BASE / "proyecto")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env={**os.environ, "USERPROFILE": str(BASE / "casa"), "HOME": str(BASE / "casa")})
chequear("el script lee el ajuste del usuario y sale con 0", r.returncode == 0 and "blockWritesOutsideWorkingDirectories`: ACTIVO" in r.stdout, r.stdout + r.stderr)
chequear("no modifica ningún ajuste ni crea archivos de ajustes", hashlib.sha256(ajustes.read_bytes()).hexdigest() == antes and not (BASE / "proyecto" / ".claude").exists())
chequear("el código no escribe archivos (solo lee)", "write_text" not in SCRIPT.read_text(encoding="utf-8") and "open(" not in SCRIPT.read_text(encoding="utf-8"))

# 7. documentación
doc = (RAIZ / "docs" / "revision-completa.md").read_text(encoding="utf-8")
rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el documento vivo ya no afirma que las reglas deny cubran cualquier comando", "que sí cubren cualquier comando" not in doc)
chequear("el README explica la segunda capa y capas_extra.py", "capas_extra.py" in rd and "sandbox" in rd and "WSL2" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
