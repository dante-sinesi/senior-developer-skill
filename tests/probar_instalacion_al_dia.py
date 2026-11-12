"""Lo instalado en ~/.claude/skills y el repositorio no se desalinean sin que nadie lo note: la instalación se registra y `asegurar` avisa."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
BASE = RAIZ / ".temporal" / "proy-instalacion"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
ORIGEN, CASA = BASE / "origen", BASE / "casa"
ORIGEN.mkdir(parents=True)
CASA.mkdir()
shutil.copytree(RAIZ / "skills", ORIGEN / "skills", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy(RAIZ / "instalar.py", ORIGEN / "instalar.py")
ENV = {**os.environ, "USERPROFILE": str(CASA), "HOME": str(CASA), "SENIOR_HOOK_DEPURAR": "1"}
MANIFIESTO = CASA / ".claude" / "skills" / ".senior-instalacion.json"


def instalar(*args):
    r = subprocess.run([sys.executable, "-X", "utf8", str(ORIGEN / "instalar.py"), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ORIGEN, env=ENV)
    return r.stdout + r.stderr


def asegurar():
    codigo = ("import sys; sys.path.insert(0, r'" + str(RAIZ / "skills" / "senior-git" / "scripts") + "'); import guardia_autoria as g; "
              "print(chr(10).join(g.asegurar_instalacion()))")
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    return (r.stdout + r.stderr).strip()


# antes de instalar nunca hubo registro
chequear("sin instalación previa avisa que no hay registro", "no tiene registro" in asegurar(), asegurar())

# 1. instalar registra de dónde vino y la huella de cada skill
salida = instalar()
datos = json.loads(MANIFIESTO.read_text(encoding="utf-8")) if MANIFIESTO.exists() else {}
chequear("instalar crea el registro con el origen, la fecha y una huella por skill",
         datos.get("origen") == ORIGEN.resolve().as_posix() and datos.get("fecha") and len(datos.get("skills", {})) >= 16 and "senior" in datos["skills"], (datos.get("origen"), salida[-300:]))
chequear("recién instalado, todo está al día", asegurar() == "", asegurar())

# 2. el repositorio cambia y nadie reinstala
(ORIGEN / "skills" / "senior" / "scripts" / "modo_hooks.py").write_text(
    (ORIGEN / "skills" / "senior" / "scripts" / "modo_hooks.py").read_text(encoding="utf-8") + "\n# cambio nuevo sin instalar\n", encoding="utf-8")
(ORIGEN / "skills" / "senior-git" / "SKILL.md").write_text((ORIGEN / "skills" / "senior-git" / "SKILL.md").read_text(encoding="utf-8") + "\nOtra línea.\n", encoding="utf-8")
a = asegurar()
chequear("avisa qué skills tienen cambios sin instalar y cómo instalarlas", "tiene cambios que no están instalados" in a and "senior, senior-git" in a and "instalar.py" in a and "los hooks siguen usando la versión instalada" in a, a)
salida = instalar("--verificar")
chequear("instalar.py --verificar lo informa como aviso y como skills desactualizadas", "AVISO" in salida and "tiene cambios que no están instalados" in salida and "desactualizadas: senior, senior-git" in salida, salida)

# 3. reinstalar lo deja al día
instalar()
chequear("reinstalar vuelve a dejar todo al día", asegurar() == "", asegurar())

# 4. lo instalado se toca a mano
destino = CASA / ".claude" / "skills" / "senior" / "scripts" / "modo_hooks.py"
destino.write_text(destino.read_text(encoding="utf-8") + "\n# retoque a mano\n", encoding="utf-8")
a = asegurar()
chequear("avisa si una skill instalada se modificó a mano", "se modificaron después de instalarlas (senior)" in a, a)
instalar()

# 5. el repositorio de origen se movió o el registro está roto
shutil.move(str(ORIGEN / "skills"), str(BASE / "skills-movidas"))
a = asegurar()
chequear("si el repositorio de origen ya no está, lo dice sin fallar", "no se encuentra el repositorio de origen" in a, a)
shutil.move(str(BASE / "skills-movidas"), str(ORIGEN / "skills"))
MANIFIESTO.write_text("{no es json", encoding="utf-8")
chequear("un registro dañado se avisa y se rehace al instalar", "dañado" in asegurar() and (instalar() or True) and asegurar() == "")

# 6. skills que no son del paquete no cuentan
otra = CASA / ".claude" / "skills" / "otra-skill"
otra.mkdir()
(otra / "SKILL.md").write_text("---\nname: otra-skill\n---\n", encoding="utf-8")
chequear("una skill ajena instalada al lado no genera avisos", asegurar() == "", asegurar())

# 7. asegurar lo muestra aunque sea silencioso
codigo = ("import sys; sys.path.insert(0, r'" + str(RAIZ / "skills" / "senior-git" / "scripts") + "'); import guardia_autoria as g; "
          "from pathlib import Path; g.cmd_asegurar(Path(r'" + str(BASE) + "'), True, True)")
(ORIGEN / "skills" / "senior" / "SKILL.md").write_text((ORIGEN / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8") + "\nx\n", encoding="utf-8")
r = subprocess.run([sys.executable, "-X", "utf8", "-c", codigo], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
chequear("asegurar --silencioso igual muestra el aviso de instalación", "tiene cambios que no están instalados" in r.stdout, r.stdout + r.stderr)

rd = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("el README explica el aviso de instalación desactualizada", "instalación desactualizada" in rd.lower() and ".senior-instalacion.json" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
