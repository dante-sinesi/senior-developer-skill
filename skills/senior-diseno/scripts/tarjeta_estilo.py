#!/usr/bin/env python3
"""Tarjeta de estilo: la definición gráfica del proyecto, antes de diseñar pantallas, y su mantenimiento.

La tarjeta es la primera porción del sistema de diseño, no un documento aparte: usa las variables reales de
`docs/diseno/sistema/tokens.css` y muestra las piezas firma del estilo en todos sus estados. Después sigue viva:
cada componente nuevo del inventario se agrega también a la tarjeta, en el mismo cambio. Este script prepara las
tres alternativas de estilo (A, B y C), registra la elegida y comprueba que la tarjeta no quede vieja.

Uso:
    python tarjeta_estilo.py nueva --nombre <proyecto> [--raiz .]
        Crea docs/diseno/estilo/AAAA-MM-DD-<proyecto>/estilo-a.html, estilo-b.html y estilo-c.html (sin ningún estilo
        impuesto: cada alternativa propone el suyo). Se ajustan con el feedback (crear_bosquejos.py --evolucionar).
    python tarjeta_estilo.py revisar <estilo-x.html>
        Comprueba que la alternativa defina variables y muestre piezas firma con sus estados.
    python tarjeta_estilo.py elegir <estilo-x.html> [--pisar] [--raiz .]
        La alternativa elegida pasa a ser la tarjeta viva docs/diseno/estilo/tarjeta.html; sus variables pasan a
        sistema/tokens.css, sus componentes al inventario y la decisión a notas/decisiones.md.
    python tarjeta_estilo.py componente "<Nombre>" --variantes a,b --estados x,y [--motivo "…"] [--raiz .]
        Registra un componente nuevo (o suma variantes y estados a uno existente) en el inventario y deja en la
        tarjeta un hueco marcado «completar» para mostrarlo. Mientras el hueco siga, la tarjeta cuenta como vieja.
    python tarjeta_estilo.py no-web --plataforma <nombre> --artefacto <ruta> [--recurso <ruta>] [--raiz .]
        Para un juego o programa que no es una página: registra la muestra que vive en el propio programa
        (escena, pantalla o ventana) en docs/diseno/estilo/tarjeta.md.
    python tarjeta_estilo.py estado [--raiz .]
        Dice si la tarjeta está al día: cada componente, variante y estado del inventario y cada variable de color y
        de tipografía están en la tarjeta. Código de salida 1 si no.

Marcas de la tarjeta web: data-componente="Nombre", data-variante="…" y data-estado="…". Solo biblioteca estándar.
"""
import argparse
import re
import sys
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

PLANTILLAS = Path(__file__).resolve().parents[1] / "plantillas"
VACIOS = {"br", "img", "input", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}
MARCA_PENDIENTE = re.compile(r"<!--\s*completar\b", re.I)
FILA_SEPARADOR = re.compile(r"^\|?[\s:|-]+\|?$")


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8-sig", errors="replace")


def escribir(ruta, texto):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")


def norm(texto):
    sin = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sin.lower()).strip()


def slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", norm(texto)).strip("-") or "proyecto"


def rutas(raiz):
    estilo = Path(raiz) / "docs" / "diseno" / "estilo"
    sistema = Path(raiz) / "docs" / "diseno" / "sistema"
    return {"estilo": estilo, "html": estilo / "tarjeta.html", "md": estilo / "tarjeta.md", "sistema": sistema,
            "variables": sistema / "tokens.css", "inventario": sistema / "inventario-componentes.md",
            "decisiones": Path(raiz) / "docs" / "diseno" / "notas" / "decisiones.md"}


