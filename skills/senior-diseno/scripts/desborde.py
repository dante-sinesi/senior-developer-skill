#!/usr/bin/env python3
"""Mide en un navegador de verdad (Edge o Chrome ya instalados, sin interfaz) lo que el análisis estático no ve: si una página se sale de su ancho.

Una página que desborda a lo ancho en mobile (390 px) obliga a deslizar de costado y deja contenido cortado: no se acepta, y no depende de que alguien lo
mire. `revisar_diseno.py` corre esta medición en cada HTML (390 px y 1280 px) y la marca FALLA.

Uso:
    python desborde.py <archivo.html> [--ancho 390] [--alto 844]
        Dice cuánto mide el contenido frente al ancho de la vista y qué elementos se pasan (hasta 5, los de más afuera). Código de salida 1 si desborda,
        2 si no hay navegador.

Cómo mide: carga la página dentro de un marco del ancho pedido (los navegadores sin interfaz no bajan de unos 500 px, y un marco sí respeta las reglas
@media de ese ancho), sin la barra de vistas del bosquejo, y mira el ancho del contenido y la posición de cada elemento. Un elemento dentro de un
contenedor con su propio scroll horizontal (una tabla o un bloque de código) no cuenta. Los archivos de paso van dentro del proyecto y se borran al terminar.
Una excepción justificada se escribe en la página: <!-- excepcion-desborde: motivo --> (un menú que entra deslizando desde afuera, por ejemplo).
Solo biblioteca estándar.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capturar  # noqa: E402

QUITAR = re.compile(r"<(style|script)\b[^>]*\bdata-herramienta\b[^>]*>.*?</\1>", re.S | re.I)
RE_EXCEPCION = re.compile(r"<!--\s*excepcion-desborde\s*:\s*\S", re.I)

JS_DESBORDE = """
var de = d.documentElement, vista = de.clientWidth, res = {vista: vista, pagina: Math.max(de.scrollWidth, d.body ? d.body.scrollWidth : 0), culpables: []}, vistos = {};
function recortado(el) {
  var a = el.parentElement;
  while (a && a !== d.body && a !== de) { var o = w.getComputedStyle(a).overflowX; if (['auto', 'scroll', 'hidden', 'clip'].indexOf(o) >= 0) return true; a = a.parentElement; }
  return false;
}
d.querySelectorAll('body *').forEach(function (el) {
  var cs = w.getComputedStyle(el);
  if (cs.position === 'fixed' || cs.display === 'none') return;
  var b = el.getBoundingClientRect();
  if (b.width === 0 || b.right <= vista + 1 || recortado(el)) return;
  var clase = (typeof el.className === 'string' && el.className.trim()) ? '.' + el.className.trim().split(/\\s+/)[0] : '';
  var k = el.tagName.toLowerCase() + clase;
  if (!vistos[k]) { vistos[k] = 1; res.culpables.push({el: k, derecha: Math.round(b.right)}); }
});
res.culpables.sort(function (a, b) { return b.derecha - a.derecha; });
res.culpables = res.culpables.slice(0, 5);
return res;
"""

ENVOLTURA = """<!doctype html><meta charset="utf-8"><body style="margin:0">
<iframe id="f" style="border:0;display:block;width:{ancho}px;height:{alto}px" srcdoc="{contenido}"></iframe><pre id="resultado"></pre>
<script>
var f = document.getElementById('f');
f.onload = function () {{
  setTimeout(function () {{
    var salida;
    try {{ salida = (function (d, w) {{ {js} }})(f.contentDocument, f.contentWindow); }} catch (e) {{ salida = {{error: String(e)}}; }}
    document.getElementById('resultado').textContent = JSON.stringify(salida);
  }}, 400);
}};
</script>"""


def evaluar(ruta, js, ancho=1280, alto=800, quitar_herramientas=True, navegador=None):
    """Carga la página en un marco de `ancho` px, corre `js` (cuerpo de una función con `d` = documento y `w` = ventana del marco) y devuelve lo que ese
    código retorne, o None si no hay navegador o no respondió."""
    navegador = navegador or capturar.buscar_navegador()
    if not navegador:
        return None
    ruta = Path(ruta).resolve()
    texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
    if quitar_herramientas:
        texto = QUITAR.sub("", texto)
    # sin la barra de desplazamiento (en un celular es superpuesta y no le resta ancho) y con los archivos que la página pida saliendo de su carpeta
    texto = f'<base href="{ruta.parent.as_uri()}/"><style>html{{scrollbar-width:none}}::-webkit-scrollbar{{display:none}}</style>' + texto
    paso = Path(tempfile.mkdtemp(dir=ruta.parent))
    perfil = paso / "perfil"
    try:
        pagina = paso / "medir.html"
        pagina.write_text(ENVOLTURA.format(ancho=ancho, alto=alto, contenido=html.escape(texto, quote=True), js=js), encoding="utf-8")
        cmd = [navegador, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={perfil}", "--virtual-time-budget=5000",
               "--dump-dom", pagina.as_uri()]
        try:
            salida = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90).stdout
        except subprocess.TimeoutExpired:
            return None
        m = re.search(r'<pre id="resultado">(.*?)</pre>', salida, re.S)
        if not m or not m.group(1).strip():
            return None
        return json.loads(html.unescape(m.group(1)))
    finally:
        shutil.rmtree(paso, ignore_errors=True)


def medir(ruta, ancho=390, alto=844):
    """{'vista', 'pagina', 'culpables': [{'el', 'derecha'}]} o None si no se pudo medir."""
    r = evaluar(ruta, JS_DESBORDE, ancho, alto)
    return None if not r or "error" in r else r


def hay_desborde(r):
    return bool(r) and (r["pagina"] > r["vista"] + 1 or bool(r["culpables"]))


def mensaje(r, ancho):
    partes = []
    if r["pagina"] > r["vista"] + 1:
        partes.append(f"el contenido mide {r['pagina']} px y la vista {r['vista']} px (sobran {r['pagina'] - r['vista']}): hay que deslizar de costado")
    if r["culpables"]:
        partes.append("elementos que se pasan: " + ", ".join(f"{c['el']} (llega a {c['derecha']} px)" for c in r["culpables"]))
    return f"a {ancho} px: " + "; ".join(partes) + ". Arreglar con anchos relativos, flex/grid con min-width: 0, imágenes con max-width: 100% o un contenedor con overflow-x: auto"


def hallazgos(ruta, anchos=(390, 1280)):
    """Hallazgos (dicts como los de revisar_diseno) de desborde horizontal de un HTML; un único AVISO si no hay navegador."""
    ruta = Path(ruta)
    if not capturar.buscar_navegador():
        return [{"chequeo": "desborde", "sev": "AVISO", "archivo": str(ruta), "linea": 1,
                 "msg": "no se pudo medir el desborde horizontal: no hay Edge ni Chrome instalados"}]
    justificada = bool(RE_EXCEPCION.search(ruta.read_text(encoding="utf-8-sig", errors="replace")))
    res = []
    for ancho in anchos:
        r = medir(ruta, ancho, 844 if ancho < 600 else 800)
        if r is None:
            res.append({"chequeo": "desborde", "sev": "AVISO", "archivo": str(ruta), "linea": 1, "msg": f"no se pudo medir el desborde a {ancho} px (el navegador no respondió)"})
        elif hay_desborde(r):
            res.append({"chequeo": "desborde", "sev": "JUSTIFICADA" if justificada else "FALLA", "archivo": str(ruta), "linea": 1, "msg": mensaje(r, ancho)})
    return res


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--ancho", type=int, default=390)
    ap.add_argument("--alto", type=int, default=844)
    a = ap.parse_args()
    if not Path(a.archivo).is_file():
        sys.exit(f"No existe: {a.archivo}")
    if not capturar.buscar_navegador():
        print("No se encontró Edge ni Chrome instalados: no se puede medir.")
        sys.exit(2)
    r = medir(a.archivo, a.ancho, a.alto)
    if r is None:
        print("No se pudo medir (el navegador no respondió).")
        sys.exit(2)
    if hay_desborde(r):
        print("DESBORDA " + mensaje(r, a.ancho))
        sys.exit(1)
    print(f"Sin desborde a {a.ancho} px (contenido {r['pagina']} px, vista {r['vista']} px).")


if __name__ == "__main__":
    main()
