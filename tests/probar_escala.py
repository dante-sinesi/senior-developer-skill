import io
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "skills" / "senior" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import escala  # noqa: E402
import verificar  # noqa: E402

P = RAIZ / ".temporal" / "proy-escala"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def escribir(ruta, texto):
    f = P / ruta
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


def cli(*args):
    p = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "escala.py"), *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


# 1. los niveles se muestran completos y cada uno suma al anterior
rc, s = cli("niveles")
chequear("muestra los tres niveles", all(x in s for x in ("Pequeño:", "Mediano:", "Grande:")), s[:200])
chequear("el mediano y el grande dicen que incluyen lo anterior", s.count("Incluye todo lo del nivel anterior") == 2)
chequear("el grande detalla arquitectura, requisitos, seguridad, cobertura y costo",
         all(x in s for x in ("Arquitectura primero", "trazabilidad", "registro de riesgos", "cobertura mínima", "más lento a propósito")))
rc, s = cli("niveles", "--nivel", "grande")
chequear("--nivel muestra solo ese", "Grande:" in s and "Pequeño:" not in s)

# 2. proyecto sin docs/: no dice nada
if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)
escribir("app.py", "x = 1\n")
chequear("sin docs/ no avisa nada", escala.evaluar(P) == ([], True))

# 3. con ESTADO.md sin escala: pide declararla
plantilla = (RAIZ / "skills" / "senior-memoria" / "plantillas" / "ESTADO.md").read_text(encoding="utf-8")
chequear("la plantilla de ESTADO trae la línea de escala", "**Escala del proyecto:**" in plantilla)
escribir("docs/ESTADO.md", "# Estado del proyecto\n\n**Última actualización:** 2026-01-01\n\n## Dónde estamos\n")
lin, ok = escala.evaluar(P)
chequear("sin declarar: falla y manda a preguntar", (not ok) and "sin declarar" in lin[0] and "niveles" in lin[0], lin)

# 4. fijar escribe y reemplaza
rc, s = cli("fijar", "mediano", "--raiz", str(P))
t = (P / "docs" / "ESTADO.md").read_text(encoding="utf-8")
chequear("fijar inserta la línea bajo la última actualización", rc == 0 and "**Escala del proyecto:** mediano" in t and t.index("Última") < t.index("Escala"), t)
cli("fijar", "grande", "--raiz", str(P))
t = (P / "docs" / "ESTADO.md").read_text(encoding="utf-8")
chequear("fijar de nuevo reemplaza, no duplica", t.count("Escala del proyecto") == 1 and "grande" in t, t)
chequear("la escala declarada se lee", escala.declarada(P) == "grande")
rc, s = cli("fijar", "enorme", "--raiz", str(P))
chequear("un nivel inválido se rechaza", rc != 0)
rc, s = cli("fijar", "mediano", "--raiz", str(P / "no-existe"))
chequear("sin ESTADO.md no fija", rc != 0 and "adopta" in s, s)

# 5. el nivel grande exige lo suyo
lin, ok = escala.evaluar(P)
chequear("grande vacío: falta README, tests, ADR, diagramas, requisitos, riesgos y cobertura",
         (not ok) and all(x in lin[0] for x in ("README", "tests", "ADR", "diagramas", "requisitos", "riesgos", "cobertura")), lin)
escribir("README.md", "# P\n")
escribir("tests/test_app.py", "def test_x():\n    assert True\n")
escribir("docs/decisiones/0001-arquitectura.md", "# ADR\n")
escribir("docs/diagramas/clases.md", "```mermaid\nclassDiagram\n```\n")
escribir("docs/requisitos/negocio/RN-001.md", "# RN\n")
escribir("docs/seguridad/riesgos.md", "# Riesgos\n")
lin, ok = escala.evaluar(P)
chequear("sin umbral de cobertura sigue faltando solo eso", (not ok) and "cobertura" in lin[0] and "ADR" not in lin[0], lin)
escribir("pyproject.toml", "[tool.coverage.report]\nfail_under = 85\n")
lin, ok = escala.evaluar(P)
chequear("con todo, el grande queda en orden", ok and "lo que exige el nivel está" in lin[0], lin)

# 6. los niveles menores piden menos
cli("fijar", "pequeño", "--raiz", str(P))
shutil.rmtree(P / "tests")
(P / "README.md").unlink()
lin, ok = escala.evaluar(P)
chequear("pequeño no exige README ni tests", ok, lin)
cli("fijar", "mediano", "--raiz", str(P))
lin, ok = escala.evaluar(P)
chequear("mediano exige README y tests si hay código", (not ok) and "README" in lin[0] and "tests" in lin[0], lin)

