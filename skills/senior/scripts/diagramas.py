#!/usr/bin/env python3
"""Verifica que los diagramas Mermaid de la documentación sean legibles.

Uso:
    python diagramas.py [--raiz .] [--docs docs]

Revisa cada bloque ```mermaid en docs/**/*.md y cada archivo .mmd:
  - Tiene título (encabezado markdown justo arriba o `title:` en el propio bloque).
  - Tiene una descripción de la pregunta que responde (un párrafo corto arriba
    del bloque, o un comentario `%% pregunta: ...` dentro).
  - No supera los límites de tamaño (ver LIMITES). Si los supera, hay que
    DIVIDIR el diagrama: uno general con pocas piezas que enlaza a detalles.

Los límites se pueden ajustar por proyecto en docs/.diagramas.json:
    {"limites": {"secuencia_mensajes": 25}}

Además estima el ANCHO con el que quedaría cada diagrama de flujo o de secuencia al ancho de un README (unos 830 px) y avisa
cuando se achicaría demasiado: horizontal con muchos pasos o etiquetas y mensajes largos se leen chicos o no se leen. La
estimación (calibrada contra Mermaid, con un error de alrededor del 15 %) no dibuja nada y no reemplaza mirar el resultado.

Los conteos son aproximados (análisis por patrones, no un parser completo de
Mermaid). Códigos de salida: 0 todo bien, 1 hay diagramas por corregir.
Solo biblioteca estándar.
"""
import argparse
import json
import re
import sys
from pathlib import Path

LIMITES = {
    "secuencia_participantes": 8,
    "secuencia_mensajes": 20,
    "clases": 10,
    "clase_miembros": 8,
    "flujo_nodos": 15,
    "er_entidades": 10,
}
FLECHA_SEC = re.compile(r"(<<-->>|<<->>|-->>|->>|--x|-x|--\)|-\)|-->|->)")
ARISTA_FLUJO = re.compile(
    r"\b([A-Za-z_]\w*)(?:\s*(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}))?\s*"
    r"(?:-->|---|-\.->|==>|--[ox]|<-->)(?:\|[^|]*\|)?\s*(?=([A-Za-z_]\w*))")
REL_CLASE = re.compile(r"^\s*(\w+)\s*(?:\"[^\"]*\"\s*)?(?:<\|--|--\|>|\*--|--\*|o--|--o|<--|-->|\.\.>|<\.\.|\.\.\|>|<\|\.\.|--|\.\.)\s*(?:\"[^\"]*\"\s*)?(\w+)")
REL_ER = re.compile(r"^\s*(\w+)\s+[|}o{]{1,2}(?:--|\.\.)[|}o{]{1,2}\s+(\w+)")


def cargar_limites(carpeta_docs):
    limites = dict(LIMITES)
    ruta = carpeta_docs / ".diagramas.json"
    if ruta.exists():
        try:
            limites.update(json.loads(ruta.read_text(encoding="utf-8-sig")).get("limites", {}))
        except (OSError, ValueError):
            pass
    return limites


def bloques_de_markdown(texto):
    """Devuelve lista de (linea_inicio, codigo, lineas_previas)."""
    lineas = texto.splitlines()
    res, i = [], 0
    while i < len(lineas):
        if lineas[i].strip().startswith("```mermaid"):
            ini = i
            cuerpo = []
            i += 1
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                cuerpo.append(lineas[i])
                i += 1
            res.append((ini + 1, "\n".join(cuerpo), lineas[max(0, ini - 8):ini]))
        i += 1
    return res


def tipo_diagrama(codigo):
    for linea in codigo.splitlines():
        l = linea.strip()
        if not l or l.startswith(("%%", "---")) or ":" in l.split()[0:1] or l.startswith(("title:", "config:")):
            continue
        if l.startswith("sequenceDiagram"):
            return "secuencia"
        if l.startswith("classDiagram"):
            return "clases"
        if l.startswith(("flowchart", "graph")):
            return "flujo"
        if l.startswith("stateDiagram"):
            return "flujo"
        if l.startswith("erDiagram"):
            return "er"
        return "otro"
    return "otro"


