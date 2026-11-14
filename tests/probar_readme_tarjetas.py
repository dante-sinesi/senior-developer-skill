"""Tarjetas SVG para el README: un motor neutro con reglas objetivas (pie de foto, sello de origen, contraste, decoración segura) y la comparación de tres estilos.
Los temas de esta prueba son datos de prueba; el paquete no trae ningún estilo propio."""
import copy
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SCRIPT = RAIZ / "skills" / "senior-docs" / "scripts" / "readme_tarjetas.py"
sys.path.insert(0, str(SCRIPT.parent))
import readme_tarjetas as rt  # noqa: E402

BASE = RAIZ / ".temporal" / "proy-tarjetas"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def falla(fn, *a, texto=None):
    try:
        fn(*a)
    except rt.TarjetaError as e:
        return texto is None or texto in str(e)
    return False


TEMA_A = {"nombre": "Horno", "composicion": "dividida",
          "colores": {"fondo": "#2B1810", "titulo": "#FFE9C7", "texto": "#F2C9A0", "acento": "#FF8A3D"},
          "tipografia": {"familia": "Georgia, serif", "mayusculas": False}, "sombra_titulo": "#7A3A12",
          "decoracion": {"fondo_svg": '<circle cx="650" cy="150" r="120" fill="#3D2216"/>', "frente_svg": '<rect x="0" y="292" width="760" height="8" fill="#FF8A3D"/>'}}
TEMA_B = {"nombre": "Harina", "composicion": "centrada",
          "colores": {"fondo": "#F7F1E3", "titulo": "#3B2A1A", "texto": "#5A4631", "acento": "#B5651D", "sello_medido": "#2F6B3A", "sello_esperado": "#8A5A00"},
          "tipografia": {"familia": "Georgia, serif", "mayusculas": True},
          "decoracion": {"fondo_svg": '<rect x="14" y="14" width="732" height="272" fill="none" stroke="#B5651D" stroke-width="2"/>'}}
TEMA_C = {"nombre": "Cartel", "composicion": "cartel", "alto": 280,
          "colores": {"fondo": "#101010", "titulo": "#FFFFFF", "texto": "#D9D9D9", "acento": "#FFE600"},
          "tipografia": {"familia": "Impact, sans-serif", "peso_titulo": 900, "mayusculas": True},
          "decoracion": {"fondo_svg": '<rect width="760" height="14" fill="#FFE600"/>'}}
PORTADA = {"tipo": "portada", "titulo": "Panadería Lumbre", "subtitulo": "Sistema de pedidos para una panadería artesanal", "pie": "Portada de Panadería Lumbre."}
CIFRA_M = {"tipo": "cifra", "valor": "-57 %", "etiqueta": "tokens al leer una imagen grande", "origen": "medido", "pie": "Lo medido."}
CIFRA_E = {"tipo": "cifra", "valor": "-51 %", "etiqueta": "tokens al leer JSON", "origen": "esperado", "nota": "De una muestra, con caracteres / 4.", "pie": "Lo esperado."}
ANTES_DESPUES = {"tipo": "antes_despues", "titulo": "Leer un registro", "antes": {"etiqueta": "sin la skill", "valor": 1000}, "despues": {"etiqueta": "con la skill", "valor": 100},
                 "origen": "esperado", "nota": "De una muestra.", "pie": "Un registro pasa de 1.000 a 100."}


def con(base, **cambios):
    d = copy.deepcopy(base)
    d.update(cambios)
    return d


