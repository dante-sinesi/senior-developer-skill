#!/usr/bin/env python3
"""El instalador quita de ~/.claude/skills solo lo que él instaló y ya no está en el paquete; nunca lo de otro paquete ni lo del usuario."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
BASE = RAIZ / ".temporal" / "proy-limpieza"
CASA = BASE / "casa"
SKILLS = CASA / ".claude" / "skills"
RETIRADAS = CASA / ".claude" / "senior-retiradas"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:600]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def poner(nombre, texto="mio\n"):
    (SKILLS / nombre).mkdir(parents=True, exist_ok=True)
    (SKILLS / nombre / "SKILL.md").write_text(f"---\nname: {nombre}\n---\n{texto}", encoding="utf-8")


def instalar(*args):
    env = {**os.environ, "USERPROFILE": str(CASA), "HOME": str(CASA), "SENIOR_HOOK_DEPURAR": "1", "SENIOR_TOKEN_DIET_HOME": str(CASA)}
    env.pop("CLAUDE_PROJECT_DIR", None)
    r = subprocess.run([sys.executable, "-X", "utf8", str(RAIZ / "instalar.py"), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    return r.returncode, r.stdout + r.stderr


def instaladas():
    return sorted(d.name for d in SKILLS.iterdir() if d.is_dir())


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
for n in ("senior-memoria", "senior-refactor", "senior-vieja", "mi-skill", "senior-diseno", "auditar-diseno", "senior-lenguajes"):
    poner(n)
# registro de una instalación anterior (trae un nombre que no está en la lista cerrada) y registro de otro paquete
(SKILLS / ".senior-instalacion.json").write_text(json.dumps({"origen": "x", "skills": {"senior-vieja": "h", "senior-diseno": "h", "senior": "h"}}), encoding="utf-8")
(SKILLS / ".otro-instalacion.json").write_text(json.dumps({"skills": {"senior-lenguajes": ""}}), encoding="utf-8")

antes = instaladas()
rc, s = instalar("--verificar")
chequear("--verificar lista lo retirado y no toca nada",
         instaladas() == antes and all(n in s for n in ("senior-memoria", "senior-refactor", "senior-vieja")) and not RETIRADAS.exists(), s[-700:])
chequear("y no lo ofrece para lo del usuario, lo de otro paquete ni lo mudado", "mi-skill" not in s and "senior-lenguajes" not in s, s[-700:])

rc, s = instalar()
quedan = instaladas()
chequear("instalar quita lo retirado: lo del registro y lo de la lista cerrada", not {"senior-memoria", "senior-refactor", "senior-vieja"} & set(quedan), quedan)
chequear("conserva lo del usuario, lo de otro paquete y el diseñador", {"mi-skill", "senior-lenguajes", "senior-diseno", "auditar-diseno", "senior"} <= set(quedan), quedan)
guardadas = sorted(d.name.rsplit("-", 2)[0] for d in RETIRADAS.iterdir()) if RETIRADAS.is_dir() else []
chequear("lo quitado no se borra: queda fuera de skills, recuperable", guardadas == ["senior-memoria", "senior-refactor", "senior-vieja"], guardadas)
chequear("dice qué quitó y adónde fue", "senior-retiradas" in s and "senior-memoria" in s, s[-900:])
chequear("avisa que el diseñador ahora es un paquete aparte", "paquete de diseño" in s, s[-900:])
rc, s = instalar()
chequear("una segunda vez no tiene nada que quitar", "retirad" not in s, s[-700:])
(SKILLS / ".senior-diseno-instalacion.json").write_text(json.dumps({"skills": {"senior-diseno": "", "auditar-diseno": ""}}), encoding="utf-8")
rc, s = instalar()
chequear("con el diseñador instalado desde su paquete no avisa ni lo toca", "paquete de diseño" not in s and {"senior-diseno", "auditar-diseno"} <= set(instaladas()), s[-700:])

shutil.rmtree(BASE, onerror=_forzar)
print("\nfallos:", mal)
sys.exit(1 if mal else 0)