def tiene_titulo(codigo, previas):
    if re.search(r"^\s*title:\s*\S", codigo, re.MULTILINE):
        return True
    return any(re.match(r"^\s*#{1,6}\s+\S", l) or re.match(r"^\s*\*\*[^*]+\*\*\s*$", l) for l in previas)


def tiene_descripcion(codigo, previas):
    if re.search(r"^\s*%%\s*pregunta:\s*\S", codigo, re.MULTILINE):
        return True
    for l in reversed(previas):
        s = l.strip()
        if not s:
            continue
        if s.startswith("#") or re.match(r"^\*\*[^*]+\*\*$", s):
            return False
        return True
    return False


def medir(tipo, codigo):
    """Devuelve dict con las magnitudes relevantes del diagrama."""
    if tipo == "secuencia":
        participantes, mensajes = set(), 0
        for l in codigo.splitlines():
            s = l.strip()
            m = re.match(r"(?:participant|actor)\s+(\w+)", s)
            if m:
                participantes.add(m.group(1))
                continue
            if FLECHA_SEC.search(s) and ":" in s and not s.startswith(("%%", "Note", "note")):
                mensajes += 1
                origen = re.split(r"<<-->>|<<->>|-->>|->>|--x|-x|--\)|-\)|-->|->", s)[0]
                destino = re.split(r"<<-->>|<<->>|-->>|->>|--x|-x|--\)|-\)|-->|->", s, maxsplit=1)[-1].split(":")[0]
                for nombre in (origen, destino):
                    nombre = re.sub(r"^[+\-]|[+\-]$", "", nombre.strip())
                    if re.fullmatch(r"\w+", nombre):
                        participantes.add(nombre)
        return {"participantes": len(participantes), "mensajes": mensajes}
    if tipo == "clases":
        clases, miembros, actual, dentro = set(), {}, None, False
        for l in codigo.splitlines():
            s = l.strip()
            m = re.match(r"class\s+(\w+)\s*(\{)?", s)
            if m:
                actual = m.group(1)
                clases.add(actual)
                miembros.setdefault(actual, 0)
                dentro = bool(m.group(2)) and "}" not in s
                continue
            if dentro:
                if s == "}":
                    dentro = False
                elif s:
                    miembros[actual] = miembros.get(actual, 0) + 1
                continue
            m = re.match(r"(\w+)\s*:\s*\S", s)
            if m and not REL_CLASE.match(s):
                clases.add(m.group(1))
                miembros[m.group(1)] = miembros.get(m.group(1), 0) + 1
                continue
            m = REL_CLASE.match(s)
            if m:
                clases.update(m.groups())
        return {"clases": len(clases), "max_miembros": max(miembros.values(), default=0)}
    if tipo == "flujo":
        nodos = set()
        for m in ARISTA_FLUJO.finditer(codigo):
            nodos.add(m.group(1))
            nodos.add(m.group(2))
        nodos -= set(re.findall(r"^\s*subgraph\s+(\w+)", codigo, re.MULTILINE))  # una fase que agrupa pasos no es un paso
        return {"nodos": len(nodos)}
    if tipo == "er":
        entidades = set(re.findall(r"^\s*(\w+)\s*\{", codigo, re.MULTILINE))
        for l in codigo.splitlines():
            m = REL_ER.match(l)
            if m:
                entidades.update(m.groups())
        return {"entidades": len(entidades)}
    return {}


def excesos(tipo, medidas, limites):
    res = []
    reglas = {
        "secuencia": [("participantes", "secuencia_participantes", "participantes"),
                      ("mensajes", "secuencia_mensajes", "mensajes")],
        "clases": [("clases", "clases", "clases"), ("max_miembros", "clase_miembros", "miembros en una clase")],
        "flujo": [("nodos", "flujo_nodos", "nodos")],
        "er": [("entidades", "er_entidades", "entidades")],
    }
    for medida, limite, nombre in reglas.get(tipo, []):
        if medidas.get(medida, 0) > limites[limite]:
            res.append(f"{medidas[medida]} {nombre} (máx. {limites[limite]})")
    return res