# 7. la escala evoluciona sola: sin preguntar, sin bajar y sin bloquear
cli("fijar", "pequeño", "--raiz", str(P))
for i in range(160):
    escribir(f"src/m{i}.py", "x = 1\n")
lin, ok = escala.evaluar(P)
chequear("antes de evolucionar, verificar lo informa y no bloquea", ok and any("ya corresponde al nivel grande" in l for l in lin), (ok, lin))
chequear("sugerir por tamaño", escala.sugerir(5) == "pequeño" and escala.sugerir(50) == "mediano" and escala.sugerir(300) == "grande")
msg = escala.evolucionar(P)
chequear("evolucionar sube de pequeño a grande sin preguntar", "sin preguntar" in msg and escala.declarada(P) == "grande", msg)
t = (P / "docs" / "ESTADO.md").read_text(encoding="utf-8")
chequear("deja escrito que subió sola, desde qué nivel y por qué", "subió sola desde pequeño" in t and "161 archivos" in t, t)
chequear("quedó marcado como subida sola", escala.subio_sola(P))
lin, ok = escala.evaluar(P)
chequear("lo que el nivel nuevo suma es una guía, no un bloqueo", ok and "como guía" in lin[0], (ok, lin))
chequear("evolucionar de nuevo no hace nada", escala.evolucionar(P) == "")
rc, s = cli("estado", "--raiz", str(P))
chequear("estado sale con 0 aunque falte cosas del nivel nuevo", rc == 0, s)

# no baja nunca: un proyecto chico declarado grande por el usuario sigue grande
cli("fijar", "grande", "--raiz", str(P))
for f in (P / "src").glob("*.py"):
    f.unlink()
chequear("no baja el nivel cuando el proyecto achica", escala.evolucionar(P) == "" and escala.declarada(P) == "grande")
chequear("un nivel fijado por el usuario no queda marcado como subida sola", not escala.subio_sola(P))
lin, ok = escala.evaluar(P)
chequear("lo que eligió el usuario sí se exige", (not ok) or "lo que exige el nivel está" in lin[0], lin)

# crece de mediano a grande: el segundo salto también es solo
cli("fijar", "mediano", "--raiz", str(P))
for i in range(160):
    escribir(f"src/n{i}.py", "x = 1\n")
msg = escala.evolucionar(P)
chequear("de mediano a grande también sube sola", escala.declarada(P) == "grande" and "mediano a grande" in msg, msg)

# 8. integración con verificar.py
class A:
    base = "HEAD"


lin, ok = verificar.chequeo_escala(P, A())
chequear("verificar.py incluye el chequeo", "escala" in verificar.CHEQUEOS and lin)

# 9. la documentación lo enlaza
adoptar = (RAIZ / "skills" / "adoptar-proyecto" / "SKILL.md").read_text(encoding="utf-8")
senior = ((RAIZ / "skills") / "senior" / "SKILL.md").read_text(encoding="utf-8") + (((RAIZ / "skills") / "senior" / "references" / "metodo-completo.md").read_text(encoding="utf-8"))
readme = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("adoptar-proyecto manda a preguntar la escala", "escala.py niveles" in adoptar and "escala.py fijar" in adoptar)
chequear("senior pregunta la escala una sola vez y la deja evolucionar", "se pregunta una sola vez" in senior and "no se vuelve a preguntar" in senior and "escala.py evolucionar" in senior)
chequear("cerrar-sesion corre estado, que evoluciona sin preguntar", "escala.py estado" in (RAIZ / "skills" / "cerrar-sesion" / "SKILL.md").read_text(encoding="utf-8"))
chequear("el README la explica", "Escala del proyecto" in readme and "`escala`" in readme)


# 12. escala: el nivel grande con interfaz exige la tarjeta
G = RAIZ / ".temporal" / "proy-escala-interfaz"
if G.exists():
    shutil.rmtree(G, onerror=_forzar)
(G / "docs").mkdir(parents=True)
(G / "index.html").write_text("<html></html>", encoding="utf-8")
chequear("hay_interfaz detecta páginas y Godot", escala.hay_interfaz(G))
chequear("grande con interfaz y sin tarjeta: falta la tarjeta", any("tarjeta de estilo" in f for f in escala.faltantes(G, "grande")))
(G / "docs/diseno/estilo").mkdir(parents=True)
(G / "docs/diseno/estilo/tarjeta.html").write_text("<html></html>", encoding="utf-8")
chequear("con tarjeta ya no falta", not any("tarjeta de estilo" in f for f in escala.faltantes(G, "grande")))
chequear("el mediano la recomienda y el grande la exige", "tarjeta de estilo viva" in escala.texto_niveles("mediano") and "obligatoria" in escala.texto_niveles("grande"))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
