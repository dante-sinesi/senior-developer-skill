"""Visor de propuestas (senior-diseno): una página para ver todas las propuestas en desktop, mobile o ambas."""
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "skills" / "senior-diseno" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import ver_propuestas as vp  # noqa: E402

P = RAIZ / ".temporal" / "proy-visor"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def manifiesto_de(ruta):
    m = re.search(r'<script type="application/json" id="manifiesto">(.*?)</script>', Path(ruta).read_text(encoding="utf-8"), re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def falla(fn, *a, texto=None, **k):
    try:
        fn(*a, **k)
    except vp.VisorError as e:
        return texto is None or texto in str(e)
    return False


if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)
for n in ("inicio__a.html", "inicio__b.html", "direccion-c.html", "ajustes__a__desktop.svg", "ajustes__a__mobile.svg", "ajustes__b__desktop.svg", "_borrador.html", "comparar.html", "ver-viejo.html"):
    (P / n).write_text("<p>x</p>", encoding="utf-8")

# ---- agrupar por nombre
m = vp.manifiesto_de_carpeta(P, "Demo", ["desktop", "mobile"])
pantallas = {p["id"]: p for p in m["pantallas"]}
chequear("agrupa por pantalla: inicio, ajustes y general", set(pantallas) == {"inicio", "ajustes", "general"}, list(pantallas))
chequear("una propuesta con un archivo por modo los junta", pantallas["ajustes"]["propuestas"][0] == {"id": "a", "titulo": "A", "desktop": "ajustes__a__desktop.svg", "mobile": "ajustes__a__mobile.svg"}, pantallas["ajustes"]["propuestas"][0])
chequear("un archivo sin modo sirve para los dos (HTML responsivo)", pantallas["inicio"]["propuestas"][0].get("archivo") == "inicio__a.html")
chequear("se ignoran los borradores, comparar.html y los visores", all(n not in json.dumps(m) for n in ("_borrador", "comparar.html", "ver-viejo")), m)
(P / "vacia").mkdir()
chequear("una carpeta sin propuestas se rechaza con un mensaje", falla(vp.manifiesto_de_carpeta, P / "vacia", "x", ["desktop"], texto="No hay propuestas"))

# ---- pendientes y modos de la app
ruta, pend = vp.crear(P, "Demo")
chequear("con los dos modos, la propuesta a la que le falta uno queda pendiente", pend == ["Ajustes / B: falta mobile"], pend)
ruta2, pend2 = vp.crear(P, "Demo", ["desktop"], salida="ver-desktop.html")
chequear("una app solo desktop no marca nada como pendiente", pend2 == [], pend2)
chequear("el visor declara los modos de la app", manifiesto_de(ruta2)["modos"] == ["desktop"] and manifiesto_de(ruta)["modos"] == ["desktop", "mobile"])
chequear("un modo desconocido se rechaza", falla(vp.leer_modos, "tablet", texto="--modos"))