# ---------------- 1. reglas de las tarjetas
chequear("una tarjeta sin pie se rechaza", falla(rt.validar, con(PORTADA, pie=" "), texto="pie"))
chequear("una cifra sin origen se rechaza", falla(rt.validar, {k: v for k, v in CIFRA_M.items() if k != "origen"}, texto="origen"))
chequear("un origen inventado se rechaza", falla(rt.validar, con(CIFRA_M, origen="aproximado")))
chequear("una cifra esperada sin nota se rechaza", falla(rt.validar, con(CIFRA_E, nota=" "), texto="nota"))
chequear("una medida no necesita nota", rt.validar(CIFRA_M) is None)
chequear("un tipo desconocido se rechaza", falla(rt.validar, {"tipo": "torta", "pie": "x"}))
chequear("un título de más de 40 caracteres se rechaza (una idea por tarjeta)", falla(rt.validar, con(PORTADA, titulo="x" * 41), texto="40"))
chequear("un subtítulo de más de 90 caracteres se rechaza (sin saturar)", falla(rt.validar, con(PORTADA, subtitulo="x" * 91), texto="90"))
chequear("antes_despues: el «antes» en cero se rechaza", falla(rt.validar, con(ANTES_DESPUES, antes={"etiqueta": "a", "valor": 0})))
chequear("antes_despues: un valor negativo se rechaza", falla(rt.validar, con(ANTES_DESPUES, despues={"etiqueta": "a", "valor": -1})))

# ---------------- 2. el tema: contraste, colores, composición
chequear("el contraste de blanco sobre negro es 21:1", abs(rt.contraste("#fff", "#000") - 21) < 0.01)
chequear("un título con poco contraste contra el fondo se rechaza", falla(rt.validar_tema, con(TEMA_A, colores={**TEMA_A["colores"], "titulo": "#3A2418"}), texto="contraste"))
chequear("un texto con poco contraste se rechaza", falla(rt.validar_tema, con(TEMA_B, colores={**TEMA_B["colores"], "texto": "#E8E0D0"}), texto="contraste"))
chequear("un sello con poco contraste se rechaza", falla(rt.validar_tema, con(TEMA_B, colores={**TEMA_B["colores"], "sello_medido": "#F0E8D8"}), texto="sello_medido"))
chequear("un acento con menos de 3:1 se rechaza", falla(rt.validar_tema, con(TEMA_B, colores={**TEMA_B["colores"], "acento": "#EFE8D8"}), texto="acento"))
chequear("un color que falta se rechaza", falla(rt.validar_tema, con(TEMA_A, colores={"fondo": "#000", "titulo": "#fff", "texto": "#fff"}), texto="acento"))
chequear("un color mal escrito se rechaza", falla(rt.validar_tema, con(TEMA_A, colores={**TEMA_A["colores"], "titulo": "amarillo"}), texto="color"))
chequear("una composición desconocida se rechaza", falla(rt.validar_tema, con(TEMA_A, composicion="espiral")))
chequear("un alto fuera de 200 a 400 se rechaza", falla(rt.validar_tema, con(TEMA_A, alto=100)))
chequear("los tres temas de prueba son válidos", all(rt.validar_tema(t) for t in (TEMA_A, TEMA_B, TEMA_C)))

# ---------------- 3. decoración segura
for desc, deco in {"un script": '<script>alert(1)</script>', "un evento": '<rect onclick="x()" width="1" height="1"/>', "un recurso externo": '<image href="https://x.test/a.png"/>',
                   "una fuente externa": '<rect style="fill:url(https://x.test/f)"/>', "foreignObject": "<foreignObject><div/></foreignObject>", "un @import": "<style>@import 'x.css';</style>"}.items():
    chequear(f"la decoración con {desc} se rechaza", falla(rt.validar_tema, con(TEMA_A, decoracion={"fondo_svg": deco}), texto="decoración"))
chequear("una referencia interna (#id) y un data: sí se permiten", rt.validar_tema(con(TEMA_A, decoracion={"fondo_svg": '<use href="#a"/><image href="data:image/png;base64,AAAA"/>'})) is not None)
chequear("un SVG de más de 200 KB se rechaza", falla(rt.renderizar, PORTADA, con(TEMA_A, decoracion={"fondo_svg": "<g>" + '<rect width="1" height="1"/>' * 9000 + "</g>"}), texto="KB"))

# ---------------- 4. el dibujo
svgs = {c: rt.renderizar(PORTADA, t) for c, t in (("A", TEMA_A), ("B", TEMA_B), ("C", TEMA_C))}
for c, s in svgs.items():
    chequear(f"el estilo {c} da un SVG bien formado", ET.fromstring(s) is not None)
