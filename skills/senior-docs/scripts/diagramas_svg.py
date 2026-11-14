#!/usr/bin/env python3
"""Diagramas SVG (flujo y secuencia) para el README, en el estilo del tema que eligió el usuario. Lo usa `readme_tarjetas.py` para los tipos `flujo` y `secuencia`.

Salen de JSON (nunca a mano), con el pie de foto obligatorio y los mismos colores del tema. Mantienen el límite de tamaño de los diagramas de `senior-docs`
(hasta 15 nodos en un flujo, 8 participantes y 20 mensajes en una secuencia) y avisan si un texto no entra en lugar de recortarlo.

  flujo      {"tipo": "flujo", "titulo": "...", "columnas": 4, "nodos": [{"id": "a", "texto": "...", "col": 0, "fila": 0, "forma": "caja|decision"}],
              "grupos": [{"texto": "...", "desde": [col, fila], "hasta": [col, fila]}],
              "flechas": [{"de": "a", "a": "b", "texto": "etiqueta opcional", "estilo": "solida|punteada"}], "pie": "..."}
  secuencia  {"tipo": "secuencia", "titulo": "...", "participantes": [{"id": "u", "texto": "Usuario"}],
              "pasos": [{"de": "u", "a": "c", "texto": "...", "estilo": "solida|punteada"} | {"nota": "...", "sobre": "id"} | {"bloque": "alt: ..."}], "pie": "..."}
Solo biblioteca estándar.
"""
from xml.sax.saxutils import escape

ANCHO = 760
MARGEN = 30
TAM = 14
FACTOR = 0.62          # ancho medio de un carácter / tamaño: seguro para las familias monoespaciadas
MAX_NODOS, MAX_PARTICIPANTES, MAX_PASOS = 15, 8, 20


class DiagramaError(ValueError):
    pass


def _lineas(texto, ancho_px, tam=TAM, max_lineas=3):
    por_linea = max(4, int(ancho_px / (tam * FACTOR)))
    res, actual = [], ""
    for p in str(texto).split():
        prueba = (actual + " " + p).strip()
        if len(prueba) <= por_linea or not actual:
            actual = prueba
        else:
            res.append(actual)
            actual = p
    if actual:
        res.append(actual)
    if len(res) > max_lineas or any(len(l) > por_linea for l in res):
        raise DiagramaError(f"el texto «{str(texto)[:40]}…» no entra en {max_lineas} líneas de {int(ancho_px)} px: acortarlo")
    return res


def _t(x, y, tam, peso, color, texto, ancla="middle", extra=""):
    return f'<text x="{x:g}" y="{y:g}" font-size="{tam}" font-weight="{peso}" fill="{color}" text-anchor="{ancla}"{extra}>{escape(str(texto))}</text>'


def _flecha(x1, y1, x2, y2, color, dash=False):
    """Una cabeza de flecha en (x2, y2) orientada según el último tramo (x1, y1) → (x2, y2)."""
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) >= abs(dy):
        s = 1 if dx > 0 else -1
        pts = f"{x2},{y2} {x2 - 9 * s},{y2 - 5} {x2 - 9 * s},{y2 + 5}"
    else:
        s = 1 if dy > 0 else -1
        pts = f"{x2},{y2} {x2 - 5},{y2 - 9 * s} {x2 + 5},{y2 - 9 * s}"
    return f'<polygon points="{pts}" fill="{color}"/>'


def _validar_flujo(t):
    nodos = t.get("nodos") or []
    if not nodos or len(nodos) > MAX_NODOS:
        raise DiagramaError(f"un flujo lleva de 1 a {MAX_NODOS} nodos (tiene {len(nodos)}): si no entra, se divide en diagramas de detalle")
    ids = {n["id"] for n in nodos}
    if len(ids) != len(nodos):
        raise DiagramaError("hay nodos con el mismo id")
    for f in t.get("flechas", []):
        if f["de"] not in ids or f["a"] not in ids:
            raise DiagramaError(f"la flecha {f['de']} → {f['a']} apunta a un nodo que no existe")


