#!/usr/bin/env python3
"""Tarjetas SVG para el README de un repositorio: un motor NEUTRO que aplica reglas objetivas; el estilo lo inventa el diseñador en cada proyecto.

El motor no trae ningún aspecto propio. Dibuja la estructura (portada, cifra, antes y después), exige el pie de foto, pone el sello de origen
en las tarjetas con cifras, ajusta el texto al ancho y comprueba el contraste. Todo lo estético (colores, tipografía, composición y
decoración libre en SVG) vive en un TEMA, un JSON que el diseñador escribe para el proyecto a partir de su descripción.

Uso:
    python readme_tarjetas.py generar   [--raiz .] [--fuente docs/tarjetas] [--salida docs/img] [--estilo <tema.json>] [--idioma es|en]
    python readme_tarjetas.py comparar  --tarjeta <tarjeta.json> --estilos a.json b.json [c.json] [--salida .temporal/estilos] [--idioma es|en]
    python readme_tarjetas.py verificar [--raiz .] [--fuente docs/tarjetas] [--salida docs/img]
    python readme_tarjetas.py bloque    <nombre> [--raiz .] [--ancho 760]       # el bloque de Markdown para pegar la tarjeta en el README

Tarjetas (un JSON por tarjeta, en `docs/tarjetas/`; el SVG sale en `docs/img/<nombre>.svg`):
  portada        {"tipo": "portada", "titulo": "...", "subtitulo": "...", "pie": "..."}
  cifra          {"tipo": "cifra", "valor": "-57 %", "etiqueta": "...", "origen": "medido|esperado", "nota": "...", "pie": "..."}
  antes_despues  {"tipo": "antes_despues", "titulo": "...", "antes": {"etiqueta": "...", "valor": N}, "despues": {"etiqueta": "...", "valor": N},
                  "origen": "medido|esperado", "nota": "...", "pie": "..."}
Reglas que el motor hace cumplir (el aspecto es libre, esto no):
  - toda tarjeta lleva un «pie»: una frase que dice qué muestra. Va en el <desc> del SVG, en el `alt` y debajo de la imagen en el README;
  - toda tarjeta con cifras lleva «origen» (medido o esperado) y un sello; una «esperada» necesita una «nota» que diga cómo se calculó la cifra;
    una cifra esperada nunca se mezcla con una medida (el origen es de la tarjeta entera) y nunca se inventa ni se redondea a favor;
  - una idea por tarjeta, sin saturar: título hasta 40 caracteres, subtítulo hasta 90;
  - contraste de texto de al menos 4,5:1 contra el fondo (y 3:1 para el color de acento);
  - la decoración es SVG libre pero sin scripts, sin eventos, sin recursos externos ni foreignObject, y cada SVG pesa menos de 200 KB.
El tema (JSON): ver `senior-diseno/references/tarjetas-readme.md`. Solo biblioteca estándar.
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

TIPOS = ("portada", "cifra", "antes_despues")
CON_CIFRAS = ("cifra", "antes_despues")
ORIGENES = ("medido", "esperado")
COMPOSICIONES = ("izquierda", "centrada", "cartel", "dividida")
MAX_TITULO, MAX_SUBTITULO, MAX_BYTES = 40, 90, 200_000
ANCHO, ALTO_POR_DEFECTO, CUADRADOS = 760, 300, 20
SELLOS = {"es": {"medido": "MEDIDO", "esperado": "ESPERADO"}, "en": {"medido": "MEASURED", "esperado": "EXPECTED"}}
COLORES_OBLIGATORIOS = ("fondo", "titulo", "texto", "acento")
PELIGROSO = re.compile(r"(?is)<\s*script|\bon[a-z]+\s*=|foreignobject|@import|(?:href|src)\s*=\s*[\"']\s*(?!data:|#)[^\"']+|url\(\s*[\"']?\s*(?:https?:|//)")


class TarjetaError(ValueError):
    pass


# ---------------------------------------------------------------- color y contraste
def _rgb(color):
    c = str(color).strip().lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", c):
        raise TarjetaError(f"color no válido: {color!r} (usar #rgb o #rrggbb)")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def luminancia(color):
    def canal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(v) for v in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- tema
def validar_tema(tema):
    """Normaliza el tema y comprueba las reglas objetivas. Devuelve el tema completo."""
    if not isinstance(tema, dict):
        raise TarjetaError("el tema tiene que ser un objeto JSON")
    colores = dict(tema.get("colores") or {})
    for k in COLORES_OBLIGATORIOS:
        if k not in colores:
            raise TarjetaError(f"el tema necesita el color «{k}»")
    for k, v in colores.items():
        _rgb(v)
    colores.setdefault("sello_medido", colores["acento"])
    colores.setdefault("sello_esperado", colores["acento"])
    colores.setdefault("barra_antes", colores["texto"])
    colores.setdefault("barra_despues", colores["acento"])
    colores.setdefault("barra_vacia", colores["fondo"])
    for par, minimo in ((("titulo", "fondo"), 4.5), (("texto", "fondo"), 4.5), (("sello_medido", "fondo"), 4.5), (("sello_esperado", "fondo"), 4.5),
                        (("acento", "fondo"), 3.0)):
        c = contraste(colores[par[0]], colores[par[1]])
        if c < minimo:
            raise TarjetaError(f"contraste insuficiente entre «{par[0]}» y «{par[1]}»: {c:.1f}:1 (mínimo {minimo}:1)")
    tipografia = dict(tema.get("tipografia") or {})
    tipografia.setdefault("familia", "Georgia, 'Times New Roman', serif")
    tipografia.setdefault("peso_titulo", 700)
    tipografia.setdefault("peso_texto", 400)
    tipografia.setdefault("mayusculas", False)
    composicion = tema.get("composicion", "izquierda")
    if composicion not in COMPOSICIONES:
        raise TarjetaError(f"composición desconocida: {composicion!r} (opciones: {', '.join(COMPOSICIONES)})")
    alto = int(tema.get("alto", ALTO_POR_DEFECTO))
    if not 200 <= alto <= 400:
        raise TarjetaError("el alto del lienzo va de 200 a 400")
    deco = dict(tema.get("decoracion") or {})
    for k in ("fondo_svg", "frente_svg"):
        if PELIGROSO.search(deco.get(k, "")):
            raise TarjetaError(f"la decoración «{k}» tiene scripts, eventos o recursos externos: no se permite")
    return {"nombre": str(tema.get("nombre", "sin nombre")), "colores": colores, "tipografia": tipografia, "composicion": composicion, "alto": alto,
            "sombra_titulo": tema.get("sombra_titulo"), "decoracion": deco, "fuentes": list(tema.get("fuentes") or [])}


def cargar_json(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise TarjetaError(f"no se pudo leer {ruta}: {e}")


# ---------------------------------------------------------------- validación de una tarjeta
def validar(tarjeta):
    tipo = tarjeta.get("tipo")
    if not str(tarjeta.get("pie", "")).strip():
        raise TarjetaError("toda tarjeta necesita un «pie»: una frase que diga qué muestra la imagen")
    if tipo not in TIPOS:
        raise TarjetaError(f"tipo de tarjeta desconocido: {tipo!r}")
    if tipo == "portada":
        for k in ("titulo", "subtitulo"):
            if not tarjeta.get(k):
                raise TarjetaError(f"la portada necesita «{k}»")
    else:
        if tarjeta.get("origen") not in ORIGENES:
            raise TarjetaError("las tarjetas con cifras necesitan «origen»: medido o esperado")
        if tarjeta["origen"] == "esperado" and not str(tarjeta.get("nota", "")).strip():
            raise TarjetaError("una tarjeta esperada necesita una «nota» que diga cómo se calculó la cifra")
    if tipo == "cifra":
        for k in ("valor", "etiqueta"):
            if not tarjeta.get(k):
                raise TarjetaError(f"la cifra necesita «{k}»")
    if tipo == "antes_despues":
        for k in ("titulo", "antes", "despues"):
            if not tarjeta.get(k):
                raise TarjetaError(f"antes_despues necesita «{k}»")
        for lado in ("antes", "despues"):
            v = tarjeta[lado].get("valor")
            if not isinstance(v, (int, float)) or v < 0 or not tarjeta[lado].get("etiqueta"):
                raise TarjetaError(f"«{lado}» necesita etiqueta y un valor numérico no negativo")
        if tarjeta["antes"]["valor"] <= 0:
            raise TarjetaError("«antes» tiene que ser mayor que cero")
    titulo = str(tarjeta.get("titulo", ""))
    if len(titulo) > MAX_TITULO:
        raise TarjetaError(f"el título tiene {len(titulo)} caracteres (máximo {MAX_TITULO}): una idea por tarjeta")
    if len(str(tarjeta.get("subtitulo", ""))) > MAX_SUBTITULO:
        raise TarjetaError(f"el subtítulo tiene más de {MAX_SUBTITULO} caracteres: sin saturar")


# ---------------------------------------------------------------- texto: ajuste al ancho
def ancho_texto(texto, tam, mayus):
    return len(texto) * tam * (0.70 if mayus else 0.58)


def ajustar(texto, ancho, tam_max, tam_min, mayus):
    tam = tam_max
    while tam > tam_min and ancho_texto(texto, tam, mayus) > ancho:
        tam -= 2
    return tam


def envolver(texto, ancho, tam, mayus, max_lineas=2):
    lineas, actual = [], ""
    for palabra in str(texto).split():
        prueba = (actual + " " + palabra).strip()
        if ancho_texto(prueba, tam, mayus) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas[:max_lineas]


def _t(x, y, tam, peso, color, contenido, ancla="start", extra=""):
    return (f'<text x="{x:g}" y="{y:g}" font-size="{tam}" font-weight="{peso}" fill="{color}" text-anchor="{ancla}"{extra}>'
            f'{escape(str(contenido))}</text>')


def _titulo(tema, x, y, tam, contenido, ancla):
    c, sombra = tema["colores"], tema["sombra_titulo"]
    peso = tema["tipografia"]["peso_titulo"]
    s = _t(x + 4, y + 4, tam, peso, sombra, contenido, ancla) if sombra else ""
    return s + _t(x, y, tam, peso, c["titulo"], contenido, ancla)


# ---------------------------------------------------------------- dibujo
def _zona_texto(tema):
    """(x_inicial, ancho disponible, ancla, x de anclaje) según la composición."""
    comp, alto = tema["composicion"], tema["alto"]
    if comp == "centrada":
        return 80, ANCHO - 160, "middle", ANCHO / 2
    if comp == "dividida":
        return 40, ANCHO - 260, "start", 40
    return 40, ANCHO - 80, "start", 40


def _sello(tema, origen, idioma, x, ancla):
    c = tema["colores"]
    color = c["sello_medido"] if origen == "medido" else c["sello_esperado"]
    texto = SELLOS[idioma][origen]
    ancho = max(116, int(len(texto) * 12 + 28))
    x0 = x - ancho / 2 if ancla == "middle" else x
    trazo = "" if origen == "medido" else ' stroke-dasharray="6 4"'
    return (f'<rect x="{x0:g}" y="36" width="{ancho}" height="34" fill="{c["fondo"]}" stroke="{color}" stroke-width="2"{trazo}/>'
            + _t(x0 + ancho / 2, 59, 15, 700, color, texto, "middle"))


def _cuerpo(tarjeta, tema, idioma):
    c, tip, alto = tema["colores"], tema["tipografia"], tema["alto"]
    x, ancho, ancla, ax = _zona_texto(tema)
    mayus = bool(tip["mayusculas"])
    pone = (lambda s: str(s).upper()) if mayus else str
    tipo = tarjeta["tipo"]
    if tipo == "portada":
        titulo = pone(tarjeta["titulo"])
        tam = ajustar(titulo, ancho, 64, 28, mayus)
        lineas = envolver(tarjeta["subtitulo"], ancho, 22, False)
        if tema["composicion"] == "cartel":
            y_titulo = alto - 64
            sub = "".join(_t(ax, 74 + i * 28, 22, tip["peso_texto"], c["texto"], l, ancla) for i, l in enumerate(lineas))
            return _titulo(tema, ax, y_titulo, tam, titulo, ancla) + sub
        y_titulo = alto * 0.5
        sub = "".join(_t(ax, y_titulo + 50 + i * 28, 22, tip["peso_texto"], c["texto"], l, ancla) for i, l in enumerate(lineas))
        return _titulo(tema, ax, y_titulo, tam, titulo, ancla) + sub
    sello = _sello(tema, tarjeta["origen"], idioma, ax, ancla)
    if tipo == "cifra":
        valor = str(tarjeta["valor"])
        tam = ajustar(valor, ancho, 92, 40, False)
        etiqueta = "".join(_t(ax, alto - 80 + i * 28, 22, tip["peso_texto"], c["texto"], l, ancla) for i, l in enumerate(envolver(tarjeta["etiqueta"], ancho, 22, False)))
        return sello + _titulo(tema, ax, alto - 110, tam, valor, ancla) + etiqueta
    antes, despues = tarjeta["antes"], tarjeta["despues"]
    llenos = round(despues["valor"] / antes["valor"] * CUADRADOS)
    if despues["valor"] > 0:
        llenos = max(1, llenos)
    filas = []
    base = alto - 110
    for i, (lado, n, color) in enumerate(((antes, CUADRADOS, c["barra_antes"]), (despues, llenos, c["barra_despues"]))):
        y = base + i * 44
        filas.append(_t(40, y + 15, 17, tip["peso_texto"], c["texto"], lado["etiqueta"]))
        filas += [f'<rect x="{230 + j * 21}" y="{y}" width="17" height="17" fill="{color if j < n else c["barra_vacia"]}"/>' for j in range(CUADRADOS)]
        filas.append(_t(ANCHO - 30, y + 15, 15, tip["peso_texto"], c["texto"], f"{lado['valor']:,}", "end"))
    return sello + _t(40, base - 26, 24, tip["peso_titulo"], c["titulo"], tarjeta["titulo"]) + "".join(filas)


def _css_fuentes(tema, base):
    partes = []
    for f in tema["fuentes"]:
        ruta = Path(base) / f["archivo"]
        if not ruta.exists():
            raise TarjetaError(f"no existe la fuente {f['archivo']}")
        b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
        partes.append("@font-face{font-family:'%s';font-weight:%s;src:url(data:font/woff2;base64,%s) format('woff2');}" % (f.get("familia", "Incrustada"), f.get("peso", 400), b64))
    return "".join(partes)


def renderizar(tarjeta, tema, idioma="es", base="."):
    validar(tarjeta)
    tema = validar_tema(tema)
    c, alto = tema["colores"], tema["alto"]
    titulo = escape(str(tarjeta.get("titulo") or tarjeta.get("etiqueta") or tema["nombre"]))
    desc = escape(" ".join(p for p in (tarjeta["pie"], tarjeta.get("nota", "")) if p))
    deco = tema["decoracion"]
    css = _css_fuentes(tema, base)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto}" viewBox="0 0 {ANCHO} {alto}" role="img" '
           f'font-family="{escape(tema["tipografia"]["familia"], {chr(34): "&quot;"})}">'
           f"<title>{titulo}</title><desc>{desc}</desc>" + (f"<style>{css}</style>" if css else "")
           + f'<rect width="{ANCHO}" height="{alto}" fill="{c["fondo"]}"/>' + deco.get("fondo_svg", "")
           + _cuerpo(tarjeta, tema, idioma) + deco.get("frente_svg", "") + "</svg>\n")
    if len(svg.encode("utf-8")) > MAX_BYTES:
        raise TarjetaError(f"el SVG pesa {len(svg) // 1024} KB (máximo {MAX_BYTES // 1000} KB): menos decoración o fuentes más livianas")
    return svg


# ---------------------------------------------------------------- operaciones
def tarjetas_de(fuente):
    return [p for p in sorted(Path(fuente).glob("*.json")) if p.stem != "estilo"]


def generar(raiz, fuente, salida, estilo, idioma):
    fuente, salida = Path(raiz) / fuente, Path(raiz) / salida
    ruta_estilo = Path(estilo) if estilo else fuente / "estilo.json"
    if not ruta_estilo.exists():
        raise TarjetaError(f"falta el estilo ({ruta_estilo}): el diseñador lo crea y el usuario lo elige antes de generar")
    tema = cargar_json(ruta_estilo)
    salida.mkdir(parents=True, exist_ok=True)
    escritas = []
    for p in tarjetas_de(fuente):
        try:
            svg = renderizar(cargar_json(p), tema, idioma, base=raiz)
        except TarjetaError as e:
            raise TarjetaError(f"{p.name}: {e}")
        destino = salida / f"{p.stem}.svg"
        destino.write_text(svg, encoding="utf-8", newline="\n")
        escritas.append(destino)
    return escritas


def comparar(tarjeta_json, estilos, salida, idioma, base="."):
    """Dibuja la MISMA tarjeta con cada estilo y arma una página para elegir. Devuelve (ruta de la página, [ruta de cada SVG])."""
    tarjeta = cargar_json(tarjeta_json)
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    bloques, rutas = [], []
    for letra, ruta in zip("ABC", estilos):
        tema = validar_tema(cargar_json(ruta))
        svg = renderizar(tarjeta, tema, idioma, base=base)
        destino = salida / f"estilo-{letra.lower()}.svg"
        destino.write_text(svg, encoding="utf-8", newline="\n")
        rutas.append(destino)
        bloques.append(f'<section><h2>Estilo {letra}: {html.escape(tema["nombre"])}</h2><p>Composición: {tema["composicion"]}. Colores de fondo y título: '
                       f'{tema["colores"]["fondo"]} y {tema["colores"]["titulo"]}.</p>{svg}</section>')
    pagina = salida / "comparar.html"
    pagina.write_text('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                      "<title>Estilos para la tarjeta</title><style>body{font-family:system-ui,sans-serif;margin:24px;background:#f4f4f4;color:#222}"
                      "section{margin:0 0 32px}svg{max-width:100%;height:auto;display:block}h2{margin:0 0 4px;font-size:1.1rem}p{margin:0 0 8px;color:#555}</style>"
                      "</head><body><h1>Elegí un estilo</h1>" + "".join(bloques) + "</body></html>\n", encoding="utf-8", newline="\n")
    return pagina, rutas


def bloque_readme(nombre, pie, titulo=None, ancho=ANCHO, ruta="docs/img"):
    alt = html.escape(titulo or nombre, quote=True)
    return f'<p align="center"><img src="{ruta}/{nombre}.svg" alt="{alt}" width="{ancho}"><br><sub>{html.escape(pie)}</sub></p>'


def verificar(raiz, fuente, salida, idioma="es"):
    """(líneas, ok): ¿están al día los SVG respecto de los JSON y el estilo, y el README muestra cada pie?"""
    raiz = Path(raiz)
    fuente, salida = raiz / fuente, raiz / salida
    tarjetas = tarjetas_de(fuente) if fuente.is_dir() else []
    if not tarjetas:
        return ["Tarjetas: el proyecto no usa tarjetas SVG (se omite)."], True
    problemas = []
    ruta_estilo = fuente / "estilo.json"
    if not ruta_estilo.exists():
        return ["Tarjetas: hay tarjetas pero falta docs/tarjetas/estilo.json."], False
    tema = cargar_json(ruta_estilo)
    readme = (raiz / "README.md").read_text(encoding="utf-8", errors="replace") if (raiz / "README.md").exists() else ""
    for p in tarjetas:
        try:
            tarjeta = cargar_json(p)
            esperado = renderizar(tarjeta, tema, idioma, base=raiz)
        except TarjetaError as e:
            problemas.append(f"{p.name}: {e}")
            continue
        svg = salida / f"{p.stem}.svg"
        if not svg.exists():
            problemas.append(f"{p.stem}.svg no existe: regenerar con `readme_tarjetas.py generar`")
        elif svg.read_text(encoding="utf-8").replace("\r\n", "\n") != esperado:
            problemas.append(f"{p.stem}.svg está desactualizado respecto de {p.name} o del estilo: regenerar")
        if f"{p.stem}.svg" in readme and tarjeta["pie"] not in readme and html.escape(tarjeta["pie"]) not in readme:
            problemas.append(f"el README muestra {p.stem}.svg sin su pie de foto debajo")
        elif f"{p.stem}.svg" not in readme:
            problemas.append(f"el README no muestra {p.stem}.svg")
    huerfanas = [s.name for s in salida.glob("*.svg") if s.stem not in {p.stem for p in tarjetas}] if salida.is_dir() else []
    if huerfanas:
        problemas.append("SVG sin tarjeta de origen (no se hacen a mano): " + ", ".join(huerfanas))
    if problemas:
        return [f"Tarjetas: {len(problemas)} problemas:"] + [f"  {x}" for x in problemas], False
    return [f"Tarjetas: {len(tarjetas)} al día, con pie de foto y estilo «{tema.get('nombre', '?')}»."], True


def main():
    for f in (sys.stdout, sys.stderr):
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    for nombre in ("generar", "verificar", "bloque"):
        s = sub.add_parser(nombre)
        s.add_argument("--raiz", default=".")
        s.add_argument("--fuente", default="docs/tarjetas")
        s.add_argument("--salida", default="docs/img")
        s.add_argument("--idioma", choices=("es", "en"), default="es")
        if nombre == "generar":
            s.add_argument("--estilo")
        if nombre == "bloque":
            s.add_argument("nombre")
            s.add_argument("--ancho", type=int, default=ANCHO)
    c = sub.add_parser("comparar")
    c.add_argument("--tarjeta", required=True)
    c.add_argument("--estilos", nargs="+", required=True)
    c.add_argument("--salida", default=".temporal/estilos")
    c.add_argument("--idioma", choices=("es", "en"), default="es")
    a = ap.parse_args()
    try:
        if a.orden == "generar":
            for p in generar(a.raiz, a.fuente, a.salida, a.estilo, a.idioma):
                print(p)
            return 0
        if a.orden == "comparar":
            if not 2 <= len(a.estilos) <= 3:
                sys.exit("Se comparan dos o tres estilos.")
            pagina, rutas = comparar(a.tarjeta, a.estilos, a.salida, a.idioma)
            print(pagina)
            return 0
        if a.orden == "bloque":
            t = cargar_json(Path(a.raiz) / a.fuente / f"{a.nombre}.json")
            print(bloque_readme(a.nombre, t["pie"], t.get("titulo"), a.ancho))
            return 0
        lineas, ok = verificar(a.raiz, a.fuente, a.salida, a.idioma)
        print("\n".join(lineas))
        return 0 if ok else 1
    except TarjetaError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