ANCHO_README = 830       # ancho útil del contenido de un README en GitHub de escritorio
ESCALA_BUENA = 0.85      # por encima se lee bien
ESCALA_MINIMA = 0.60     # por debajo se vuelve ilegible
PX_POR_CARACTER = 7.2
SENTIDOS = ("TB", "TD", "BT", "LR", "RL")
NODO_FLUJO = re.compile(r'(?<![\w])([A-Za-z_]\w*)\s*(?:\[\[?"?([^\]"]*)"?\]?\]|\(\(?"?([^)"]*)"?\)?\)|\{"?([^}"]*)"?\})')
MENSAJE_SEC = re.compile(r"^\s*(\w+)\s*(?:<<-->>|<<->>|-->>|->>|--x|-x|--\)|-\)|-->|->)\s*[+-]?(\w+)\s*:\s*(.*)$")
DECLARACION_SEC = re.compile(r"^\s*(?:participant|actor)\s+(\w+)(?:\s+as\s+(.*))?$")


def _ancho_texto(texto):
    lineas = re.split(r"<br\s*/?>", texto) if texto else [""]
    return max(len(l.strip()) for l in lineas) * PX_POR_CARACTER


def _estimar_flujo(codigo):
    if re.search(r"^\s*subgraph\b", codigo, re.M):
        return None  # con fases agrupadas Mermaid reacomoda todo: el ancho solo se sabe dibujándolo
    m = re.search(r"^\s*(?:flowchart|graph)\s+(TB|TD|BT|LR|RL)", codigo, re.M)
    sentido = m.group(1) if m else "TB"
    anchos = {}
    for n in NODO_FLUJO.finditer(codigo):
        nombre = n.group(1)
        texto = next((g for g in n.groups()[1:] if g is not None), nombre)
        rombo = n.group(4) is not None
        anchos.setdefault(nombre, (_ancho_texto(texto) + 32) * (1.9 if rombo else 1.0))
    aristas = []
    for a in ARISTA_FLUJO.finditer(codigo):
        aristas.append((a.group(1), a.group(2)))
        for x in a.groups():
            anchos.setdefault(x, _ancho_texto(x) + 32)
    if not anchos:
        return None
    # capas por camino más largo, ignorando las aristas que vuelven (ciclos)
    hijos = {}
    for a, b in aristas:
        hijos.setdefault(a, []).append(b)
    estado, atras = {}, set()

    def visitar(n):
        estado[n] = 1
        for h in hijos.get(n, []):
            if estado.get(h) == 1:
                atras.add((n, h))
            elif h not in estado:
                visitar(h)
        estado[n] = 2
    for n in list(anchos):
        if n not in estado:
            visitar(n)
    vuelven = len(atras)
    rango = {n: 0 for n in anchos}
    for _ in range(len(anchos)):
        for a, b in aristas:
            if a != b and (a, b) not in atras and rango[b] < rango[a] + 1:
                rango[b] = rango[a] + 1
    tienen_entrada = {b for a, b in aristas if (a, b) not in atras}
    for n in anchos:  # una fuente se acerca a lo que alimenta, como hace Mermaid, en lugar de quedar en la primera capa
        destinos = [rango[b] for a, b in aristas if a == n and (a, b) not in atras]
        if n not in tienen_entrada and destinos and min(destinos) > 1:
            rango[n] = min(destinos) - 1
    capas = {}
    for n, r in rango.items():
        capas.setdefault(r, []).append(anchos[n])
    if sentido in ("LR", "RL"):
        return int(sum(max(c) for c in capas.values()) + 55 * (len(capas) - 1) + 20)
    return int(max(sum(c) + 60 * (len(c) - 1) for c in capas.values()) + 45 * min(vuelven, 3) + 20)


def _estimar_secuencia(codigo):
    orden = []
    for l in codigo.splitlines():
        d = DECLARACION_SEC.match(l)
        if d and d.group(1) not in orden:
            orden.append(d.group(1))
    mensajes = []
    for l in codigo.splitlines():
        m = MENSAJE_SEC.match(l)
        if m:
            for x in (m.group(1), m.group(2)):
                if x not in orden:
                    orden.append(x)
            mensajes.append((m.group(1), m.group(2), len(m.group(3).strip())))
    if len(orden) < 2:
        return None
    huecos = [220.0] * (len(orden) - 1)
    for a, b, largo in mensajes:
        i, j = sorted((orden.index(a), orden.index(b)))
        if i == j:
            continue
        necesita = (PX_POR_CARACTER * largo + 30) / (j - i)
        for k in range(i, j):
            huecos[k] = max(huecos[k], necesita)
    return int(sum(huecos) + 350)


