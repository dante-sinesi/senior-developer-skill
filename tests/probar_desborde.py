"""Desborde horizontal (medido en un navegador real) y lo que el visor oculta de verdad."""
import io
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "skills" / "senior-diseno" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import capturar  # noqa: E402
import desborde  # noqa: E402
import ver_propuestas as vp  # noqa: E402

P = RAIZ / ".temporal" / "proy-desborde"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)
CABEZA = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'

# ---- lo que no necesita navegador: las plantillas y las reglas escritas
bosquejo = (RAIZ / "skills" / "senior-diseno" / "plantillas" / "bosquejo.html").read_text(encoding="utf-8")
chequear("la plantilla de bosquejo trae la base estructural contra el desborde y la regla escrita",
         "box-sizing: border-box" in bosquejo and "max-width: 100%" in bosquejo and "overflow-wrap: anywhere" in bosquejo and "SIN DESBORDE HORIZONTAL" in bosquejo)
chequear("la plantilla de la tarjeta de estilo trae la misma base", "box-sizing: border-box" in (RAIZ / "skills" / "senior-diseno" / "plantillas" / "estilo.html").read_text(encoding="utf-8"))
visor = (RAIZ / "skills" / "senior-diseno" / "plantillas" / "visor-propuestas.html").read_text(encoding="utf-8")
chequear("el visor no deja que un display propio le gane al atributo hidden", "[hidden] { display: none !important; }" in visor)
skill = (RAIZ / "skills" / "senior-diseno" / "SKILL.md").read_text(encoding="utf-8")
chequear("el SKILL.md de diseño explica el chequeo de desborde", "desborde" in skill.lower() and "390" in skill)

PRUEBA_VIVA = None
if capturar.buscar_navegador():
    (P / "vivo.html").write_text(CABEZA + "<p>vivo</p>", encoding="utf-8")
    PRUEBA_VIVA = desborde.medir(P / "vivo.html", 390)  # ¿el navegador de esta máquina responde? (un Edge colgado devuelve vacío)
if not capturar.buscar_navegador() or PRUEBA_VIVA is None:
    print("ok   (" + ("sin Edge ni Chrome" if not capturar.buscar_navegador() else "el navegador de esta máquina no respondió a una página trivial") + ": se omiten las pruebas que miden en un navegador)")
    print("Todo bien." if not mal else f"{mal} casos mal.")
    sys.exit(1 if mal else 0)

def omite(medicion):
    """True (y lo dice) si el navegador no dio la medición: lo que depende de ella se omite en vez de dar un rojo del entorno."""
    vacia = medicion is None or (isinstance(medicion, list) and any("no se pudo medir" in x.get("msg", "") for x in medicion))
    if vacia:
        print("ok   (omitida: el navegador no devolvió la medición en esta máquina)")
    return vacia


# ---- medir de verdad
(P / "malo.html").write_text(CABEZA + '<body style="margin:0"><div style="width:700px;background:#ccc">ancho fijo</div>', encoding="utf-8")
(P / "bueno.html").write_text(CABEZA + '<body style="margin:0"><div style="max-width:100%">todo entra</div>'
                              '<pre style="overflow-x:auto;width:100%">una línea de código muy larga muy larga muy larga muy larga muy larga muy larga muy larga muy larga muy larga</pre>', encoding="utf-8")
(P / "justificado.html").write_text(CABEZA + '<!-- excepcion-desborde: menú que entra deslizando desde afuera --><body style="margin:0"><div style="width:700px">menú</div>', encoding="utf-8")
(P / "grid.html").write_text(CABEZA + '<body style="margin:0"><div style="display:grid;grid-template-columns:1fr"><pre>' + "x" * 200 + "</pre></div>", encoding="utf-8")

r = desborde.medir(P / "malo.html", 390)
if not omite(r):
    chequear("una página con un bloque de 700 px desborda a 390 px y dice cuánto y qué elemento", r and desborde.hay_desborde(r) and r["pagina"] >= 700 and r["culpables"][0]["el"] == "div", r)
rb = desborde.medir(P / "bueno.html", 390)
if not omite(rb):
    chequear("una página que entra, aunque tenga código ancho en un contenedor con scroll, no desborda", not desborde.hay_desborde(rb))
