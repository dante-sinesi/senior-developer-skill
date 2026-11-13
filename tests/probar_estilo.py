import io
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
sys.path.insert(0, str(RAIZ / "skills" / "senior" / "scripts"))
import tarjeta_estilo as te  # noqa: E402
import verificar  # noqa: E402
import escala  # noqa: E402

P = RAIZ / ".temporal" / "proy-estilo"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def cli(*a):
    p = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "tarjeta_estilo.py"), *a], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def leer(r):
    return (P / r).read_text(encoding="utf-8")


def escribir(r, t):
    f = P / r
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(t, encoding="utf-8", newline="\n")


TILE = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Estilo</title>
<style data-tokens>
:root { --c-fondo:#10131a; --c-texto:#f2efe6; --c-acento:#e8a33d; --f-titulo:"Fraunces",serif; --e-1:8px; }
</style>
<style data-componentes>
.boton{background:var(--c-acento);color:var(--c-fondo);font-family:var(--f-titulo);padding:var(--e-1)}
</style></head>
<body style="background:var(--c-fondo);color:var(--c-texto)"><main data-tarjeta>
<h1 style="font-family:var(--f-titulo)">Estilo del proyecto</h1>
<section data-componente="Botón">
 <button class="boton" data-variante="principal" data-estado="reposo">Guardar</button>
 <button class="boton" data-variante="principal" data-estado="hover">Guardar</button>
 <button class="boton" data-variante="secundario" data-estado="reposo">Cancelar</button>
 <button class="boton" data-variante="secundario" data-estado="hover">Cancelar</button>
</section>
<section data-componente="Campo"><div data-estado="reposo"><label>Nombre <input></label></div><div data-estado="error"><label>Correo <input></label></div></section>
</main></body></html>
"""

if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)

# 1. nueva: tres alternativas sin estilo impuesto
rc, s = cli("nueva", "--nombre", "Mi juego", "--raiz", str(P), "--fecha", "2026-01-02")
ronda = P / "docs" / "diseno" / "estilo" / "2026-01-02-mi-juego"
chequear("nueva crea estilo-a, b y c", rc == 0 and all((ronda / f"estilo-{l}.html").exists() for l in "abc"), s)
a = (ronda / "estilo-a.html").read_text(encoding="utf-8")
chequear("cada alternativa trae la barra de vistas y sus marcas", "marco-ui" in a or "data-herramienta" in a and "data-tokens" in a and "data-tarjeta" in a)
chequear("la plantilla no impone ningún estilo: el bloque de variables y el de componentes están vacíos de reglas",
         not re.search(r"--[\w-]+\s*:", re.search(r"<style data-tokens>(.*?)</style>", a, re.S).group(1).split("*/", 1)[1])
         and "{" not in re.search(r"<style data-componentes>(.*?)</style>", a, re.S).group(1))
chequear("el título trae la letra de la alternativa", "Estilo A" in a)
rc, s = cli("nueva", "--nombre", "Mi juego", "--raiz", str(P), "--fecha", "2026-01-02")
chequear("repetir no pisa nada", "0 archivos creados" in s, s)

# 2. revisar
rc, s = cli("revisar", str(ronda / "estilo-a.html"))
chequear("una alternativa vacía no está lista", rc == 1 and "no define variables" in s and "ninguna pieza firma" in s, s)
(ronda / "estilo-b.html").write_text(TILE, encoding="utf-8", newline="\n")
rc, s = cli("revisar", str(ronda / "estilo-b.html"))
chequear("una alternativa completa queda lista para mostrar", rc == 0 and "listo para mostrar" in s, s)
sin_estados = TILE.replace(' data-estado="reposo"', "").replace(' data-estado="hover"', "").replace(' data-estado="error"', "")
(ronda / "estilo-c.html").write_text(sin_estados, encoding="utf-8", newline="\n")
rc, s = cli("revisar", str(ronda / "estilo-c.html"))
chequear("una pieza sin estados se marca", rc == 1 and "no muestra ningún estado" in s, s)

# 3. sin tarjeta no dice nada
chequear("sin tarjeta, evaluar no dice nada", te.evaluar(P) == ([], True))

# 4. elegir
escribir("docs/diseno/sistema/tokens.css", (SCRIPTS.parent / "plantillas" / "tokens.css").read_text(encoding="utf-8"))
rc, s = cli("elegir", str(ronda / "estilo-b.html"), "--raiz", str(P))
chequear("elegir crea la tarjeta viva", rc == 0 and (P / "docs/diseno/estilo/tarjeta.html").exists(), s)
t = leer("docs/diseno/estilo/tarjeta.html")
chequear("la tarjeta enlaza tokens.css en lugar de copiar las variables", 'href="../sistema/tokens.css"' in t and "--c-acento:#e8a33d" not in t, t[:300])
chequear("las variables pasaron al sistema (reemplazando la plantilla sin tocar)", "--c-acento:#e8a33d" in leer("docs/diseno/sistema/tokens.css").replace(" ", ""))
inv = leer("docs/diseno/sistema/inventario-componentes.md")
chequear("las piezas firma pasaron al inventario con sus variantes y estados",
         "| Botón |" in inv and "principal" in inv and "secundario" in inv and "| Campo |" in inv and "error" in inv, inv)
dec = leer("docs/diseno/notas/decisiones.md")
chequear("la decisión quedó registrada como D-001 aunque la plantilla nombre D-001 en la prosa", "- D-001 — Estilo del proyecto: estilo-b.html" in dec and "D-002" not in dec, dec)
rc, s = cli("elegir", str(ronda / "estilo-b.html"), "--raiz", str(P))
chequear("no se pisa una tarjeta existente sin --pisar", rc != 0 and "--pisar" in s, s)
lineas, ok = te.evaluar(P)
chequear("recién elegida, la tarjeta está al día", ok and "al día" in lineas[0], lineas)
rc, s = cli("estado", "--raiz", str(P))
chequear("estado sale con 0", rc == 0, s)

# 5. componente nuevo: el hueco hace que la tarjeta cuente como vieja
rc, s = cli("componente", "Tarjeta de producto", "--variantes", "simple,destacada", "--estados", "reposo,hover", "--motivo", "ningún componente muestra un producto", "--raiz", str(P))
inv = leer("docs/diseno/sistema/inventario-componentes.md")
chequear("lo registra en el inventario y con su motivo", rc == 0 and "| Tarjeta de producto |" in inv and "ningún componente muestra un producto" in inv, s + inv)
t = leer("docs/diseno/estilo/tarjeta.html")
chequear("deja un hueco marcado en la tarjeta con cada variante y estado", t.count('data-componente="Tarjeta de producto"') == 1 and t.count("completar") >= 5, t[-700:])
lineas, ok = te.evaluar(P)
chequear("mientras haya huecos, la tarjeta está vieja", (not ok) and "hueco" in lineas[0], lineas)
rc, s = cli("estado", "--raiz", str(P))
chequear("estado sale con 1", rc == 1, s)
completa = re.sub(r"<!-- completar[^>]*-->", "", t)
completa = completa.replace('<div data-variante="simple" data-estado="reposo"></div>', '<div data-variante="simple" data-estado="reposo">x</div>')
(P / "docs/diseno/estilo/tarjeta.html").write_text(completa, encoding="utf-8", newline="\n")
lineas, ok = te.evaluar(P)
chequear("completado el hueco, vuelve a estar al día", ok, lineas)

# 6. un componente que ya existe no se duplica: se suman variantes y estados
rc, s = cli("componente", "botón", "--variantes", "peligro", "--estados", "presionado", "--raiz", str(P))
inv = leer("docs/diseno/sistema/inventario-componentes.md")
chequear("un componente existente suma variantes en vez de duplicarse", len([l for l in inv.splitlines() if l.startswith("| Botón |")]) == 1 and "peligro" in inv and "una variante no es un componente nuevo" in s, s + inv)
lineas, ok = te.evaluar(P)
chequear("variantes y estados nuevos que la tarjeta no muestra la dejan vieja", (not ok) and "peligro" in lineas[0] and "presionado" in lineas[0], lineas)

# 7. variables nuevas
escribir("docs/diseno/sistema/tokens.css", leer("docs/diseno/sistema/tokens.css") + "\n:root { --c-exito: #2a7; }\n")
lineas, ok = te.evaluar(P)
chequear("una variable de color nueva que la tarjeta no nombra la deja vieja", (not ok) and "--c-exito" in lineas[0], lineas)

# 8. un componente del inventario que falta en la tarjeta
t = leer("docs/diseno/estilo/tarjeta.html")
(P / "docs/diseno/estilo/tarjeta.html").write_text(t.replace('data-componente="Campo"', 'data-componente="Otro"'), encoding="utf-8", newline="\n")
lineas, ok = te.evaluar(P)
chequear("un componente del inventario que no está en la tarjeta se señala", (not ok) and "«Campo»" in lineas[0], lineas)

# 9. integración con verificar.py
class A:
    base = "HEAD"


lin, ok = verificar.chequeo_diseno(P, A())
chequear("verificar.py diseno incluye la tarjeta y falla si está vieja", (not ok) and any("Tarjeta de estilo" in l for l in lin), lin)

# 10. las estructuras usan el estilo cuando hay tarjeta
rc, s = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "crear_bosquejos.py"), "--nombre", "Pantallas", "--raiz", str(P), "--fecha", "2026-02-01"],
                       capture_output=True, text=True, encoding="utf-8").returncode, ""
d = leer("docs/diseno/rondas/2026-02-01-pantallas/direccion-a.html")
chequear("con tarjeta, las direcciones enlazan tokens.css y aclaran que solo cambian la estructura", "../../sistema/tokens.css" in d and "solo cambia la estructura" in d)
Q = RAIZ / ".temporal" / "proy-estilo-sin"
if Q.exists():
    shutil.rmtree(Q, onerror=_forzar)
Q.mkdir(parents=True)
subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "crear_bosquejos.py"), "--nombre", "Chico", "--raiz", str(Q), "--fecha", "2026-02-01"], capture_output=True)
d2 = (Q / "docs/diseno/rondas/2026-02-01-chico/direccion-a.html").read_text(encoding="utf-8")
chequear("sin tarjeta, las direcciones quedan como siempre", "tokens.css" not in d2)

# 11. fuera de la web
W = RAIZ / ".temporal" / "proy-estilo-godot"
if W.exists():
    shutil.rmtree(W, onerror=_forzar)
(W / "docs/diseno/sistema").mkdir(parents=True)
(W / "project.godot").write_text("config_version=5\n", encoding="utf-8")
(W / "docs/diseno/sistema/inventario-componentes.md").write_text(
    "# Inventario\n\n| Componente | Variantes | Estados | Dónde se usa | Notas |\n|---|---|---|---|---|\n| Botón | principal | reposo, hover | menú | |\n", encoding="utf-8")
rc, s = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "tarjeta_estilo.py"), "no-web", "--plataforma", "Godot", "--artefacto", "res://estilo/muestra.tscn",
                        "--recurso", "res://tema.tres", "--raiz", str(W)], capture_output=True, text=True, encoding="utf-8").returncode, ""
md = (W / "docs/diseno/estilo/tarjeta.md").read_text(encoding="utf-8")
chequear("no-web crea tarjeta.md con la muestra y el recurso", "res://estilo/muestra.tscn" in md and "res://tema.tres" in md and "| Botón |" in md, md)
lineas, ok = te.evaluar(W)
chequear("la fila nueva sin lugar de muestra deja la tarjeta vieja", (not ok) and "sin indicar dónde se muestran" in lineas[0], lineas)
(W / "docs/diseno/estilo/tarjeta.md").write_text(md.replace("(pendiente: indicar dónde se muestra)", "EstiloMuestra.tscn, nodo Botones"), encoding="utf-8", newline="\n")
lineas, ok = te.evaluar(W)
chequear("indicado dónde se muestra, queda al día", ok, lineas)
subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "tarjeta_estilo.py"), "componente", "Barra de vida", "--estados", "llena,vacía", "--raiz", str(W)], capture_output=True)
lineas, ok = te.evaluar(W)
chequear("un componente nuevo sin mostrar en la muestra deja la tarjeta vieja", (not ok) and "Barra de vida" in lineas[0], lineas)

# 12. escala: el nivel grande con interfaz exige la tarjeta
G = RAIZ / ".temporal" / "proy-estilo-escala"
if G.exists():
    shutil.rmtree(G, onerror=_forzar)
(G / "docs").mkdir(parents=True)
(G / "index.html").write_text("<html></html>", encoding="utf-8")
chequear("hay_interfaz detecta páginas y Godot", escala.hay_interfaz(G) and escala.hay_interfaz(W))
chequear("grande con interfaz y sin tarjeta: falta la tarjeta", any("tarjeta de estilo" in f for f in escala.faltantes(G, "grande")))
(G / "docs/diseno/estilo").mkdir(parents=True)
(G / "docs/diseno/estilo/tarjeta.html").write_text("<html></html>", encoding="utf-8")
chequear("con tarjeta ya no falta", not any("tarjeta de estilo" in f for f in escala.faltantes(G, "grande")))
chequear("el mediano la recomienda y el grande la exige", "tarjeta de estilo viva" in escala.texto_niveles("mediano") and "obligatoria" in escala.texto_niveles("grande"))

# 12b. hallazgos de la prueba con un estilo real
TEXTO_DEC = "\n".join(["Una línea por decisión (D-001).", "- D-004 — algo", "| D-005 | x |", ""])
chequear("siguiente_decision ignora los ID de la prosa", te.siguiente_decision(TEXTO_DEC) == "D-006")
chequear("siguiente_decision sin decisiones es D-001", te.siguiente_decision("texto sin decisiones (D-009 en prosa)") == "D-001")

pagina = "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>t</title></head><body>%s</body></html>"
botones = "".join(f"<button class='boton boton-principal'>Guardar pedido {i}</button>" for i in range(7))
(P / "sin-tarjeta.html").write_text(pagina % f"<main>{botones}</main>", encoding="utf-8")
(P / "con-tarjeta.html").write_text(pagina % f"<main data-tarjeta>{botones}</main>", encoding="utf-8")
p1 = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "revisar_diseno.py"), "saturacion", str(P / "sin-tarjeta.html")], capture_output=True, text=True, encoding="utf-8")
p2 = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPTS / "revisar_diseno.py"), "saturacion", str(P / "con-tarjeta.html")], capture_output=True, text=True, encoding="utf-8")
chequear("una pantalla con 7 acciones principales falla la no saturación", "acciones principales" in p1.stdout and p1.returncode != 0, p1.stdout)
chequear("lo mismo dentro de una tarjeta (data-tarjeta) no falla: es un catálogo de estados, no una pantalla", "acciones" not in p2.stdout and p2.returncode == 0, p2.stdout)
# 13. documentación
sk = (RAIZ / "skills/senior-diseno/SKILL.md").read_text(encoding="utf-8")
me = (RAIZ / "skills/senior-diseno/references/metodo.md").read_text(encoding="utf-8")
sd = (RAIZ / "skills/senior-diseno/references/sistema-de-diseno.md").read_text(encoding="utf-8")
rd = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("SKILL.md explica el paso de estilo y los comandos", "1b. **Estilo**" in sk and "tarjeta_estilo.py elegir" in sk and "references/estilo.md" in sk)
chequear("metodo.md tiene el paso 2b", "| 2b |" in me and "Paso 2b" in me)
chequear("el sistema de diseño exige actualizar la tarjeta con cada componente", "en el mismo cambio" in sd and "tarjeta_estilo.py estado" in sd)
chequear("el README lo explica, incluido lo que no se puede verificar fuera de la web", "Tarjeta de estilo (antes de las pantallas)" in rd and "no se verifica por script" in rd)
chequear("la plantilla del inventario ya no trae una fila de ejemplo que obligue a mostrar un Botón",
         "| Botón |" not in (RAIZ / "skills/senior-diseno/plantillas/inventario-componentes.md").read_text(encoding="utf-8").split("Ejemplo de fila")[1].split("\n\n", 1)[1])
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(rd) == [])
est = (RAIZ / "skills/senior-diseno/references/estilo.md").read_text(encoding="utf-8")
chequear("estilo.md declara el límite honesto fuera de la web", "Límite honesto" in est and "no se genera ni se verifica por script" in est)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
