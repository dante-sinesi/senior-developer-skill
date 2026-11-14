"""auditar-consumo --repo mide las skills del repositorio, no las instaladas: un recorte se ve sin reinstalar."""
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
CONSUMO = RAIZ / "skills" / "auditar-consumo" / "scripts" / "consumo.py"
BASE = RAIZ / ".temporal" / "pcons-repo"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def escribir(ruta, texto):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")


def skill(nombre, descripcion, cuerpo):
    return f"---\nname: {nombre}\ndescription: {descripcion}\n---\n\n# {nombre}\n\n{cuerpo}\n"


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
P, HOME = BASE / "paquete", BASE / "casa"
escribir(P / "skills" / "chica" / "SKILL.md", skill("chica", "Hace algo corto.", "Cuerpo corto."))
escribir(P / "skills" / "larga" / "SKILL.md", skill("larga", "Una descripción muy larga. " * 60, "Línea de cuerpo.\n" * 700))
escribir(P / "skills" / "larga" / "references" / "detalle.md", "x" * 4000)
escribir(HOME / ".claude" / "skills" / "instalada" / "SKILL.md", skill("instalada", "Solo está instalada, no está en el repositorio.", "Cuerpo."))
escribir(HOME / ".claude" / "CLAUDE.md", "y" * 12000)


def correr(*args):
    r = subprocess.run([sys.executable, str(CONSUMO), "--raiz", str(P), "--home", str(HOME), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


rc, s = correr("--repo", "--json")
r = json.loads(s)
nombres = sorted(x["nombre"] for x in r["skills"])
chequear("--repo mide las skills de la carpeta skills/ y no las instaladas", nombres == ["chica", "larga"] and all(x["origen"] == "repositorio" for x in r["skills"]), nombres)
chequear("no mezcla lo de la máquina: sin CLAUDE.md, memoria ni ajustes", r["instrucciones"] == [] and r["memoria"] is None and r["ajustes"]["hooks"] == 0 and r["fijo"]["instrucciones"] == 0)
chequear("marca la descripción larga y el cuerpo grande", any("larga" in h and "caracteres" in h for h in r["hallazgos"]) and any("larga" in h and "líneas" in h for h in r["hallazgos"]), r["hallazgos"])
rc, s = correr("--repo")
chequear("el resumen dice que es el repositorio y lista lo que más pesa", "Skills del repositorio" in s and "larga" in s and "no de lo instalado" in s and rc == 1, s)
chequear("sin --repo sigue midiendo lo instalado", "instalada" in correr("--json")[1] and "chica" not in correr("--json")[1])

# el recorte se ve sin reinstalar
antes = json.loads(correr("--repo", "--json")[1])["fijo"]["descripciones"]
escribir(P / "skills" / "larga" / "SKILL.md", skill("larga", "Descripción corta.", "Cuerpo breve."))
despues = json.loads(correr("--repo", "--json")[1])
chequear("tras recortar la skill, la medición baja al instante", despues["fijo"]["descripciones"] < antes and despues["hallazgos"] == [], (antes, despues["fijo"]))
rc, s = correr("--repo")
chequear("sin hallazgos sale con 0", rc == 0 and "Para revisar" not in s, s)

# sin carpeta skills/
vacio = BASE / "vacio"
vacio.mkdir()
r = subprocess.run([sys.executable, str(CONSUMO), "--raiz", str(vacio), "--home", str(HOME), "--repo"], capture_output=True, text=True, encoding="utf-8", errors="replace")
chequear("sin carpeta skills/ lo dice y falla", r.returncode != 0 and "carpeta skills/" in r.stderr, r.stderr)

# el repositorio real
r = subprocess.run([sys.executable, str(CONSUMO), "--raiz", str(RAIZ), "--home", str(HOME), "--repo", "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace")
real = json.loads(r.stdout)
chequear("sobre este repositorio mide las skills del paquete", len(real["skills"]) >= 16 and any(x["nombre"] == "senior" for x in real["skills"]), len(real["skills"]))

sk = (RAIZ / "skills" / "auditar-consumo" / "SKILL.md").read_text(encoding="utf-8")
rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("la skill y el README explican --repo", "--repo" in sk and "--repo" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
