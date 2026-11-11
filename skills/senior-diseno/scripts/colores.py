#!/usr/bin/env python3
"""Utilidades de color y contraste WCAG (solo biblioteca estándar).

Uso como herramienta:
    python colores.py "#1a1a1a" "#ffffff"      # razón de contraste entre dos colores
"""
import colorsys
import re
import sys

NOMBRES = {
    "white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0), "blue": (0, 0, 255),
    "green": (0, 128, 0), "gray": (128, 128, 128), "grey": (128, 128, 128), "silver": (192, 192, 192),
    "navy": (0, 0, 128), "purple": (128, 0, 128), "orange": (255, 165, 0), "yellow": (255, 255, 0),
    "teal": (0, 128, 128), "maroon": (128, 0, 0), "olive": (128, 128, 0), "lime": (0, 255, 0),
    "aqua": (0, 255, 255), "fuchsia": (255, 0, 255), "indigo": (75, 0, 130), "violet": (238, 130, 238),
}
RE_HEX = re.compile(r"#([0-9a-fA-F]{3,8})\b")
RE_FUNC = re.compile(r"(rgba?|hsla?)\(\s*([^)]*)\)", re.IGNORECASE)


def _num(texto, porcentaje_base=255.0):
    texto = texto.strip()
    if texto.endswith("%"):
        return float(texto[:-1]) / 100.0 * porcentaje_base
    return float(texto)


def parsear_color(valor):
    """Devuelve (r, g, b) de 0 a 255, o None si no es un color fijo reconocible."""
    v = valor.strip().lower()
    if v in NOMBRES:
        return NOMBRES[v]
    m = RE_HEX.fullmatch(v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        elif len(h) in (6, 8):
            h = h[:6]
        else:
            return None
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = RE_FUNC.fullmatch(v)
    if m:
        tipo = m.group(1).lower()
        partes = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
        try:
            if tipo.startswith("rgb") and len(partes) >= 3:
                return tuple(max(0, min(255, round(_num(p)))) for p in partes[:3])
            if tipo.startswith("hsl") and len(partes) >= 3:
                h = float(partes[0].replace("deg", "")) / 360.0
                s, l = _num(partes[1], 1.0), _num(partes[2], 1.0)
                r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0, min(1, l)), max(0, min(1, s)))
                return (round(r * 255), round(g * 255), round(b * 255))
        except ValueError:
            return None
    return None


def encontrar_colores(texto):
    """Colores fijos (hex, rgb, hsl) que aparecen dentro de un texto de CSS."""
    res = []
    for m in RE_HEX.finditer(texto):
        c = parsear_color(m.group(0))
        if c:
            res.append((m.group(0).lower(), c))
    for m in RE_FUNC.finditer(texto):
        c = parsear_color(m.group(0))
        if c:
            res.append((m.group(0).lower(), c))
    return res


def luminancia(rgb):
    def canal(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = luminancia(a), luminancia(b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


def matiz(rgb):
    """Matiz en grados (0 a 360) y saturación (0 a 1)."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    return h * 360.0, s


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a, b = parsear_color(sys.argv[1]), parsear_color(sys.argv[2])
    if not a or not b:
        sys.exit("No se pudo interpretar alguno de los colores.")
    r = contraste(a, b)
    print(f"Contraste {r:.2f}:1 — texto normal (4,5) {'cumple' if r >= 4.5 else 'NO cumple'}, "
          f"texto grande y componentes (3) {'cumple' if r >= 3 else 'NO cumple'}")