def dibujar_flujo(t, tema):
    _validar_flujo(t)
    c = tema["colores"]
    cols = int(t.get("columnas") or (max(n["col"] for n in t["nodos"]) + 1))
    celda = (ANCHO - 2 * MARGEN) / cols
    ancho_nodo = min(celda - 22, 220)
    nodos = {}
    for n in t["nodos"]:
        decision = n.get("forma") == "decision"
        lineas = _lineas(n["texto"], ancho_nodo - (50 if decision else 16), max_lineas=3)
        h = max(64 if decision else 40, 18 * len(lineas) + 18)
        nodos[n["id"]] = {"n": n, "lineas": lineas, "h": h, "decision": decision}
    filas = sorted({n["fila"] for n in t["nodos"]})
    alto_fila = {f: max(v["h"] for v in nodos.values() if v["n"]["fila"] == f) for f in filas}
    y = 74 if not t.get("grupos") else 84
    sep = 54 if not t.get("grupos") else 78
    y_fila = {}
    for f in filas:
        y_fila[f] = y
        y += alto_fila[f] + sep
    alto = int(y - sep + 34)
    for v in nodos.values():
        n = v["n"]
        v["cx"] = MARGEN + (n["col"] + 0.5) * celda
        v["cy"] = y_fila[n["fila"]] + alto_fila[n["fila"]] / 2
        v["top"], v["bot"] = v["cy"] - v["h"] / 2, v["cy"] + v["h"] / 2
        v["izq"], v["der"] = v["cx"] - ancho_nodo / 2, v["cx"] + ancho_nodo / 2
    partes = [_t(MARGEN, 36, 20, 700, c["titulo"], t["titulo"], "start")]
    for g in t.get("grupos", []):
        dentro = [v for v in nodos.values() if g["desde"][0] <= v["n"]["col"] <= g["hasta"][0] and g["desde"][1] <= v["n"]["fila"] <= g["hasta"][1]]
        if not dentro:
            continue
        x0, x1 = min(v["izq"] for v in dentro) - 8, max(v["der"] for v in dentro) + 8
        y0, y1 = min(v["top"] for v in dentro) - 30, max(v["bot"] for v in dentro) + 12
        partes.append(f'<rect x="{x0:g}" y="{y0:g}" width="{x1 - x0:g}" height="{y1 - y0:g}" rx="6" fill="{c["acento"]}" fill-opacity="0.07" '
                      f'stroke="{c["acento"]}" stroke-opacity="0.55" stroke-dasharray="6 4"/>')
        partes.append(_t(x0 + 10, y0 + 19, 13, 700, c["acento"], g["texto"], "start"))
    for f in t.get("flechas", []):
        a, b = nodos[f["de"]], nodos[f["a"]]
        dash = ' stroke-dasharray="6 5"' if f.get("estilo") == "punteada" else ""
        if a["n"]["fila"] == b["n"]["fila"] and a["n"]["col"] != b["n"]["col"]:
            x1, x2 = (a["der"], b["izq"]) if b["cx"] > a["cx"] else (a["izq"], b["der"])
            ruta = [(x1, a["cy"]), (x2, b["cy"])]
        elif b["cy"] > a["cy"]:
            ym = (a["bot"] + b["top"]) / 2
            ruta = [(a["cx"], a["bot"]), (a["cx"], ym), (b["cx"], ym), (b["cx"], b["top"])] if abs(a["cx"] - b["cx"]) > 1 else [(a["cx"], a["bot"]), (b["cx"], b["top"])]
        else:
            ym = b["bot"] + 20 if t.get("grupos") else (a["top"] + b["bot"]) / 2
            ruta = [(a["cx"], a["top"]), (a["cx"], ym), (b["cx"], ym), (b["cx"], b["bot"])] if abs(a["cx"] - b["cx"]) > 1 else [(a["cx"], a["top"]), (b["cx"], b["bot"])]
        d = "M" + " L".join(f"{x:g} {yy:g}" for x, yy in ruta)
        partes.append(f'<path d="{d}" fill="none" stroke="{c["acento"]}" stroke-width="2"{dash}/>')
        partes.append(_flecha(ruta[-2][0], ruta[-2][1], ruta[-1][0], ruta[-1][1], c["acento"]))
        if f.get("texto"):
            mx, my = (ruta[len(ruta) // 2 - 1][0] + ruta[len(ruta) // 2][0]) / 2, (ruta[len(ruta) // 2 - 1][1] + ruta[len(ruta) // 2][1]) / 2
            ancho_t = len(f["texto"]) * 12 * FACTOR * 0.9 + 12
            partes.append(f'<rect x="{mx - ancho_t / 2:g}" y="{my - 10:g}" width="{ancho_t:g}" height="18" fill="{c["fondo"]}"/>')
            partes.append(_t(mx, my + 4, 12, 400, c["texto"], f["texto"]))
    for v in nodos.values():
        if v["decision"]:
            pts = f'{v["cx"]:g},{v["top"]:g} {v["der"]:g},{v["cy"]:g} {v["cx"]:g},{v["bot"]:g} {v["izq"]:g},{v["cy"]:g}'
            partes.append(f'<polygon points="{pts}" fill="{c["fondo"]}" stroke="{c["acento"]}" stroke-width="2"/>')
        else:
            partes.append(f'<rect x="{v["izq"]:g}" y="{v["top"]:g}" width="{ancho_nodo:g}" height="{v["h"]:g}" rx="4" fill="{c["fondo"]}" stroke="{c["acento"]}" stroke-width="2"/>')
        base = v["cy"] - (len(v["lineas"]) - 1) * 9 + 5
        partes += [_t(v["cx"], base + i * 18, TAM, 400, c["texto"], l) for i, l in enumerate(v["lineas"])]
    return "".join(partes), alto


def dibujar_secuencia(t, tema):
    c = tema["colores"]
    ps, pasos = t.get("participantes") or [], t.get("pasos") or []
    if not ps or len(ps) > MAX_PARTICIPANTES or not pasos or len(pasos) > MAX_PASOS:
        raise DiagramaError(f"una secuencia lleva hasta {MAX_PARTICIPANTES} participantes y {MAX_PASOS} pasos (tiene {len(ps)} y {len(pasos)}): si no entra, se divide")
    celda = (ANCHO - 2 * MARGEN) / len(ps)
    x = {p["id"]: MARGEN + (i + 0.5) * celda for i, p in enumerate(ps)}
    ancho_caja = min(celda - 14, 150)
    cajas = {p["id"]: _lineas(p["texto"], ancho_caja - 12, max_lineas=2) for p in ps}
    h_caja = max(len(l) for l in cajas.values()) * 18 + 16
    y0 = 58
    cuerpo, y = [], y0 + h_caja + 30
    for p in pasos:
        if "bloque" in p:
            cuerpo.append(f'<path d="M{MARGEN} {y - 12} H{ANCHO - MARGEN}" stroke="{c["acento"]}" stroke-opacity="0.6" stroke-dasharray="3 5"/>')
            cuerpo.append(_t(MARGEN + 6, y + 4, 12, 700, c["acento"], p["bloque"], "start"))
            y += 34
        elif "nota" in p:
            ancho_n = min(2.2 * celda, 330)
            lineas = _lineas(p["nota"], ancho_n - 16, 13, 3)
            hn = 18 * len(lineas) + 10
            cx = x[p["sobre"]]
            x0 = min(max(cx - ancho_n / 2, MARGEN), ANCHO - MARGEN - ancho_n)
            cuerpo.append(f'<rect x="{x0:g}" y="{y - 14:g}" width="{ancho_n:g}" height="{hn:g}" fill="{c["acento"]}" fill-opacity="0.1" stroke="{c["acento"]}" stroke-opacity="0.7"/>')
            cuerpo += [_t(x0 + ancho_n / 2, y + 3 + i * 18, 13, 400, c["texto"], l) for i, l in enumerate(lineas)]
            y += hn + 34
        else:
            dash = ' stroke-dasharray="6 5"' if p.get("estilo") == "punteada" else ""
            x1, x2 = x[p["de"]], x[p["a"]]
            if x1 == x2:
                lineas = _lineas(p["texto"], celda - 40, 13, 2)
                cuerpo.append(f'<path d="M{x1:g} {y:g} h34 v16 h-34" fill="none" stroke="{c["acento"]}" stroke-width="2"{dash}/>')
                cuerpo.append(_flecha(x1 + 34, y + 16, x1, y + 16, c["acento"]))
                cuerpo += [_t(x1 + 42, y + 3 + i * 16, 13, 400, c["texto"], l, "start") for i, l in enumerate(lineas)]
                y += 40 + 16 * (len(lineas) - 1)
            else:
                lineas = _lineas(p["texto"], abs(x2 - x1) - 14, 13, 2)
                cuerpo += [_t((x1 + x2) / 2, y - 6 - (len(lineas) - 1 - i) * 16, 13, 400, c["texto"], l) for i, l in enumerate(lineas)]
                cuerpo.append(f'<path d="M{x1:g} {y:g} H{x2:g}" stroke="{c["acento"]}" stroke-width="2"{dash}/>')
                cuerpo.append(_flecha(x1, y, x2, y, c["acento"]))
                y += 36 + 16 * (len(lineas) - 1)
    alto = int(y + 14)
    cab = [_t(MARGEN, 36, 20, 700, c["titulo"], t["titulo"], "start")]
    for p in ps:
        cx = x[p["id"]]
        cab.append(f'<path d="M{cx:g} {y0 + h_caja} V{alto - 8}" stroke="{c["acento"]}" stroke-opacity="0.45" stroke-dasharray="4 6"/>')
        cab.append(f'<rect x="{cx - ancho_caja / 2:g}" y="{y0}" width="{ancho_caja:g}" height="{h_caja}" rx="4" fill="{c["fondo"]}" stroke="{c["acento"]}" stroke-width="2"/>')
        n = len(cajas[p["id"]])
        cab += [_t(cx, y0 + h_caja / 2 - (n - 1) * 9 + 5 + i * 18, TAM, 700, c["titulo"], l) for i, l in enumerate(cajas[p["id"]])]
    return "".join(cab) + "".join(cuerpo), alto


def dibujar(tarjeta, tema):
    """(cuerpo SVG, alto en px) de un diagrama."""
    if tarjeta["tipo"] == "flujo":
        return dibujar_flujo(tarjeta, tema)
    return dibujar_secuencia(tarjeta, tema)