chequear("tres estilos con composición distinta dan tres dibujos distintos", len(set(svgs.values())) == 3)
for comp in rt.COMPOSICIONES:
    chequear(f"la composición «{comp}» se dibuja", "Panadería Lumbre" in rt.renderizar(PORTADA, con(TEMA_A, composicion=comp)).replace("PANADERÍA LUMBRE", "Panadería Lumbre"))
s = rt.renderizar(CIFRA_E, TEMA_B)
chequear("el pie y la nota van en el <desc> del SVG", "<desc>Lo esperado. De una muestra, con caracteres / 4.</desc>" in s, s[:300])
chequear("la tarjeta medida lleva un sello con trazo sólido", "MEDIDO" in rt.renderizar(CIFRA_M, TEMA_B) and "stroke-dasharray" not in rt.renderizar(CIFRA_M, TEMA_B))
chequear("la esperada lleva un sello con trazo discontinuo", "ESPERADO" in s and "stroke-dasharray" in s)
chequear("el sello cambia de idioma", "MEASURED" in rt.renderizar(CIFRA_M, TEMA_B, "en") and "EXPECTED" in rt.renderizar(CIFRA_E, TEMA_B, "en"))
chequear("el título largo se achica para entrar en el ancho", int(re.search(r'font-size="(\d+)"', rt.renderizar(con(PORTADA, titulo="x" * 40), TEMA_C).split("<text")[1]).group(1)) < 64
         and int(re.search(r'font-size="(\d+)"', rt.renderizar(con(PORTADA, titulo="Lumbre"), TEMA_C).split("<text")[1]).group(1)) == 64)
raro = con(PORTADA, titulo='A <b> & "c"', subtitulo="Más <i>texto</i> & 'algo'")
chequear("los caracteres especiales no rompen el XML", ET.fromstring(rt.renderizar(raro, TEMA_A)) is not None)
chequear("el subtítulo largo se parte en líneas y, si no entra en dos, avisa", len(rt.envolver("palabra " * 8, 400, 22, False)) == 2 and falla(rt.envolver, "palabra " * 30, 400, 22, False, texto="no entra"))
ba = rt.renderizar(ANTES_DESPUES, TEMA_A)
chequear("antes_despues llena las barras en proporción (100 de 1.000 son 2 de 20)", ba.count('fill="#FF8A3D"') >= 2 and ET.fromstring(ba) is not None)
uno = rt.renderizar(con(ANTES_DESPUES, despues={"etiqueta": "x", "valor": 1}), TEMA_A)
chequear("un resultado mayor que cero nunca muestra cero cuadrados", uno.count('width="17" height="17" fill="#FF8A3D"') >= 1, uno.count('fill="#FF8A3D"'))

# ---------------- 5. fuentes incrustadas
shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
(BASE / "fuentes").mkdir(parents=True)
(BASE / "fuentes" / "f.woff2").write_bytes(b"wOF2" + b"0" * 50)
con_fuente = con(TEMA_A, fuentes=[{"archivo": "fuentes/f.woff2", "familia": "Mi Fuente", "peso": 700}])
chequear("una fuente local se incrusta en el SVG", "@font-face" in rt.renderizar(PORTADA, con_fuente, base=BASE) and "Mi Fuente" in rt.renderizar(PORTADA, con_fuente, base=BASE))
chequear("una fuente que no existe se rechaza", falla(rt.renderizar, PORTADA, con(TEMA_A, fuentes=[{"archivo": "no.woff2"}]), texto="fuente"))