def ancho_estimado(tipo, codigo):
    """Ancho natural aproximado, en px, de un diagrama de flujo o de secuencia; None para los demás tipos."""
    try:
        if tipo == "flujo":
            return _estimar_flujo(codigo)
        if tipo == "secuencia":
            return _estimar_secuencia(codigo)
    except (RecursionError, ValueError, IndexError):
        return None
    return None


def escala_en_readme(ancho):
    return min(1.0, ANCHO_README / ancho) if ancho else 1.0


def aviso_de_ancho(tipo, codigo):
    """Texto del aviso si el diagrama se achicaría demasiado al ancho de un README; None si entra bien."""
    ancho = ancho_estimado(tipo, codigo)
    if not ancho:
        return None
    escala = escala_en_readme(ancho)
    if escala >= ESCALA_BUENA:
        return None
    consejo = ("pasarlo a vertical (TB), con etiquetas de hasta 25 caracteres, o agrupar los pasos en fases" if tipo == "flujo"
               else "mensajes de hasta unos 40 caracteres y menos participantes")
    nivel = "ilegible" if escala < ESCALA_MINIMA else "chico"
    return f"quedaría {nivel} al ancho de un README: ancho estimado {ancho} px, se achica al {round(escala * 100)} % ({consejo})"


def revisar_diagrama(ruta, linea, codigo, previas, limites):
    problemas = []
    if not tiene_titulo(codigo, previas):
        problemas.append("sin título (agregar un encabezado arriba o `title:` en el bloque)")
    if not tiene_descripcion(codigo, previas):
        problemas.append("sin descripción de la pregunta que responde (párrafo arriba o `%% pregunta: ...`)")
    tipo = tipo_diagrama(codigo)
    for e in excesos(tipo, medir(tipo, codigo), limites):
        problemas.append(f"demasiado grande: {e}. Dividir en un diagrama general y diagramas de detalle")
    return [f"{ruta}:{linea} [{tipo}] {p}" for p in problemas]


def analizar(raiz, carpeta_docs):
    limites = cargar_limites(carpeta_docs)
    problemas, total = [], 0
    for ruta in sorted(carpeta_docs.rglob("*.md")):
        rel = ruta.relative_to(raiz).as_posix()
        for linea, codigo, previas in bloques_de_markdown(ruta.read_text(encoding="utf-8-sig", errors="replace")):
            total += 1
            problemas.extend(revisar_diagrama(rel, linea, codigo, previas, limites))
    for ruta in sorted(carpeta_docs.rglob("*.mmd")):
        total += 1
        rel = ruta.relative_to(raiz).as_posix()
        problemas.extend(revisar_diagrama(rel, 1, ruta.read_text(encoding="utf-8-sig", errors="replace"), [], limites))
    return total, problemas


def avisos_de_ancho(raiz, carpeta_docs):
    """[(ruta:línea, aviso)] de los diagramas de docs/ que se achicarían demasiado al ancho de un README. No bloquean."""
    out = []
    for ruta in sorted(carpeta_docs.rglob("*.md")):
        rel = ruta.relative_to(raiz).as_posix()
        for linea, codigo, _ in bloques_de_markdown(ruta.read_text(encoding="utf-8-sig", errors="replace")):
            aviso = aviso_de_ancho(tipo_diagrama(codigo), codigo)
            if aviso:
                out.append((f"{rel}:{linea}", aviso))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--docs", default="docs")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    carpeta = raiz / args.docs
    if not carpeta.is_dir():
        print(f"Diagramas: no existe la carpeta {args.docs}.")
        sys.exit(0)
    total, problemas = analizar(raiz, carpeta)
    if not problemas:
        print(f"Diagramas: {total} revisados, todos legibles.")
        sys.exit(0)
    print(f"Diagramas: {len(problemas)} problemas en {total} diagramas.")
    for p in problemas:
        print(f"  {p}")
    sys.exit(1)


if __name__ == "__main__":
    main()
