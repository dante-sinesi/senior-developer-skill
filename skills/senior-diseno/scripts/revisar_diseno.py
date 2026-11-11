#!/usr/bin/env python3
"""Revisión automática de diseño: controla las políticas de la skill sin gastar tokens.

Uso:
    python revisar_diseno.py [chequeo] <archivos o carpetas> [--tipo sitio|app] [--sitio] [--capturas] [--max 30] [--json]

Chequeos (sin indicar ninguno corre "todo"). Ninguno juzga el aspecto artístico:
  base        viewport, reglas responsivas, marcadores sin completar, relleno de texto y frases genéricas
  tipografia  una familia es lo ideal y dos el máximo (por archivo; con --sitio, en el conjunto); más solo con
              <!-- excepcion-tipografia: motivo -->, cuando el arte lo requiere
  saturacion  presupuesto de atención por pantalla: 1 acción principal, 4 campos visibles (6 más en
              opciones avanzadas), 5 acciones, navegación corta, texto por bloque,
              acciones reconocibles (nada de solo íconos, etiquetas verbales)
  interaccion reactividad: hover, foco, presionado, transiciones, menús que se deslizan,
              prefers-reduced-motion, sin "transition: all"
  estados     contenido real y partes que quedan por defecto (solo avisos): estilo de error en los campos,
              estado vacío y de carga en una app, texto largo, color de selección, casillas, cifras de
              tablas y barras de scroll
  etiquetas   formularios: etiqueta visible por campo, sin placeholder como etiqueta, etiquetas únicas
              y no confusas, sin etiquetas genéricas, tipos y autocompletado
  contraste   razón de contraste WCAG de cada par color/fondo (4,5:1 texto normal, 3:1 texto grande)
  sistema     variables de diseño, valores sueltos, estilos en línea y componentes definidos dos veces

Marcas: FALLA incumple una política estricta; AVISO conviene revisar; JUSTIFICADA tenía una excepción
escrita. Para justificar una excepción de una pantalla, dentro de ella:
    <!-- excepcion-saturacion: motivo -->     (también excepcion-etiquetas, excepcion-interaccion…)
Los elementos con data-herramienta (barra de vistas del bosquejo) se ignoran.

Son heurísticas: señalan qué mirar, no dictan el diseño. Código de salida: 0 sin FALLA, 1 con FALLA.
Solo biblioteca estándar.
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colores  # noqa: E402
import htmlmin  # noqa: E402

EXT_DOC = {".html", ".htm", ".php", ".vue", ".svelte", ".jsx", ".tsx", ".ejs", ".twig"}
EXT_CSS = {".css"}
CAMPOS_EXCLUIDOS = {"hidden", "submit", "button", "reset", "image"}
FUENTES_DEFECTO = {"inter", "roboto", "arial", "helvetica", "helvetica neue", "system-ui", "-apple-system",
                   "blinkmacsystemfont", "segoe ui", "open sans", "sans-serif", "ui-sans-serif", "san francisco"}
FRASES_GENERICAS = [r"transforma tu", r"potencia tu", r"lleva tu .{0,30}al siguiente nivel", r"sin fricci[oó]n",
                    r"soluciones innovadoras", r"experiencia [uú]nica", r"todo en un solo lugar", r"el futuro de",
                    r"revoluciona", r"de manera (sencilla|simple) y r[aá]pida", r"unlock", r"seamless",
                    r"supercharge", r"cutting-edge", r"next level", r"get started", r"empower"]
ETIQUETAS_GENERICAS = {"dato", "datos", "informacion", "información", "info", "texto", "campo", "otro", "otros",
                       "valor", "descripcion", "descripción"}
ETIQUETAS_AMBIGUAS = {"fecha", "numero", "número", "codigo", "código", "tipo", "nombre", "estado", "monto"}
BOTONES_GENERICOS = {"aceptar", "ok", "enviar", "submit", "click aquí", "clic aquí", "haz clic aquí", "ver más"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
RE_PASO = re.compile(r"(^|[-_])(paso|step|etapa)([-_\d]|$)", re.IGNORECASE)
TARJETA = re.compile(r"card|tarjeta|feature|beneficio|servicio|plan|item", re.IGNORECASE)


class Doc:
    def __init__(self, ruta):
        self.ruta = str(ruta)
        self.texto = Path(ruta).read_text(encoding="utf-8-sig", errors="replace")
        ext = Path(ruta).suffix.lower()
        self.raiz = htmlmin.parsear(self.texto, ext) if ext not in EXT_CSS else htmlmin.Nodo("#raiz", {}, None, 1)
        if ext in EXT_CSS:
            self.css_texto, self.reglas = self.texto, htmlmin.parsear_css(self.texto)
        else:
            self.css_texto, self.reglas = htmlmin.css_de_documento(self.raiz, ruta)
        self.tokens = htmlmin.tokens_de(self.reglas)
        self.es_pagina = any(n.tag == "html" for n in self.raiz.iterar())


def H(chequeo, sev, doc, linea, msg):
    return {"chequeo": chequeo, "sev": sev, "archivo": doc.ruta, "linea": linea, "msg": msg}


def ignorado(n):
    return n.tiene("data-herramienta") or n.dentro_de(lambda a: a.tiene("data-herramienta"))


def oculto(n):
    return n.tiene("hidden") or n.attr("type") == "hidden" or n.dentro_de(lambda a: a.tiene("hidden"))


def en_avanzado(n):
    def es(a):
        return (a.tag == "details" and not a.tiene("open")) or a.tiene("data-avanzado") or \
            any(("avanzad" in c or "advanced" in c) for c in a.clases())
    return n.dentro_de(es) or es(n)


def pantallas(doc):
    p = [n for n in doc.raiz.iterar() if n.tiene("data-pantalla") and not ignorado(n)]
    if p:
        return p
    cuerpo = [n for n in doc.raiz.iterar() if n.tag == "body"]
    return cuerpo or [doc.raiz]


def excepcion(nodo, chequeo, excluir=frozenset()):
    for n in nodos(nodo, excluir):
        for c in n.comentarios:
            m = re.match(rf"excepcion-{chequeo}\s*:\s*(.+)", c, re.IGNORECASE | re.DOTALL)
            if m:
                return " ".join(m.group(1).split())
    for a in nodo.ancestros():
        for c in a.comentarios:
            m = re.match(rf"excepcion-{chequeo}\s*:\s*(.+)", c, re.IGNORECASE | re.DOTALL)
            if m:
                return " ".join(m.group(1).split())
    return None


def aplicar_excepcion(h, nodo, chequeo, excluir=frozenset()):
    motivo = excepcion(nodo, chequeo, excluir)
    if motivo and h["sev"] == "FALLA":
        h["sev"], h["msg"] = "JUSTIFICADA", f"{h['msg']} (excepción: {motivo})"
    return h


def es_campo(n):
    if n.tag in ("select", "textarea"):
        return True
    return n.tag == "input" and n.attr("type", "text").lower() not in CAMPOS_EXCLUIDOS


def pantallas_con_resto(doc):
    """Pantallas marcadas con data-pantalla más, si queda contenido fuera de ellas, el resto de la página."""
    explicitas = [n for n in doc.raiz.iterar() if n.tiene("data-pantalla") and not ignorado(n)]
    cuerpo = next((n for n in doc.raiz.iterar() if n.tag == "body"), doc.raiz)
    if not explicitas:
        # un formulario por pasos (clases paso, step, etapa) muestra un paso por vez: cada uno es una pantalla
        pasos = [n for n in doc.raiz.iterar() if not ignorado(n) and (n.tiene("data-paso") or n.tiene("data-step") or
                 any(RE_PASO.search(c) for c in n.clases()))]
        pasos = [n for n in pasos if not n.dentro_de(lambda a: a in pasos)]
        if len(pasos) >= 2:
            ids = {id(n) for n in pasos}
            nombres = [f"paso {i + 1}" for i in range(len(pasos))]
            return [(p, set(), nombres[i]) for i, p in enumerate(pasos)] + [(cuerpo, ids, "(resto de la página)")]
        return [(cuerpo, set(), "(página)")]
    ids = {id(n) for n in explicitas}
    return [(p, set(), p.attr("data-pantalla")) for p in explicitas] + [(cuerpo, ids, "(resto de la página)")]


def nodos(p, excluir):
    for n in p.iterar():
        if excluir and any(id(a) in excluir for a in (n, *n.ancestros())):
            continue
        yield n


def campos_de(nodo, excluir=frozenset()):
    """Campos distintos de un nodo; los radios de un mismo grupo cuentan como uno."""
    vistos, res = set(), []
    for n in nodos(nodo, excluir):
        if not es_campo(n) or ignorado(n) or oculto(n):
            continue
        if n.attr("type").lower() == "radio" and n.attr("name"):
            if ("radio", n.attr("name")) in vistos:
                continue
            vistos.add(("radio", n.attr("name")))
        res.append(n)
    return res


def texto_accion(n):
    return " ".join(n.texto().split()).strip() or n.attr("value").strip()


def es_accion(n):
    if n.tag == "button" or n.attr("role") == "button":
        return True
    if n.tag == "input" and n.attr("type").lower() in ("submit", "button", "reset"):
        return True
    return n.tag == "a" and bool(n.clases() & {"btn", "boton", "botón", "button", "cta"} or
                                 any(re.search(r"btn|boton|button|cta", c) for c in n.clases()))


def chequeo_base(doc, opciones):
    """Base técnica y de contenido. No juzga el aspecto: nada de estética."""
    res = []
    if doc.es_pagina and not any(n.tag == "meta" and n.attr("name").lower() == "viewport" for n in doc.raiz.iterar()):
        res.append(H("base", "FALLA", doc, 1, "falta <meta name=\"viewport\">: sin ella no es responsiva en mobile"))
    if doc.reglas and not any("@media" in r.contexto or "@container" in r.contexto for r in doc.reglas):
        res.append(H("base", "AVISO", doc, 1, "no hay reglas responsivas (@media o @container): ¿cómo se adapta a mobile?"))
    visible = doc.raiz.texto()
    marcadores = re.findall(r"\{\{\w+\}\}", doc.texto)
    if marcadores:
        res.append(H("base", "AVISO", doc, 1, f"quedan {len(marcadores)} marcadores {{{{…}}}} sin completar"))
    if re.search(r"lorem ipsum|dolor sit amet", visible, re.IGNORECASE):
        res.append(H("base", "AVISO", doc, 1, "relleno «lorem ipsum»: usar contenido real o plausible marcado como provisorio"))
    for patron in FRASES_GENERICAS:
        m = re.search(patron, visible, re.IGNORECASE)
        if m:
            res.append(H("base", "AVISO", doc, 1, f"frase genérica «{m.group(0)}»: afirmar algo concreto del producto"))
    return res


FAMILIAS_GENERICAS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif", "ui-sans-serif",
                      "ui-monospace", "ui-rounded", "emoji", "math", "fangsong", "inherit", "initial", "unset", "revert", ""}
RE_FUENTE_ICONOS = re.compile(r"icon|awesome|symbols|glyph", re.IGNORECASE)
RE_TAMANO_FONT = re.compile(r"[\d.]+(?:px|rem|em|%|pt|vw|vh)(?:\s*/\s*[\d.]+\w*)?\s+(.+)", re.IGNORECASE)


def familias_de(doc):
    """Primera familia con nombre de cada declaración font-family o font (se ignoran las genéricas y las de íconos)."""
    familias = set()
    for r in doc.reglas:
        if "@font-face" in r.selector or "@font-face" in r.contexto:
            continue
        for prop in ("font-family", "font"):
            v = r.decl.get(prop)
            if not v:
                continue
            v = resolver(v, doc)
            if prop == "font":
                m = RE_TAMANO_FONT.search(v)
                if not m:
                    continue
                v = m.group(1)
            for nombre in re.split(r",", v):
                nombre = nombre.strip().strip("\"'").lower()
                if nombre.startswith("var(") or nombre in FAMILIAS_GENERICAS or RE_FUENTE_ICONOS.search(nombre):
                    continue
                familias.add(nombre)
                break  # solo la primera con nombre: las demás son alternativas de respaldo
    return familias


RE_EXCEPCION_TIPO = re.compile(r"excepcion-tipografia\s*:\s*(.+?)\s*-->", re.IGNORECASE | re.DOTALL)


def hallazgo_tipografia(doc, familias, donde):
    """Una familia es lo ideal, dos el máximo. Más de dos solo si el arte lo requiere, y por escrito:
    <!-- excepcion-tipografia: motivo -->. Con motivo se informa como JUSTIFICADA; sin él, FALLA."""
    if len(familias) <= 2:
        return None
    msg = f"{len(familias)} familias tipográficas {donde} ({', '.join(sorted(familias))}): lo ideal es una y el máximo dos"
    m = RE_EXCEPCION_TIPO.search(doc.texto)
    if m:
        return H("tipografia", "JUSTIFICADA", doc, 1, f"{msg}. Excepción: {m.group(1).strip()[:120]}")
    return H("tipografia", "FALLA", doc, 1, msg + "; si el arte lo requiere, justificarlo con <!-- excepcion-tipografia: motivo -->")


def chequeo_tipografia(doc, opciones):
    """Regla del usuario: una familia tipográfica es lo ideal; dos, el máximo; más solo con excepción escrita."""
    h = hallazgo_tipografia(doc, familias_de(doc), "en la web")
    return [h] if h else []


def resolver(valor, doc):
    return htmlmin.resolver_var(valor, doc.tokens)


def chequeo_saturacion(doc, opciones):
    res = []
    for p, excl, nombre in pantallas_con_resto(doc):
        etiqueta = f"pantalla «{nombre}»"
        hallazgos = []
        campos = campos_de(p, excl)
        visibles = [c for c in campos if not en_avanzado(c)]
        avanzados = [c for c in campos if en_avanzado(c)]
        if len(visibles) > 4:
            hallazgos.append(H("saturacion", "FALLA", doc, p.linea,
                               f"{etiqueta}: {len(visibles)} campos visibles a la vez (máximo 4); pasar el resto a pasos o a «opciones avanzadas»"))
        if len(avanzados) > 6:
            hallazgos.append(H("saturacion", "FALLA", doc, p.linea,
                               f"{etiqueta}: {len(avanzados)} campos en opciones avanzadas (máximo 6)"))
        acciones = [n for n in nodos(p, excl) if es_accion(n) and not ignorado(n) and not oculto(n)
                    and not n.dentro_de(lambda a: a.tag == "nav") and not en_avanzado(n)]
        if len(acciones) > 5:
            hallazgos.append(H("saturacion", "FALLA", doc, p.linea, f"{etiqueta}: {len(acciones)} acciones visibles (máximo 5)"))
        primarias = [n for n in acciones if n.tiene("data-primaria") or
                     any(re.search(r"primar|principal|cta", c) for c in n.clases())]
        if len(primarias) > 1:
            hallazgos.append(H("saturacion", "FALLA", doc, p.linea,
                               f"{etiqueta}: {len(primarias)} acciones principales (debe haber una sola)"))
        if campos and not primarias:
            hallazgos.append(H("saturacion", "AVISO", doc, p.linea, f"{etiqueta}: hay formulario pero ninguna acción principal marcada"))
        for nav in [n for n in nodos(p, excl) if n.tag == "nav" and not ignorado(n)]:
            enlaces = [n for n in nav.iterar() if n.tag == "a"]
            if len(enlaces) > 7:
                hallazgos.append(H("saturacion", "FALLA", doc, nav.linea, f"navegación con {len(enlaces)} destinos (máximo 7 en desktop, 5 en mobile)"))
            elif len(enlaces) > 5:
                hallazgos.append(H("saturacion", "AVISO", doc, nav.linea, f"navegación con {len(enlaces)} destinos: en mobile el máximo es 5"))
        for n in acciones:
            t = texto_accion(n)
            if not re.search(r"\w", t):  # vacío o solo emoji o símbolos como «×»: no hay texto que lo explique
                hallazgos.append(H("saturacion", "FALLA", doc, n.linea, "acción solo con ícono, sin texto visible: sumar una etiqueta verbal"))
            elif t.lower().strip(" .!") in BOTONES_GENERICOS:
                hallazgos.append(H("saturacion", "AVISO", doc, n.linea, f"botón «{t}» genérico: usar verbo y objeto («Guardar pedido»)"))
        if opciones.get("tipo") == "sitio":
            bloques = [n for n in nodos(p, excl) if (n.tiene("data-bloque") or n.tag == "section") and not ignorado(n)]
            for b in bloques:
                palabras = len(b.texto().split())
                if palabras > 80:
                    hallazgos.append(H("saturacion", "AVISO", doc, b.linea,
                                       f"bloque «{b.attr('data-bloque') or b.tag}» con {palabras} palabras: una idea por bloque (referencia: 80)"))
        res.extend(aplicar_excepcion(h, p, "saturacion", excl) for h in hallazgos)
    return res


def _segundos(valor):
    m = re.fullmatch(r"([\d.]+)(ms|s)", valor.strip().lower())
    if not m:
        return None
    n = float(m.group(1))
    return n / 1000.0 if m.group(2) == "ms" else n


def chequeo_interaccion(doc, opciones):
    res = []
    interactivos = [n for n in doc.raiz.iterar() if (n.tag in ("button", "a", "select", "textarea") or
                    (n.tag == "input" and n.attr("type") not in ("hidden",))) and not ignorado(n)]
    if not interactivos or not doc.reglas:
        return res
    sels = " ".join(r.selector.lower() for r in doc.reglas)
    if ":hover" not in sels:
        res.append(H("interaccion", "FALLA", doc, 1, "ningún estado :hover: los botones y enlaces no responden al puntero"))
    if ":focus-visible" not in sels and ":focus" not in sels:
        res.append(H("interaccion", "FALLA", doc, 1, "ningún estado de foco (:focus-visible): inutilizable con teclado"))
    if ":active" not in sels and ":hover" in sels:
        res.append(H("interaccion", "AVISO", doc, 1, "sin estado :active (presionado): en mobile no hay hover, falta la señal de toque"))
    if any(n.tiene("disabled") for n in interactivos) and ":disabled" not in sels and "[disabled]" not in sels:
        res.append(H("interaccion", "AVISO", doc, 1, "hay elementos deshabilitados sin estilo :disabled"))
    transiciones, animaciones = [], False
    for r in doc.reglas:
        for prop, v in r.decl.items():
            if prop.startswith("transition"):
                transiciones.append((r, prop, v))
            if prop.startswith("animation"):
                animaciones = True
    if ":hover" in sels and not transiciones:
        res.append(H("interaccion", "AVISO", doc, 1, "hay :hover pero ninguna transición: los cambios de estado son abruptos"))
    for r, prop, v in transiciones:
        if prop == "transition" and re.match(r"\s*all\b", v):
            res.append(H("interaccion", "AVISO", doc, 1, f"«transition: all» en «{r.selector.strip()[:40]}»: listar las propiedades que cambian"))
        for t in re.findall(r"[\d.]+m?s", v):
            s = _segundos(t)
            if s is not None and s > 0.5:
                res.append(H("interaccion", "AVISO", doc, 1, f"transición de {t} en «{r.selector.strip()[:40]}»: más de 500 ms se siente lento"))
    if (transiciones or animaciones) and not any("prefers-reduced-motion" in r.contexto for r in doc.reglas):
        res.append(H("interaccion", "FALLA", doc, 1, "hay movimiento pero no se respeta prefers-reduced-motion"))
    for r in doc.reglas:
        sel = r.selector.lower()
        if re.search(r"menu|menú|drawer|panel|dropdown|offcanvas|modal|accordion|collapse|sidebar", sel) and \
                r.decl.get("display", "").strip().lower() == "none":
            tiene_mov = any(re.search(r"menu|menú|drawer|panel|dropdown|offcanvas|modal|accordion|collapse|sidebar", x.selector.lower())
                            and any(k.startswith("transition") or k.startswith("animation") for k in x.decl) for x in doc.reglas)
            if not tiene_mov:
                res.append(H("interaccion", "AVISO", doc, 1,
                             f"«{r.selector.strip()[:40]}» se muestra y oculta con display:none y sin transición: aparece de golpe (usar transform u opacity)"))
                break
    return res


def _normal(t):
    return re.sub(r"[^\w\s]", "", t.lower()).strip()


def chequeo_etiquetas(doc, opciones):
    res = []
    contenedores = [n for n in doc.raiz.iterar() if n.tag == "form" and not ignorado(n)] or pantallas(doc)
    ids_etiqueta = {}
    for n in doc.raiz.iterar():
        if n.tag == "label" and n.tiene("for"):
            ids_etiqueta[n.attr("for")] = n
    for cont in contenedores:
        textos = []
        for c in campos_de(cont):
            etiqueta = None
            if c.attr("id") in ids_etiqueta:
                etiqueta = ids_etiqueta[c.attr("id")]
            else:
                for a in c.ancestros():
                    if a.tag == "label":
                        etiqueta = a
                        break
            if etiqueta is None and c.tiene("aria-labelledby"):
                etiqueta = next((n for n in doc.raiz.iterar() if n.attr("id") == c.attr("aria-labelledby")), None)
            nombre = c.attr("name") or c.attr("id") or c.tag
            if etiqueta is None:
                if c.tiene("placeholder") and not c.tiene("aria-label"):
                    res.append(H("etiquetas", "FALLA", doc, c.linea, f"campo «{nombre}» con solo placeholder: la etiqueta visible no puede faltar"))
                elif c.tiene("aria-label"):
                    res.append(H("etiquetas", "FALLA", doc, c.linea, f"campo «{nombre}» sin etiqueta visible (solo aria-label)"))
                else:
                    res.append(H("etiquetas", "FALLA", doc, c.linea, f"campo «{nombre}» sin etiqueta"))
                continue
            t = " ".join(etiqueta.texto().split())
            if etiqueta.tag == "label" and etiqueta is not None and not t:
                res.append(H("etiquetas", "FALLA", doc, c.linea, f"campo «{nombre}» con etiqueta vacía"))
                continue
            textos.append((t, c))
            nt = _normal(t)
            if nt in ETIQUETAS_GENERICAS or re.fullmatch(r"campo \d+", nt):
                res.append(H("etiquetas", "FALLA", doc, c.linea, f"etiqueta genérica «{t}»: decir qué dato es"))
            elif nt in ETIQUETAS_AMBIGUAS:
                res.append(H("etiquetas", "AVISO", doc, c.linea, f"etiqueta «{t}» ambigua: ¿qué {nt}? (ej. «Fecha de entrega»)"))
            if len(t.split()) > 6:
                res.append(H("etiquetas", "AVISO", doc, c.linea, f"etiqueta de {len(t.split())} palabras: acortar"))
            tipo = c.attr("type", "text").lower()
            if re.search(r"correo|e-?mail", nt) and tipo != "email":
                res.append(H("etiquetas", "AVISO", doc, c.linea, f"«{t}» debería ser type=\"email\""))
            if re.search(r"tel[eé]fono|celular|m[oó]vil", nt) and tipo != "tel":
                res.append(H("etiquetas", "AVISO", doc, c.linea, f"«{t}» debería ser type=\"tel\""))
            if re.search(r"correo|e-?mail|tel[eé]fono|celular|^nombre|apellido|direcci[oó]n|c[oó]digo postal", nt) and not c.tiene("autocomplete"):
                res.append(H("etiquetas", "AVISO", doc, c.linea, f"«{t}»: agregar autocomplete para no obligar a reescribir"))
            if tipo in ("radio", "checkbox") and not c.dentro_de(lambda a: a.tag == "fieldset"):
                res.append(H("etiquetas", "AVISO", doc, c.linea, f"opción «{t}» fuera de un fieldset con legend: agrupar las opciones"))
        for i in range(len(textos)):
            for j in range(i + 1, len(textos)):
                a, b = _normal(textos[i][0]), _normal(textos[j][0])
                if not a or not b:
                    continue
                if a == b:
                    res.append(H("etiquetas", "FALLA", doc, textos[j][1].linea, f"etiqueta repetida «{textos[j][0]}»: cada campo necesita la suya o un grupo con título"))
                elif difflib.SequenceMatcher(None, a, b).ratio() >= 0.85:
                    res.append(H("etiquetas", "FALLA", doc, textos[j][1].linea,
                                 f"etiquetas casi iguales «{textos[i][0]}» y «{textos[j][0]}»: se confunden"))
    return res


def _color_de(decl, doc, claves):
    for k in claves:
        if k in decl:
            c = colores.parsear_color(resolver(decl[k], doc))
            if c:
                return c
    return None


def _px(valor, doc):
    m = re.fullmatch(r"([\d.]+)(px|rem|em)", resolver(valor or "", doc).strip().lower())
    if not m:
        return None
    n = float(m.group(1))
    return n * 16 if m.group(2) in ("rem", "em") else n


def chequeo_contraste(doc, opciones):
    res, base = [], {}
    for r in doc.reglas:
        if r.selector.strip() in ("body", "html", ":root", "*"):
            e = base.setdefault(r.contexto, {})
            e["fg"] = e.get("fg") or _color_de(r.decl, doc, ["color"])
            e["bg"] = e.get("bg") or _color_de(r.decl, doc, ["background-color", "background"])
    por_selector = {}
    for r in doc.reglas:  # un mismo selector puede repetirse (por ejemplo dentro de un @media): se juntan sus declaraciones
        por_selector.setdefault(r.selector.strip(), {}).update(r.decl)
    for r in doc.reglas:
        fondo_complejo = any(("gradient" in r.decl.get(k, "").lower() or "url(" in r.decl.get(k, "").lower())
                             for k in ("background", "background-image")) and "background-color" not in r.decl
        if fondo_complejo:
            continue  # el fondo es un degradado o una imagen: no hay un color fijo con el que medir
        fg = _color_de(r.decl, doc, ["color"])
        bg = _color_de(r.decl, doc, ["background-color", "background"])
        if re.search(r":(hover|focus|focus-visible|active)\b", r.selector):
            # un estado hereda del elemento base lo que no redefine (por ejemplo, el color del texto)
            original = por_selector.get(re.sub(r":[\w-]+(\([^)]*\))?", "", r.selector.strip()), {})
            fg = fg or _color_de(original, doc, ["color"])
            bg = bg or _color_de(original, doc, ["background-color", "background"])
        ref = base.get(r.contexto) or base.get("") or {}
        if not fg:
            continue  # sin color de texto propio no hay texto que medir (una barra o un fondo decorativo no cuenta)
        if not bg:
            # el texto se apoya en el fondo de la sección que lo contiene: se busca en los selectores de ancestros
            partes = re.split(r"\s*>\s*|\s+", r.selector.strip())
            for k in range(len(partes) - 1, 0, -1):
                ancestro = por_selector.get(" ".join(partes[:k]), {})
                bg = _color_de(ancestro, doc, ["background-color", "background"])
                if bg:
                    break
            bg = bg or ref.get("bg")
        if not bg:
            continue
        tam, peso = _px(r.decl.get("font-size"), doc), r.decl.get("font-weight", "")
        grande = (tam is not None and tam >= 24) or (tam is not None and tam >= 18.66 and (peso in ("bold", "700", "800", "900")))
        umbral = 3.0 if grande else 4.5
        razon = colores.contraste(fg, bg)
        if razon < umbral:
            res.append(H("contraste", "FALLA", doc, 1, f"«{r.selector.strip()[:50]}»: contraste {razon:.2f}:1 (mínimo {umbral}:1{' por ser texto grande' if grande else ''})"))
    return res


def chequeo_sistema(doc, opciones):
    res = []
    if not doc.reglas:
        return res
    if not doc.tokens:
        res.append(H("sistema", "AVISO", doc, 1, "no hay variables de diseño (--nombre en :root): definir colores, tipografía y espacios una sola vez"))
    sueltos = {}
    for r in doc.reglas:
        if r.selector.strip() in (":root", "html", "body", "*"):
            continue
        for prop, v in r.decl.items():
            if prop.startswith("--") or "var(" in v:
                continue
            for crudo, _ in colores.encontrar_colores(v):
                sueltos[crudo] = sueltos.get(crudo, 0) + 1
    if len(sueltos) > 6:
        res.append(H("sistema", "AVISO", doc, 1, f"{len(sueltos)} colores sueltos fuera de las variables (ej. {', '.join(list(sueltos)[:4])}): usar variables"))
    en_linea = [n for n in doc.raiz.iterar() if n.tiene("style") and not ignorado(n)]
    if en_linea:
        res.append(H("sistema", "AVISO", doc, en_linea[0].linea, f"{len(en_linea)} estilos en línea: saltean las variables y los componentes"))
    espacios = set()
    for r in doc.reglas:
        for prop in ("margin", "padding", "gap", "margin-top", "margin-bottom", "padding-top", "padding-bottom", "padding-left", "padding-right", "row-gap", "column-gap"):
            v = r.decl.get(prop)
            if v and "var(" not in v:
                espacios.update(re.findall(r"[\d.]+px", v))
    if len(espacios) > 10:
        res.append(H("sistema", "AVISO", doc, 1, f"{len(espacios)} espacios distintos en px: definir una escala (ej. 4, 8, 16, 24, 32)"))
    clases = []
    for r in doc.reglas:
        if re.fullmatch(r"\.[\w-]+", r.selector.strip()):
            claves = {f"{k}:{resolver(v, doc).strip().lower()}" for k, v in r.decl.items() if not k.startswith("--")}
            if len(claves) >= 3:
                clases.append((r.selector.strip(), claves))
    visto = set()
    for i in range(len(clases)):
        for j in range(i + 1, len(clases)):
            a, b = clases[i], clases[j]
            if a[0] == b[0] or (a[0], b[0]) in visto:
                continue
            union = len(a[1] | b[1])
            if union and len(a[1] & b[1]) / union >= 0.8:
                visto.add((a[0], b[0]))
                res.append(H("sistema", "AVISO", doc, 1, f"{a[0]} y {b[0]} tienen definiciones casi idénticas: ¿es el mismo componente?"))
    return res


RE_ESTADO_ERROR = re.compile(r"error|invalid|inv[aá]lid|danger|incorrect", re.IGNORECASE)
RE_ESTADO_VACIO = re.compile(r"vac[ií]o|empty|sin resultados|no hay |todav[ií]a no|a[uú]n no ", re.IGNORECASE)
RE_ESTADO_CARGA = re.compile(r"loading|cargando|spinner|skeleton|aria-busy|<progress|aria-live", re.IGNORECASE)
PROPS_TEXTO_LARGO = {"overflow-wrap", "word-wrap", "word-break", "text-overflow", "-webkit-line-clamp", "line-clamp", "hyphens"}


def chequeo_estados(doc, opciones):
    """Contenido real y partes que el navegador deja por defecto. Solo AVISO: nada de esto juzga el aspecto."""
    res = []
    if not doc.reglas or not doc.es_pagina:
        return res
    sels = " ".join(r.selector.lower() for r in doc.reglas)
    props = {p for r in doc.reglas for p in r.decl}
    valores = " ".join(v.lower() for r in doc.reglas for v in r.decl.values())
    nodos_ = [n for n in doc.raiz.iterar() if not ignorado(n)]
    campos = [n for n in nodos_ if es_campo(n) and not oculto(n)]
    botones = [n for n in nodos_ if n.tag == "button" or (n.tag == "input" and n.attr("type") in ("submit", "button"))]
    tipos = {(n.attr("type") or "").lower() for n in nodos_ if n.tag == "input"}
    hay_tabla = any(n.tag == "table" for n in nodos_)
    hay_lista = any(n.tag in ("ul", "ol") for n in nodos_)
    if campos and not (":invalid" in sels or "aria-invalid" in sels or RE_ESTADO_ERROR.search(sels)):
        res.append(H("estados", "AVISO", doc, 1, "los campos no tienen estilo de error (:invalid, [aria-invalid] o una clase de error): ¿cómo se ve un dato mal cargado?"))
    if opciones.get("tipo") == "app":
        if (hay_tabla or hay_lista) and not RE_ESTADO_VACIO.search(doc.texto):
            res.append(H("estados", "AVISO", doc, 1, "hay tablas o listas pero ningún estado vacío: ¿qué ve la persona cuando todavía no hay datos?"))
        if (botones or campos) and not RE_ESTADO_CARGA.search(doc.texto):
            res.append(H("estados", "AVISO", doc, 1, "ningún estado de carga (spinner, esqueleto, aria-busy): ¿cómo se ve una acción en curso?"))
    if not (props & PROPS_TEXTO_LARGO):
        res.append(H("estados", "AVISO", doc, 1, "ningún manejo de texto largo (overflow-wrap, text-overflow o line-clamp): un nombre o un correo largo puede romper la composición"))
    if "::selection" not in sels:
        res.append(H("estados", "AVISO", doc, 1, "el color de selección del texto es el del navegador (::selection): se puede tomar de la paleta"))
    if tipos & {"checkbox", "radio", "range"} and "accent-color" not in props:
        res.append(H("estados", "AVISO", doc, 1, "casillas, opciones o deslizadores con el color del navegador: accent-color los lleva a la paleta"))
    if hay_tabla and "font-variant-numeric" not in props and "tabular-nums" not in valores:
        res.append(H("estados", "AVISO", doc, 1, "hay una tabla sin cifras tabulares (font-variant-numeric: tabular-nums): los números no se alinean"))
    if any(r.decl.get(p, "").strip().lower() in ("auto", "scroll") for r in doc.reglas for p in ("overflow", "overflow-x", "overflow-y")) \
            and "scrollbar" not in sels and not any(p.startswith("scrollbar") for p in props):
        res.append(H("estados", "AVISO", doc, 1, "hay zonas con scroll y la barra es la del navegador (scrollbar-color, scrollbar-width)"))
    return res


CHEQUEOS = {"base": chequeo_base, "tipografia": chequeo_tipografia, "saturacion": chequeo_saturacion, "interaccion": chequeo_interaccion,
            "estados": chequeo_estados, "etiquetas": chequeo_etiquetas, "contraste": chequeo_contraste, "sistema": chequeo_sistema}


def archivos_de(rutas, incluir_css=False):
    res = []
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and (f.suffix.lower() in EXT_DOC or (incluir_css and f.suffix.lower() in EXT_CSS)) \
                        and not (set(f.parts) & {"node_modules", ".git", "vendor", "dist", "build"}):
                    res.append(f)
        elif p.is_file():
            res.append(p)
    return res


def analizar(rutas, chequeos=None, tipo="sitio", incluir_css=False, sitio=False):
    todos, familias, ultimo, textos = [], set(), None, []
    for f in archivos_de(rutas, incluir_css):
        doc = Doc(f)
        ultimo = doc
        textos.append(doc.texto)
        for nombre in (chequeos or CHEQUEOS):
            if sitio and nombre == "tipografia":
                familias |= familias_de(doc)
                continue
            todos.extend(CHEQUEOS[nombre](doc, {"tipo": tipo}))
    if sitio and (chequeos is None or "tipografia" in chequeos) and ultimo is not None:
        h = hallazgo_tipografia(ultimo, familias, "en todo el sitio")
        if h and h["sev"] == "FALLA" and any(RE_EXCEPCION_TIPO.search(d) for d in textos):
            h = H("tipografia", "JUSTIFICADA", ultimo, 1, h["msg"].split(";")[0] + ". Excepción escrita en el sitio")
        if h:
            todos.append(h)
    return todos


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chequeo", choices=["todo", *CHEQUEOS])
    ap.add_argument("rutas", nargs="+")
    ap.add_argument("--tipo", choices=["sitio", "app"], default="sitio")
    ap.add_argument("--sitio", action="store_true", help="la regla de tipografía cuenta en el conjunto de archivos (un sitio completo)")
    ap.add_argument("--capturas", action="store_true", help="además saca capturas de desktop y mobile de cada HTML (usa capturar.py)")
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    nombres = None if args.chequeo == "todo" else [args.chequeo]
    hallazgos = analizar(args.rutas, nombres, args.tipo, sitio=args.sitio)
    if args.json:
        print(json.dumps(hallazgos, ensure_ascii=False, indent=1))
    else:
        fallas = sum(h["sev"] == "FALLA" for h in hallazgos)
        avisos = sum(h["sev"] == "AVISO" for h in hallazgos)
        just = sum(h["sev"] == "JUSTIFICADA" for h in hallazgos)
        if not hallazgos:
            print("Diseño: sin hallazgos.")
        else:
            print(f"Diseño: {fallas} fallas, {avisos} avisos, {just} justificadas.")
            orden = {"FALLA": 0, "AVISO": 1, "JUSTIFICADA": 2}
            for h in sorted(hallazgos, key=lambda x: orden[x["sev"]])[:args.max]:
                print(f"  {h['sev']:11} {h['chequeo']:11} {Path(h['archivo']).name}:{h['linea']} — {h['msg']}")
            if len(hallazgos) > args.max:
                print(f"  … y {len(hallazgos) - args.max} más (usar --max o --json).")
    if args.capturas and not args.json:
        import capturar  # noqa: E402
        for f in [x for x in archivos_de(args.rutas) if x.suffix.lower() in (".html", ".htm")]:
            try:
                png = capturar.capturar_archivo(f)
            except RuntimeError as e:
                print(f"Capturas: {e}")
                break
            if png:
                print(f"Capturas de {f.name}: " + ", ".join(p.name for p in png) + f" (en {png[0].parent.as_posix()})")
            else:
                print(f"Capturas de {f.name}: no se pudo sacar ninguna (probar capturar.py por separado)")
    sys.exit(1 if any(h["sev"] == "FALLA" for h in hallazgos) else 0)


if __name__ == "__main__":
    main()
