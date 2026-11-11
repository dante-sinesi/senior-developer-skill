#!/usr/bin/env python3
"""Analizador liviano de HTML y CSS para las revisiones de diseño (solo biblioteca estándar).

No es un navegador: arma un árbol tolerante con las etiquetas, atributos, textos y comentarios
de un HTML, y extrae las reglas de CSS de los bloques <style> y de las hojas locales enlazadas.
Sirve para revisar patrones, no para renderizar. Las plantillas (PHP, Vue, JSX) se tratan de
forma aproximada: se quitan los bloques de servidor y se normalizan algunos atributos.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NO_VISIBLE = {"script", "style", "template", "head", "title", "noscript"}


class Nodo:
    __slots__ = ("tag", "attrs", "hijos", "padre", "linea", "textos", "comentarios")

    def __init__(self, tag, attrs, padre, linea):
        self.tag, self.attrs, self.padre, self.linea = tag, attrs, padre, linea
        self.hijos, self.textos, self.comentarios = [], [], []

    def iterar(self):
        yield self
        for h in self.hijos:
            yield from h.iterar()

    def attr(self, nombre, defecto=""):
        return self.attrs.get(nombre, defecto) or defecto

    def tiene(self, nombre):
        return nombre in self.attrs

    def clases(self):
        return set(self.attr("class").split())

    def ancestros(self):
        n = self.padre
        while n is not None:
            yield n
            n = n.padre

    def dentro_de(self, predicado):
        return any(predicado(a) for a in self.ancestros())

    def texto(self):
        """Texto visible de este nodo y sus descendientes (sin script, style ni head)."""
        if self.tag in NO_VISIBLE:
            return ""
        partes = list(self.textos)
        for h in self.hijos:
            partes.append(h.texto())
        return " ".join(p for p in (" ".join(x.split()) for x in partes) if p)


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo("#raiz", {}, None, 1)
        self.pila = [self.raiz]

    def handle_starttag(self, tag, attrs):
        nodo = Nodo(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.pila[-1], self.getpos()[0])
        self.pila[-1].hijos.append(nodo)
        if tag not in VOID:
            self.pila.append(nodo)

    def handle_startendtag(self, tag, attrs):
        nodo = Nodo(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.pila[-1], self.getpos()[0])
        self.pila[-1].hijos.append(nodo)

    def handle_endtag(self, tag):
        for i in range(len(self.pila) - 1, 0, -1):
            if self.pila[i].tag == tag:
                del self.pila[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self.pila[-1].textos.append(data)

    def handle_comment(self, data):
        self.pila[-1].comentarios.append(data.strip())


def normalizar_plantilla(texto, ext):
    """Aproxima una plantilla (PHP, Vue, JSX) a HTML plano para poder revisarla."""
    ext = ext.lower()
    if ext == ".php":
        texto = re.sub(r"<\?(?:php|=).*?\?>", "·", texto, flags=re.DOTALL)
    if ext in {".jsx", ".tsx", ".js", ".ts"}:
        texto = texto.replace("className=", "class=").replace("htmlFor=", "for=")
        texto = re.sub(r"\{[^{}]*\}", "x", texto)
        texto = re.sub(r"\{[^{}]*\}", "x", texto)
    return texto


def parsear(texto, ext=".html"):
    p = _Parser()
    p.feed(normalizar_plantilla(texto, ext))
    p.close()
    return p.raiz


class Regla:
    __slots__ = ("selector", "decl", "contexto")

    def __init__(self, selector, decl, contexto):
        self.selector, self.decl, self.contexto = selector, decl, contexto


def _bloques(css):
    """Recorre el CSS devolviendo (prefijo, contenido) de cada bloque de primer nivel."""
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            return
        prefijo = css[i:j].strip()
        nivel, k = 1, j + 1
        while k < n and nivel:
            if css[k] == "{":
                nivel += 1
            elif css[k] == "}":
                nivel -= 1
            k += 1
        yield prefijo, css[j + 1:k - 1]
        i = k


def _declaraciones(cuerpo):
    decl, actual, parentesis = {}, "", 0
    for ch in cuerpo + ";":
        if ch == "(":
            parentesis += 1
        elif ch == ")":
            parentesis = max(0, parentesis - 1)
        if ch == ";" and parentesis == 0:
            if ":" in actual:
                clave, _, valor = actual.partition(":")
                decl[clave.strip().lower()] = valor.strip()
            actual = ""
        else:
            actual += ch
    return decl


def parsear_css(css, contexto=""):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    reglas = []
    for prefijo, cuerpo in _bloques(css):
        if prefijo.startswith("@"):
            m = re.match(r"@([\w-]+)", prefijo)  # también vale @media(max-width:820px), sin espacio
            nombre = "@" + m.group(1).lower() if m else ""
            if nombre in ("@media", "@supports", "@container", "@layer"):
                reglas.extend(parsear_css(cuerpo, f"{contexto} {prefijo}".strip()))
            continue  # @keyframes, @font-face, etc.
        reglas.append(Regla(prefijo, _declaraciones(cuerpo), contexto))
    return reglas


def css_de_documento(raiz, ruta):
    """Devuelve (texto_css, reglas) juntando <style> y hojas locales enlazadas."""
    partes = []
    for n in raiz.iterar():
        if n.tag == "style":
            if not n.tiene("data-herramienta"):  # estilos de la barra de vistas del bosquejo: no son parte del diseño
                partes.append("\n".join(n.textos))
        elif n.tag == "link" and "stylesheet" in n.attr("rel").lower():
            href = n.attr("href")
            if href and "://" not in href and not href.startswith("//"):
                destino = (Path(ruta).parent / href.split("?")[0]).resolve()
                if destino.is_file():
                    partes.append(destino.read_text(encoding="utf-8-sig", errors="replace"))
    texto = "\n".join(partes)
    return texto, parsear_css(texto)


def tokens_de(reglas):
    """Variables CSS (--nombre) declaradas en :root, html o body."""
    tokens = {}
    for r in reglas:
        if r.selector.strip() in (":root", "html", "body", "*"):
            for k, v in r.decl.items():
                if k.startswith("--"):
                    tokens[k] = v
    return tokens


def resolver_var(valor, tokens, profundidad=0):
    """Resuelve var(--x, respaldo) usando los tokens; devuelve el valor final o el texto original."""
    if profundidad > 6:
        return valor

    def reemplazo(m):
        nombre, respaldo = m.group(1).strip(), (m.group(2) or "").strip()
        if nombre in tokens:
            return resolver_var(tokens[nombre], tokens, profundidad + 1)
        return respaldo or m.group(0)

    return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)", reemplazo, valor)
