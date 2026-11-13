"""Tope de peso de las skills (`peso.py`): hace cumplir los límites, ve los scripts sin caso de uso y respeta las excepciones justificadas."""
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
PESO = RAIZ / "skills" / "senior" / "scripts" / "peso.py"
VERIF = RAIZ / "skills" / "senior" / "scripts" / "verificar.py"
BASE = RAIZ / ".temporal" / "proy-peso"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def skill(raiz, nombre, desc="Una skill de prueba.", cuerpo="Cuerpo breve.\n", scripts=(), refs=(), readme=True):
    d = raiz / "skills" / nombre
    (d / "scripts").mkdir(parents=True, exist_ok=True)
    (d / "references").mkdir(exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {nombre}\ndescription: {desc}\n---\n\n{cuerpo}", encoding="utf-8")
    for s in scripts:
        (d / "scripts" / s).write_text("print(1)\n", encoding="utf-8")
    for r, texto in refs:
        (d / "references" / r).write_text(texto, encoding="utf-8")


def proyecto(nombre):
    p = BASE / nombre
    if p.exists():
        shutil.rmtree(p, onerror=_forzar)
    p.mkdir(parents=True)
    return p


def correr(script, raiz, *args):
    r = subprocess.run([sys.executable, str(script), *args, "--raiz", str(raiz)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


if BASE.exists():
    shutil.rmtree(BASE, onerror=_forzar)

# 1. un paquete sano pasa
p = proyecto("sano")
(p / "README.md").write_text("| `a` | uno |\n| `b` | dos |\n", encoding="utf-8")
skill(p, "a", scripts=["x.py"], cuerpo="Usar `scripts/x.py`.\n")
skill(p, "b")
rc, s = correr(PESO, p)
chequear("un paquete sano pasa", rc == 0 and "0 fallas" in s, (rc, s))

# 2. cada tope falla por separado
p = proyecto("topes")
(p / "README.md").write_text("`larga` `pesada` `larguisima` `refgrande` `muda`\n", encoding="utf-8")
skill(p, "larga", desc="x" * 801)
skill(p, "pesada", cuerpo="palabra " * 3000)
skill(p, "larguisima", cuerpo="\n".join("linea" for _ in range(160)))
skill(p, "refgrande", refs=[("enorme.md", "y" * (5_600 * 4))])
rc, s = correr(PESO, p)
chequear("descripción de más de 800 caracteres falla", "larga: la descripción mide 801" in s, s)
chequear("cuerpo de más de 3.500 tokens falla", "pesada: el cuerpo pesa" in s and "3.500" not in s and "3500" in s, s)
chequear("cuerpo de más de 150 líneas falla", "larguisima: el cuerpo tiene" in s, s)
chequear("una referencia de más de 5.500 tokens falla", "references/enorme.md pesa" in s, s)
chequear("con fallas el código de salida es 1", rc == 1)

# 3. la suma de descripciones tiene tope
p = proyecto("suma")
(p / "README.md").write_text("".join(f"`s{i}` " for i in range(14)), encoding="utf-8")
for i in range(14):
    skill(p, f"s{i}", desc="d" * 790)
rc, s = correr(PESO, p)
chequear("la suma de las descripciones tiene tope", "las descripciones suman" in s and "(paquete)" in s, s)

# 4. un script sin caso de uso y una skill fuera del README
p = proyecto("huerfanos")
(p / "README.md").write_text("`con` \n", encoding="utf-8")
skill(p, "con", scripts=["usado.py", "huerfano.py", "importado.py"], cuerpo="Se usa `scripts/usado.py`.\n")
(p / "skills" / "con" / "scripts" / "usado.py").write_text("import importado\n", encoding="utf-8")
skill(p, "fuera")
rc, s = correr(PESO, p)
chequear("un script sin caso de uso se señala", "huerfano.py no se menciona" in s, s)
chequear("un script que importa otro script o que la documentación nombra no se señala", "usado.py no se menciona" not in s and "importado.py no se menciona" not in s, s)
chequear("una skill que no figura en el README falla", "fuera: no figura en el README" in s, s)

# 5. la excepción justificada se informa y no falla
p = proyecto("excepcion")
(p / "README.md").write_text("`gorda`\n", encoding="utf-8")
skill(p, "gorda", cuerpo="palabra " * 3000 + "\n<!-- excepcion-peso: contiene la tabla completa de la norma -->\n")
rc, s = correr(PESO, p)
chequear("una excepción con motivo pasa y se informa como justificada", rc == 0 and "JUSTIFICADA" in s and "contiene la tabla completa" in s, (rc, s))
p2 = proyecto("excepcion-sin-motivo")
(p2 / "README.md").write_text("`gorda`\n", encoding="utf-8")
skill(p2, "gorda", cuerpo="palabra " * 3000 + "\n<!-- excepcion-peso: -->\n")
chequear("una excepción sin motivo no vale", correr(PESO, p2)[0] == 1)

# 6. el chequeo está en verificar.py y se omite en un proyecto sin skills/
p = proyecto("sin-skills")
rc, s = correr(VERIF, p, "peso")
chequear("en un proyecto sin skills/ se omite sin fallar", rc == 0, (rc, s))
rc, s = correr(VERIF, RAIZ, "peso")
chequear("verificar.py peso corre sobre este paquete y pasa", rc == 0 and "dentro de los topes" in s, (rc, s))

sys.exit(1 if mal else 0)