class LectorTarjeta(HTMLParser):
    """Componentes marcados con data-componente y las variantes y estados que muestra cada uno."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pila = []          # (etiqueta, nombre de componente o None)
        self.componentes = {}   # nombre normalizado → {"nombre", "variantes", "estados"}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        nombre = a.get("data-componente")
        if nombre:
            self.componentes.setdefault(norm(nombre), {"nombre": nombre, "variantes": set(), "estados": set()})
        activos = [n for _, n in self.pila if n] + ([norm(nombre)] if nombre else [])
        for n in activos:
            if a.get("data-variante"):
                self.componentes[n]["variantes"].add(norm(a["data-variante"]))
            if a.get("data-estado"):
                self.componentes[n]["estados"].add(norm(a["data-estado"]))
        if tag not in VACIOS:
            self.pila.append((tag, norm(nombre) if nombre else None))

    def handle_endtag(self, tag):
        for i in range(len(self.pila) - 1, -1, -1):
            if self.pila[i][0] == tag:
                del self.pila[i:]
                break


def leer_tarjeta(texto):
    lector = LectorTarjeta()
    lector.feed(texto)
    return lector.componentes


def celdas(linea):
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def lista(texto):
    return [norm(x) for x in re.split(r"[,;/]", texto) if x.strip() and not x.strip().startswith("(")]


def leer_tabla(texto, primera_columna):
    """(índice de la línea del encabezado, filas) de la primera tabla cuyo primer encabezado sea `primera_columna`."""
    lineas = texto.splitlines()
    for i, l in enumerate(lineas):
        if l.strip().startswith("|") and norm(celdas(l)[0]) == norm(primera_columna):
            filas, j = [], i + 1
            while j < len(lineas) and lineas[j].strip().startswith("|"):
                if not FILA_SEPARADOR.match(lineas[j].strip()):
                    filas.append((j, celdas(lineas[j])))
                j += 1
            return i, filas
    return None, []


def leer_inventario(texto):
    """{nombre normalizado: {"nombre", "variantes", "estados"}} de la tabla principal de componentes."""
    _, filas = leer_tabla(texto, "Componente")
    out = {}
    for _, c in filas:
        if len(c) >= 3 and c[0] and not c[0].startswith("("):
            out[norm(c[0])] = {"nombre": c[0], "variantes": set(lista(c[1])), "estados": set(lista(c[2]))}
    return out


def variables(css, prefijo):
    return sorted(set(re.findall(r"(--" + prefijo + r"-[\w-]+)\s*:", css)))


def evaluar(raiz):
    """(líneas, ok) para verificar.py. Sin tarjeta no dice nada: el proyecto todavía no definió su estilo."""
    r = rutas(raiz)
    if r["html"].exists():
        return evaluar_web(r)
    if r["md"].exists():
        return evaluar_no_web(r)
    return [], True


def evaluar_web(r):
    html = leer(r["html"])
    tarjeta = leer_tarjeta(html)
    falta = []
    pendientes = len(MARCA_PENDIENTE.findall(html))
    if pendientes:
        falta.append(f"{pendientes} hueco(s) marcado(s) «completar»")
    inventario = leer_inventario(leer(r["inventario"])) if r["inventario"].exists() else {}
    for clave, comp in inventario.items():
        en = tarjeta.get(clave)
        if not en:
            falta.append(f"el componente «{comp['nombre']}»")
            continue
        sin_v = sorted(comp["variantes"] - en["variantes"])
        sin_e = sorted(comp["estados"] - en["estados"])
        if sin_v:
            falta.append(f"las variantes de «{comp['nombre']}»: {', '.join(sin_v)}")
        if sin_e:
            falta.append(f"los estados de «{comp['nombre']}»: {', '.join(sin_e)}")
    extra = [c["nombre"] for k, c in tarjeta.items() if k not in inventario] if inventario else []
    if r["variables"].exists():
        css = leer(r["variables"])
        for nombre in variables(css, "c") + variables(css, "f"):
            if nombre not in html:
                falta.append(f"la variable {nombre}")
    if falta:
        return ["Tarjeta de estilo: está vieja, no muestra " + "; ".join(falta[:6]) + (f" (y {len(falta) - 6} más)" if len(falta) > 6 else "")
                + ". Se actualiza en el mismo cambio que agrega el componente o la variable."
                + (f" Hay componentes en la tarjeta que no están en el inventario: {', '.join(extra[:4])}." if extra else "")], False
    linea = f"Tarjeta de estilo: al día ({len(tarjeta)} componente(s), variables de color y tipografía mostradas)."
    if extra:
        return [linea, f"  Componentes en la tarjeta que no están en el inventario: {', '.join(extra[:4])}: registrarlos."], False
    return [linea], True


def evaluar_no_web(r):
    texto = leer(r["md"])
    _, filas = leer_tabla(texto, "Componente")
    en_tarjeta = {norm(c[0]) for _, c in filas if c and c[0]}
    pendientes = [c[0] for _, c in filas if len(c) > 1 and re.search(r"pendiente|completar", c[1], re.I)]
    inventario = leer_inventario(leer(r["inventario"])) if r["inventario"].exists() else {}
    falta = [c["nombre"] for k, c in inventario.items() if k not in en_tarjeta]
    problemas = []
    if falta:
        problemas.append("no están en la tarjeta: " + ", ".join(falta[:6]))
    if pendientes:
        problemas.append("sin indicar dónde se muestran: " + ", ".join(pendientes[:6]))
    if problemas:
        return ["Tarjeta de estilo (muestra en el programa): está vieja, " + "; ".join(problemas)
                + ". Se actualiza en el mismo cambio que agrega el componente."], False
    return [f"Tarjeta de estilo (muestra en el programa): al día ({len(en_tarjeta)} componente(s))."], True


def nueva(args):
    raiz = Path(args.raiz).resolve()
    r = rutas(raiz)
    ronda = r["estilo"] / f"{args.fecha}-{slug(args.nombre)}"
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import crear_bosquejos as cb
    creados = []
    for letra in "abc":
        contenido = cb.con_visor(cb.rellenar((PLANTILLAS / "estilo.html").read_text(encoding="utf-8"),
                                             {"proyecto": args.nombre, "letra": letra.upper()}), f"Estilo {letra.upper()}")
        cb.escribir_si_falta(ronda / f"estilo-{letra}.html", contenido, creados)
    print(f"Alternativas de estilo listas en {ronda.relative_to(raiz).as_posix()}/ ({len(creados)} archivos creados; lo existente no se tocó).")
    if r["html"].exists():
        print("AVISO: ya hay una tarjeta viva (estilo/tarjeta.html). Una ronda nueva solo se justifica si se redefine el estilo del proyecto.")
    print("Siguiente paso: diseñar tres estilos distintos (cada uno con su paleta, tipografía y piezas firma en todos sus estados), "
          "mostrarlos al usuario y ajustar con su feedback.")


def problemas_de_estilo(html):
    p = []
    m = re.search(r"<style[^>]*data-tokens[^>]*>(.*?)</style>", html, re.S | re.I)
    if not m or not re.search(r"--[\w-]+\s*:", m.group(1)):
        p.append("no define variables de diseño en <style data-tokens> (--c-…, --f-…)")
    else:
        css = m.group(1)
        if not variables(css, "c"):
            p.append("no define ninguna variable de color (--c-…)")
        if not variables(css, "f"):
            p.append("no define ninguna variable de tipografía (--f-…)")
        sin = [v for v in variables(css, "c") + variables(css, "f") if html.count(v) < 2]
        if sin:
            p.append("variables que la tarjeta no nombra fuera de su definición: " + ", ".join(sin[:5]))
    comps = leer_tarjeta(html)
    if not comps:
        p.append("no muestra ninguna pieza firma (marcar cada una con data-componente)")
    for c in comps.values():
        if not c["estados"]:
            p.append(f"«{c['nombre']}» no muestra ningún estado (data-estado)")
    return p


def revisar(args):
    p = problemas_de_estilo(leer(args.archivo))
    print(f"{Path(args.archivo).name}: " + ("listo para mostrar al usuario." if not p else "falta:"))
    for x in p:
        print("  - " + x)
    sys.exit(1 if p else 0)


def siguiente_decision(texto):
    ids = [int(x) for x in re.findall(r"\bD-(\d+)\b", texto)]
    return f"D-{(max(ids) + 1 if ids else 1):03d}"


def agregar_fila(texto, primera_columna, fila):
    """Agrega una fila al final de la tabla; devuelve el texto nuevo."""
    i, filas = leer_tabla(texto, primera_columna)
    lineas = texto.splitlines()
    if i is None:
        return None
    ultimo = filas[-1][0] if filas else i + 1
    lineas.insert(ultimo + 1, "| " + " | ".join(fila) + " |")
    return "\n".join(lineas) + "\n"


def elegir(args):
    raiz = Path(args.raiz).resolve()
    r = rutas(raiz)
    tile = Path(args.archivo)
    if not tile.is_file():
        sys.exit(f"No existe el archivo: {args.archivo}")
    html = leer(tile)
    m = re.search(r"<style[^>]*data-tokens[^>]*>(.*?)</style>", html, re.S | re.I)
    if not m or not re.search(r"--[\w-]+\s*:", m.group(1)):
        sys.exit("Ese estilo no define variables de diseño en <style data-tokens>: no se puede convertir en tarjeta.")
    if r["html"].exists() and not args.pisar:
        sys.exit("Ya hay una tarjeta viva (estilo/tarjeta.html). Para redefinir el estilo del proyecto, repetir con --pisar.")
    css = m.group(1).strip() + "\n"
    plantilla = (PLANTILLAS / "tokens.css").read_text(encoding="utf-8")
    if r["variables"].exists() and re.sub(r"\s+", "", leer(r["variables"])) not in ("", re.sub(r"\s+", "", plantilla)) and not args.pisar:
        sys.exit("sistema/tokens.css ya tiene variables propias. Para reemplazarlas por las de este estilo, repetir con --pisar.")
    escribir(r["variables"], css)
    tarjeta = html[:m.start()] + '<link rel="stylesheet" href="../sistema/tokens.css" data-tokens>' + html[m.end():]
    escribir(r["html"], tarjeta)
    # inventario: las piezas firma de la tarjeta
    comps = leer_tarjeta(html)
    base = leer(r["inventario"]) if r["inventario"].exists() else (PLANTILLAS / "inventario-componentes.md").read_text(encoding="utf-8")
    existentes = leer_inventario(base)
    for clave, c in comps.items():
        if clave in existentes:
            continue
        nuevo = agregar_fila(base, "Componente", [c["nombre"], ", ".join(sorted(c["variantes"])) or "(por definir)",
                                                  ", ".join(sorted(c["estados"])) or "(por definir)", "(por definir)",
                                                  "Pieza firma del estilo"])
        base = nuevo or base
    escribir(r["inventario"], base)
    dec = leer(r["decisiones"]) if r["decisiones"].exists() else "# Decisiones de diseño\n\nUna línea por decisión, con su ID (D-001) y el motivo.\n"
    ident = siguiente_decision(dec)
    dec = dec.rstrip("\n") + f"\n- {ident} — Estilo del proyecto: {tile.name} elegido el {date.today().isoformat()}. La tarjeta viva es docs/diseno/estilo/tarjeta.html y sus variables están en sistema/tokens.css.\n"
    escribir(r["decisiones"], dec)
    print(f"Tarjeta viva creada: {r['html'].relative_to(raiz).as_posix()}. Variables en {r['variables'].relative_to(raiz).as_posix()}, "
          f"{len(comps)} componente(s) en el inventario y decisión {ident} registrada.")
    print("Desde ahora los bosquejos de estructura usan este estilo, y cada componente nuevo se agrega también a la tarjeta (tarjeta_estilo.py componente).")


def componente(args):
    raiz = Path(args.raiz).resolve()
    r = rutas(raiz)
    variantes = [v.strip() for v in args.variantes.split(",") if v.strip()]
    estados = [e.strip() for e in args.estados.split(",") if e.strip()]
    if not estados:
        sys.exit("Falta --estados: cada componente se muestra en todos sus estados.")
    base = leer(r["inventario"]) if r["inventario"].exists() else (PLANTILLAS / "inventario-componentes.md").read_text(encoding="utf-8")
    existentes = leer_inventario(base)
    clave = norm(args.nombre)
    ya_existia = clave in existentes
    if ya_existia:
        i, filas = leer_tabla(base, "Componente")
        lineas = base.splitlines()
        for j, c in filas:
            if norm(c[0]) == clave:
                previas_v, previas_e = [x.strip() for x in c[1].split(",") if x.strip()], [x.strip() for x in c[2].split(",") if x.strip()]
                vs = previas_v + [v for v in variantes if norm(v) not in {norm(x) for x in previas_v}]
                es = previas_e + [e for e in estados if norm(e) not in {norm(x) for x in previas_e}]
                lineas[j] = "| " + " | ".join([c[0], ", ".join(vs), ", ".join(es)] + c[3:]) + " |"
                nombre_real = c[0]
        base = "\n".join(lineas) + "\n"
        print(f"«{nombre_real}» ya existía: se sumaron las variantes y estados al mismo componente (regla: una variante no es un componente nuevo).")
    else:
        base = agregar_fila(base, "Componente", [args.nombre, ", ".join(variantes) or "(única)", ", ".join(estados), "(por definir)", ""]) or base
        if args.motivo:
            base = agregar_fila(base, "Fecha", [date.today().isoformat(), args.nombre, args.motivo, "Registrado"]) or base
        print(f"«{args.nombre}» registrado en el inventario.")
    escribir(r["inventario"], base)
    if r["html"].exists() and ya_existia:
        html = leer(r["html"])
        marca = (f'  <!-- completar: mostrar en «{args.nombre}» '
                 + (f'la(s) variante(s) {", ".join(variantes)} ' if variantes else "") + f'en el/los estado(s) {", ".join(estados)} '
                 '(data-variante y data-estado) y borrar esta marca -->\n')
        if "</main>" in html:
            escribir(r["html"], html.replace("</main>", marca + "</main>", 1))
            print("Marca agregada a la tarjeta: mostrar lo nuevo dentro del componente existente, en el mismo cambio.")
    elif r["html"].exists():
        html = leer(r["html"])
        huecos = "\n".join(f'    <div data-variante="{v}" data-estado="{e}"><!-- completar: mostrar {args.nombre} · {v} · {e} --></div>'
                           for v in (variantes or ["única"]) for e in estados)
        bloque = (f'  <section data-componente="{args.nombre}">\n    <!-- completar: diseñar {args.nombre} con el estilo del proyecto y borrar estas marcas -->\n{huecos}\n  </section>\n')
        if "</main>" in html:
            html = html.replace("</main>", bloque + "</main>", 1)
            escribir(r["html"], html)
            print("Hueco agregado a la tarjeta: completarlo (variantes y estados con data-variante y data-estado) en el mismo cambio.")
    elif r["md"].exists():
        nuevo = agregar_fila(leer(r["md"]), "Componente", [args.nombre, "(pendiente: indicar dónde se muestra)", ", ".join(variantes) or "(única)", ", ".join(estados)])
        if nuevo:
            escribir(r["md"], nuevo)
            print("Fila agregada a tarjeta.md: indicar dónde se muestra en el programa.")
    else:
        print("Todavía no hay tarjeta de estilo: el componente quedó en el inventario.")


def no_web(args):
    raiz = Path(args.raiz).resolve()
    r = rutas(raiz)
    if r["md"].exists():
        sys.exit("Ya existe estilo/tarjeta.md; no se pisa.")
    texto = (PLANTILLAS / "tarjeta-no-web.md").read_text(encoding="utf-8")
    for k, v in {"plataforma": args.plataforma, "artefacto": args.artefacto, "recurso": args.recurso or "(indicar)",
                 "fecha": date.today().isoformat()}.items():
        texto = texto.replace("{{" + k + "}}", v)
    inv = leer(r["inventario"]) if r["inventario"].exists() else ""
    for c in leer_inventario(inv).values():
        texto = texto.rstrip("\n") + f"\n| {c['nombre']} | (pendiente: indicar dónde se muestra) | {', '.join(sorted(c['variantes']))} | {', '.join(sorted(c['estados']))} |\n"
    escribir(r["md"], texto)
    print(f"Registrada la muestra de estilo de {args.plataforma} en {r['md'].relative_to(raiz).as_posix()}.")


def estado(args):
    lineas, ok = evaluar(Path(args.raiz).resolve())
    print("\n".join(lineas) if lineas else "Tarjeta de estilo: todavía no hay (docs/diseno/estilo/). Se crea con `tarjeta_estilo.py nueva`.")
    sys.exit(0 if ok else 1)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)

    def con_raiz(p):
        p.add_argument("--raiz", default=".")
        return p
    n = con_raiz(sub.add_parser("nueva"))
    n.add_argument("--nombre", required=True)
    n.add_argument("--fecha", default=date.today().isoformat())
    rv = sub.add_parser("revisar")
    rv.add_argument("archivo")
    e = con_raiz(sub.add_parser("elegir"))
    e.add_argument("archivo")
    e.add_argument("--pisar", action="store_true")
    c = con_raiz(sub.add_parser("componente"))
    c.add_argument("nombre")
    c.add_argument("--variantes", default="")
    c.add_argument("--estados", default="")
    c.add_argument("--motivo", default="")
    w = con_raiz(sub.add_parser("no-web"))
    w.add_argument("--plataforma", required=True)
    w.add_argument("--artefacto", required=True)
    w.add_argument("--recurso", default="")
    con_raiz(sub.add_parser("estado"))
    args = ap.parse_args()
    {"nueva": nueva, "revisar": revisar, "elegir": elegir, "componente": componente, "no-web": no_web, "estado": estado}[args.orden](args)


if __name__ == "__main__":
    main()