# ---- la página
html = ruta.read_text(encoding="utf-8")
chequear("las imágenes se ven sin el margen blanco del marco y cada pestaña puede traer su tamaño", ".marco.imagen { display: grid; place-items: center; border: 0; background: transparent; }" in html and "function VPm(modo)" in html)
chequear("la página es autocontenida: sin recursos externos", not re.search(r'(src|href)="https?://', html) and "<link" not in html)
chequear("lo de la herramienta va marcado data-herramienta (las reglas de diseño lo ignoran)", html.count("data-herramienta") >= 4)
chequear("trae vista desktop, mobile y ambas, una o lado a lado, y avisa los pendientes", all(x in html for x in ('data-modo="desktop"', 'data-modo="mobile"', 'data-modo="ambas"', 'data-diseno="lado"', "Pendiente: falta la propuesta")))
chequear("las alternativas van en un panel lateral colapsable con el ícono de las tres líneas", all(x in html for x in ('id="lateral"', 'id="menu"', 'M4 6h16M4 12h16M4 18h16', "aria-expanded", "cerrado")))
chequear("izquierda y derecha cambian de pestaña y arriba y abajo de alternativa", "k === 'arrowright' || k === 'arrowleft'" in html and "k === 'arrowdown' || k === 'arrowup'" in html and "Teclas:" not in html)
chequear("hay un botón de pantalla completa que usa la API del navegador", 'id="pantalla-completa"' in html and "requestFullscreen" in html and "exitFullscreen" in html)
chequear("las pestañas van en el panel lateral, debajo de las alternativas", html.index('id="lista"') < html.index('id="pantallas"') and 'nav class="pestanas"' not in html)
chequear("la página no tiene barras de desplazamiento y el panel sí las tiene cuando hace falta", "overflow: hidden; background: var(--fondo)" in html and "overflow-y: auto" in html)
chequear("la versión mobile nunca es más alta que la desktop: se angosta manteniendo la proporción", "Math.min(h, VPm('desktop')[1])" in html and "dispH / altoNecesario" in html)
chequear("una app con un solo modo no muestra los botones Desktop, Mobile ni Ambas ni rotula las vistas por modo", "$('#grupo-vista').hidden = MODOS.length < 2" in html and "MODOS.length > 1 ? (modo" in html)
chequear("un título con etiquetas no rompe la página", "</script><b>" not in vp.pagina({"titulo": "</script><b>", "modos": ["mobile"], "pantallas": []}))
scripts = re.findall(r"<script data-herramienta>(.*?)</script>", html, re.S)
if shutil.which("node") and scripts:
    js = P / "_visor.js"
    js.write_text(scripts[0].replace("document.getElementById('manifiesto').textContent", "'{}'"), encoding="utf-8")
    r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    chequear("el JavaScript del visor es válido", r.returncode == 0, r.stderr)

# ---- manifiesto explícito
(P / "m.json").write_text(json.dumps({"titulo": "Explícito", "modos": ["mobile"], "pantallas": [{"id": "x", "titulo": "X", "propuestas": [{"id": "a", "titulo": "A", "archivo": "no-existe.html"}]}]}), encoding="utf-8")
chequear("un archivo del manifiesto que no existe es un error", falla(vp.crear, P, None, ["mobile"], str(P / "m.json"), texto="no existe no-existe.html"))
(P / "m.json").write_text(json.dumps({"titulo": "Explícito", "modos": ["mobile"], "pantallas": [{"id": "x", "titulo": "X", "propuestas": [{"id": "a", "titulo": "A", "archivo": "inicio__a.html"}, {"id": "a", "titulo": "A2", "archivo": "inicio__b.html"}]}]}), encoding="utf-8")
chequear("una propuesta repetida se rechaza", falla(vp.crear, P, None, ["mobile"], str(P / "m.json"), texto="repetida"))

# ---- por línea de comandos
r = subprocess.run([sys.executable, str(SCRIPTS / "ver_propuestas.py"), "crear", str(P), "--modos", "mobile", "--salida", "ver-cli.html"], capture_output=True, text=True, encoding="utf-8")
chequear("la línea de comandos crea el visor y dice cómo abrirlo", r.returncode == 0 and (P / "ver-cli.html").exists() and "abrir_en_navegador.py" in r.stdout, r.stdout + r.stderr)
r = subprocess.run([sys.executable, str(SCRIPTS / "ver_propuestas.py"), "estado", str(P)], capture_output=True, text=True, encoding="utf-8")
chequear("estado lista las pantallas y los pendientes", "Inicio: A, B" in r.stdout and "Pendientes:" in r.stdout, r.stdout)

# ---- la ronda de diseño ya trae su visor
Q = RAIZ / ".temporal" / "proy-visor-ronda"
if Q.exists():
    shutil.rmtree(Q, onerror=_forzar)