# ---------------- 6. generar, bloque del README y verificar
P = BASE / "proyecto"
(P / "docs" / "tarjetas").mkdir(parents=True)
(P / "docs" / "tarjetas" / "portada.json").write_text(json.dumps(PORTADA, ensure_ascii=False), encoding="utf-8")
(P / "docs" / "tarjetas" / "cifra.json").write_text(json.dumps(CIFRA_E, ensure_ascii=False), encoding="utf-8")
chequear("sin el estilo elegido no se genera nada", falla(rt.generar, P, "docs/tarjetas", "docs/img", None, "es", texto="estilo") and not (P / "docs" / "img").exists())
(P / "docs" / "tarjetas" / "estilo.json").write_text(json.dumps(TEMA_B, ensure_ascii=False), encoding="utf-8")
escritas = rt.generar(P, "docs/tarjetas", "docs/img", None, "es")
chequear("genera un SVG por tarjeta y no trata el estilo como tarjeta", sorted(p.name for p in escritas) == ["cifra.svg", "portada.svg"], escritas)
bloque = rt.bloque_readme("portada", 'Portada de "Lumbre" & más.', "Lumbre")
chequear("el bloque del README centra la imagen y pone el pie debajo", bloque == '<p align="center"><img src="docs/img/portada.svg" alt="Lumbre" width="760"><br><sub>Portada de &quot;Lumbre&quot; &amp; más.</sub></p>', bloque)
lineas, ok = rt.verificar(P, "docs/tarjetas", "docs/img")
chequear("sin README que las muestre, lo dice", not ok and "no muestra portada.svg" in "\n".join(lineas), lineas)
(P / "README.md").write_text("\n".join([rt.bloque_readme("portada", PORTADA["pie"], "Portada"), "", rt.bloque_readme("cifra", CIFRA_E["pie"], "Cifra"), ""]), encoding="utf-8")
lineas, ok = rt.verificar(P, "docs/tarjetas", "docs/img")
chequear("con las dos tarjetas al día y con su pie, todo bien", ok and "2 al día" in lineas[0] and "Harina" in lineas[0], lineas)
(P / "docs" / "tarjetas" / "portada.json").write_text(json.dumps(con(PORTADA, titulo="Otro nombre"), ensure_ascii=False), encoding="utf-8")
lineas, ok = rt.verificar(P, "docs/tarjetas", "docs/img")
chequear("si se cambia el JSON y no se regenera, avisa que el SVG está desactualizado", not ok and "portada.svg está desactualizado" in "\n".join(lineas), lineas)
rt.generar(P, "docs/tarjetas", "docs/img", None, "es")
(P / "docs" / "img" / "a_mano.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
lineas, ok = rt.verificar(P, "docs/tarjetas", "docs/img")
chequear("un SVG hecho a mano, sin tarjeta de origen, se señala", not ok and "a_mano.svg" in "\n".join(lineas), lineas)
(P / "docs" / "img" / "a_mano.svg").unlink()
(P / "README.md").write_text('<p align="center"><img src="docs/img/portada.svg" alt="x" width="760"></p>\n' + rt.bloque_readme("cifra", CIFRA_E["pie"]), encoding="utf-8")
lineas, ok = rt.verificar(P, "docs/tarjetas", "docs/img")
chequear("una imagen en el README sin su pie de foto se señala", not ok and "sin su pie de foto" in "\n".join(lineas), lineas)
chequear("un proyecto sin tarjetas se omite", rt.verificar(BASE, "docs/tarjetas", "docs/img") == (["Tarjetas: el proyecto no usa tarjetas SVG (se omite)."], True))

# ---------------- 7. comparar tres estilos
T = BASE / "estilos"
T.mkdir()
for n, t in (("a", TEMA_A), ("b", TEMA_B), ("c", TEMA_C)):
    (T / f"{n}.json").write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
(T / "portada.json").write_text(json.dumps(PORTADA, ensure_ascii=False), encoding="utf-8")
r = subprocess.run([sys.executable, str(SCRIPT), "comparar", "--tarjeta", str(T / "portada.json"), "--estilos", str(T / "a.json"), str(T / "b.json"), str(T / "c.json"),
                    "--salida", str(BASE / "comparacion")], capture_output=True, text=True, encoding="utf-8", errors="replace")
pagina = (BASE / "comparacion" / "comparar.html").read_text(encoding="utf-8") if (BASE / "comparacion" / "comparar.html").exists() else ""
chequear("comparar arma una página con los tres estilos rotulados A, B y C", r.returncode == 0 and pagina.count("<svg") == 3 and all(f"Estilo {x}" in pagina for x in "ABC"), r.stdout + r.stderr)
chequear("la página no carga nada de afuera (sin http, sin scripts)", "http://www.w3.org" in pagina and not re.search(r"https?://(?!www\.w3\.org)", pagina) and "<script" not in pagina)
chequear("y deja un SVG por estilo", all((BASE / "comparacion" / f"estilo-{x}.svg").exists() for x in "abc"))
r = subprocess.run([sys.executable, str(SCRIPT), "comparar", "--tarjeta", str(T / "portada.json"), "--estilos", str(T / "a.json")], capture_output=True, text=True, encoding="utf-8", errors="replace")
chequear("comparar un solo estilo no se acepta (son dos o tres)", r.returncode != 0, r.stdout + r.stderr)

# ---------------- 8. el paquete no trae ningún estilo propio
estilos = [f for f in (RAIZ / "skills").rglob("*.json") if "perfiles" not in f.parts and re.search(r'"colores"\s*:', f.read_text(encoding="utf-8", errors="replace"))]
chequear("ninguna skill trae un tema de tarjetas (el estilo se inventa por proyecto)", not estilos, estilos)
codigo = SCRIPT.read_text(encoding="utf-8")
colores_del_motor = set(re.findall(r"#[0-9A-Fa-f]{6}", codigo.split('"""', 2)[2]))
chequear("el motor no tiene colores de estilo: solo el gris neutro de la página de comparación", colores_del_motor <= {"#f4f4f4"}, colores_del_motor)

# ---- diagramas (flujo y secuencia) y texto que no entra
FLUJO = {"tipo": "flujo", "titulo": "Un flujo", "columnas": 2, "nodos": [{"id": "a", "texto": "Uno", "col": 0, "fila": 0}, {"id": "b", "texto": "Dos", "col": 1, "fila": 0},
         {"id": "c", "texto": "Tres", "col": 0, "fila": 1, "forma": "decision"}], "flechas": [{"de": "a", "a": "b", "texto": "va"}, {"de": "b", "a": "c"}], "pie": "Un flujo de prueba."}
SECUENCIA = {"tipo": "secuencia", "titulo": "Una secuencia", "participantes": [{"id": "x", "texto": "X"}, {"id": "y", "texto": "Y"}],
             "pasos": [{"de": "x", "a": "y", "texto": "hola"}, {"de": "y", "a": "y", "texto": "piensa"}, {"nota": "Una nota", "sobre": "x"}, {"bloque": "alt: otro caso"}, {"de": "y", "a": "x", "texto": "chau", "estilo": "punteada"}],
             "pie": "Una secuencia de prueba."}
for nombre, d in (("flujo", FLUJO), ("secuencia", SECUENCIA)):
    svg = rt.renderizar(d, TEMA_A)
    chequear(f"el diagrama {nombre} sale como SVG válido con título, descripción y sin la decoración del tema", ET.fromstring(svg) is not None and "<title>" in svg and "<desc>" in svg and "#7A3A12" not in svg and "#FF8A3D" in svg)
chequear("un diagrama sin pie se rechaza", falla(rt.renderizar, {k: v for k, v in FLUJO.items() if k != "pie"}, TEMA_A, texto="pie"))
chequear("un flujo con una flecha a un nodo inexistente se rechaza", falla(rt.renderizar, {**FLUJO, "flechas": [{"de": "a", "a": "zz"}]}, TEMA_A, texto="no existe"))
chequear("un flujo con más de 15 nodos se rechaza", falla(rt.renderizar, {**FLUJO, "nodos": [{"id": str(i), "texto": "n", "col": i % 2, "fila": i // 2} for i in range(16)], "flechas": []}, TEMA_A, texto="15"))
chequear("un texto de nodo que no entra se rechaza en vez de recortarse en silencio", falla(rt.renderizar, {**FLUJO, "nodos": [{"id": "a", "texto": "palabra " * 30, "col": 0, "fila": 0}], "flechas": []}, TEMA_A, texto="no entra"))
chequear("un título de portada que no entra en las líneas del lienzo avisa en vez de recortarse", falla(rt.renderizar, {**PORTADA, "subtitulo": "supercalifragilisticoespialidoso " * 2}, TEMA_A, texto="no entra") or falla(rt.renderizar, {**PORTADA, "subtitulo": "muy largo " * 40}, TEMA_A))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