r = desborde.medir(P / "grid.html", 390)
if not omite(r):
    chequear("el caso típico: un bloque de código dentro de un grid sin min-width: 0 desborda", desborde.hay_desborde(r), r)
h = desborde.hallazgos(P / "malo.html")
if not omite(h):
    chequear("el hallazgo es FALLA y trae cómo arreglarlo", h and h[0]["sev"] == "FALLA" and h[0]["chequeo"] == "desborde" and "min-width: 0" in h[0]["msg"], h)
    chequear("a 1280 px el mismo bloque de 700 px entra", not any("1280" in x["msg"] for x in h))
hj = desborde.hallazgos(P / "justificado.html")
if not omite(hj):
    chequear("una excepción escrita lo deja como JUSTIFICADA", hj[0]["sev"] == "JUSTIFICADA", hj)

R = subprocess.run([sys.executable, str(SCRIPTS / "revisar_diseno.py"), "todo", str(P / "malo.html"), str(P / "bueno.html")], capture_output=True, text=True, encoding="utf-8")
if "no se pudo medir" in R.stdout:
    print("ok   (omitida: el navegador no devolvió la medición en esta máquina)")
else:
    chequear("revisar_diseno todo marca la falla de desborde y sale con 1", R.returncode == 1 and "FALLA       desborde    malo.html" in R.stdout and "bueno.html" not in R.stdout.split("desborde")[-1], R.stdout + R.stderr)
R = subprocess.run([sys.executable, str(SCRIPTS / "revisar_diseno.py"), "desborde", str(P / "bueno.html")], capture_output=True, text=True, encoding="utf-8")
chequear("el chequeo desborde se puede correr solo y no marca FALLA en una página que entra (un AVISO de «no se pudo medir» por un navegador lento es del entorno)",
         R.returncode == 0 and "FALLA" not in R.stdout and "desborda" not in R.stdout.lower(), R.stdout + R.stderr)
import revisar_diseno as rd  # noqa: E402
chequear("las llamadas desde otros scripts (analizar) no abren un navegador", "desborde" not in rd.CHEQUEOS)

# ---- el visor oculta de verdad lo que dice ocultar
JS = ("function disp(s){var e=d.querySelector(s);return e?w.getComputedStyle(e).display:'(falta)';}"
      "return {vista: disp('#grupo-vista'), pestanas: disp('#pantallas'), titulo_pest: disp('#tit-pantallas'), notas: disp('#etq-notas'), pend: disp('#nota-pend'), alternativas: d.querySelectorAll('#lista li').length, pestanas_n: d.querySelectorAll('#pantallas li').length, texto_pest: (d.querySelector('#tit-pantallas')||{}).textContent};")
V = P / "visor-simple"
V.mkdir()
(V / "direccion-a.html").write_text(CABEZA + "<p>a</p>", encoding="utf-8")
(V / "direccion-b.html").write_text(CABEZA + "<p>b</p>", encoding="utf-8")
vp.crear(V, "Una pantalla, un modo", ["desktop"])
v = desborde.evaluar(V / "ver.html", JS, 1280, 800, quitar_herramientas=False)
if not omite(v):
    chequear("con una sola pantalla la pestaña (General) se ve igual, bajo su título «Pestañas», y no se mezcla con las alternativas", v["pestanas"] != "none" and v["titulo_pest"] != "none" and v["texto_pest"] == "Pestañas" and v["pestanas_n"] == 1 and v["alternativas"] == 2, v)
    chequear("con un solo modo no se ven los botones Desktop, Mobile y Ambas", v["vista"] == "none", v)
W = P / "visor-varios"
W.mkdir()
for n in ("inicio__a.html", "inicio__b.html", "ajustes__a.html", "ajustes__b__desktop.html"):
    (W / n).write_text(CABEZA + "<p>x</p>", encoding="utf-8")
vp.crear(W, "Varias pantallas, dos modos")
v = desborde.evaluar(W / "ver.html", JS, 1280, 800, quitar_herramientas=False)
if not omite(v):
    chequear("con varias pantallas sí se ven las pestañas, los botones de modo y la nota de pendientes", v["pestanas"] != "none" and v["vista"] != "none" and v["pend"] != "none" and v["alternativas"] == 2, v)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