r = subprocess.run([sys.executable, str(SCRIPTS / "crear_bosquejos.py"), "--nombre", "Prueba", "--raiz", str(Q), "--fecha", "2026-01-01", "--modos", "mobile"], capture_output=True, text=True, encoding="utf-8")
ronda = Q / "docs" / "diseno" / "rondas" / "2026-01-01-prueba"
chequear("la ronda nueva incluye ver.html", r.returncode == 0 and (ronda / "ver.html").exists() and "ver.html" in r.stdout, r.stdout + r.stderr)
mr = manifiesto_de(ronda / "ver.html")
chequear("el visor de la ronda trae las tres direcciones y los modos pedidos", mr["modos"] == ["mobile"] and [p["id"] for p in mr["pantallas"][0]["propuestas"]] == ["direccion-a", "direccion-b", "direccion-c"], mr)
(ronda / "ver.html").write_text("mio", encoding="utf-8")
subprocess.run([sys.executable, str(SCRIPTS / "crear_bosquejos.py"), "--nombre", "Prueba", "--raiz", str(Q), "--fecha", "2026-01-01"], capture_output=True, text=True, encoding="utf-8")
chequear("volver a crear la ronda no pisa un ver.html existente", (ronda / "ver.html").read_text(encoding="utf-8") == "mio")
chequear("al cambiar de pestaña se conserva la alternativa (por nombre o por posición)", "function irAPantalla(i)" in html and "estado.propuesta = 0" not in html)
# regenerar conserva título y modos
Rg = RAIZ / ".temporal" / "proy-visor-regenerar"
if Rg.exists():
    shutil.rmtree(Rg, onerror=_forzar)
Rg.mkdir(parents=True)
(Rg / "direccion-a.html").write_text("<p>a</p>", encoding="utf-8")
vp.crear(Rg, "Mi app", ["mobile"])
(Rg / "direccion-a-v2.html").write_text("<p>a2</p>", encoding="utf-8")
vp.regenerar(Rg)
mg = manifiesto_de(Rg / "ver.html")
chequear("regenerar suma los archivos nuevos y conserva el título y los modos", mg["titulo"] == "Mi app" and mg["modos"] == ["mobile"] and len(mg["pantallas"][0]["propuestas"]) == 2, mg)
r = subprocess.run([sys.executable, str(SCRIPTS / "crear_bosquejos.py"), "--evolucionar", str(ronda / "direccion-b.html")], capture_output=True, text=True, encoding="utf-8")
ids = [p["id"] for p in manifiesto_de(ronda / "ver.html")["pantallas"][0]["propuestas"]] if (ronda / "ver.html").read_text(encoding="utf-8").startswith("<!doctype") else []
chequear("--evolucionar deja el visor al día con la versión nueva", r.returncode == 0 and "direccion-b-v2" in ids and "ya incluye la versión nueva" in r.stdout, r.stdout + r.stderr + str(ids))
Ts = RAIZ / ".temporal" / "proy-visor-estilo"
if Ts.exists():
    shutil.rmtree(Ts, onerror=_forzar)
r = subprocess.run([sys.executable, str(SCRIPTS / "tarjeta_estilo.py"), "nueva", "--nombre", "Prueba", "--raiz", str(Ts), "--fecha", "2026-01-02"], capture_output=True, text=True, encoding="utf-8")
chequear("las alternativas de estilo también traen su visor", r.returncode == 0 and (Ts / "docs/diseno/estilo/2026-01-02-prueba/ver.html").exists() and "ver.html" in r.stdout, r.stdout + r.stderr)
skill = (RAIZ / "skills" / "senior-diseno" / "SKILL.md").read_text(encoding="utf-8")
chequear("el diseñador muestra siempre el visor abierto en el navegador y nunca capturas", "siempre con el visor" in skill and "abrir_en_navegador.py" in skill and "nunca con capturas" in skill)
chequear("el SKILL.md de diseño explica el visor", "ver_propuestas.py" in (RAIZ / "skills" / "senior-diseno" / "SKILL.md").read_text(encoding="utf-8"))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
