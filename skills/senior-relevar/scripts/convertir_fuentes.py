#!/usr/bin/env python3
"""Ingesta opcional: convierte documentos externos a Markdown dentro de docs/fuentes/.

Uso:
    python convertir_fuentes.py <rutas...> [--raiz .] [--salida docs/fuentes] [--forzar] [--lista]

<rutas> pueden ser archivos o carpetas (se recorren). Formatos: pdf, docx, pptx, xlsx, xls,
html, htm, csv, json, xml. Las IMÁGENES no se convierten: Claude las lee directamente y las
interpreta mejor que cualquier conversión.

Qué hace:
  - Convierte localmente con la biblioteca `markitdown` (dependencia OPCIONAL, no incluida:
    `pip install "markitdown[all]"`). No instala nada por su cuenta y no envía nada a la red:
    no usa ningún modelo para describir imágenes.
  - Guarda cada resultado como docs/fuentes/<nombre>.md con un encabezado (origen, hash, fecha)
    para que el índice de documentación lo encuentre y se pueda rastrear de dónde salió.
  - No reconvierte lo que no cambió (compara el hash) salvo con --forzar. Nunca borra nada.
  - Avisa cuando la conversión probablemente perdió información: casi sin texto (imágenes),
    o texto largo sin encabezados (estructura perdida). En esos casos conviene leer el archivo
    original directamente.
Con --lista solo muestra qué convertiría, sin escribir nada.

Códigos de salida: 0 bien, 1 hubo errores de conversión, 2 falta `markitdown`.
"""
import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

FORMATOS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".html", ".htm", ".csv", ".json", ".xml"}
IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
IGNORAR = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv", "docs"}
MIN_TEXTO = 200
MIN_PARA_ENCABEZADOS = 3000


def hash_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def nombre_de_salida(ruta, usados):
    base = re.sub(r"[^\w\-.]+", "_", ruta.stem, flags=re.UNICODE).strip("_") or "documento"
    nombre = base
    if nombre.lower() in usados:
        nombre = f"{base}_{hashlib.sha256(str(ruta).encode()).hexdigest()[:6]}"
    usados.add(nombre.lower())
    return nombre + ".md"


def recolectar(rutas):
    archivos, imagenes = [], []
    for r in rutas:
        p = Path(r)
        candidatos = [p] if p.is_file() else sorted(p.rglob("*")) if p.is_dir() else []
        for c in candidatos:
            if not c.is_file() or set(c.parts) & IGNORAR:
                continue
            ext = c.suffix.lower()
            if ext in FORMATOS:
                archivos.append(c)
            elif ext in IMAGENES:
                imagenes.append(c)
    return archivos, imagenes


def hash_guardado(destino):
    if not destino.exists():
        return None
    m = re.search(r"(?m)^sha256:\s*([0-9a-f]{64})\s*$", destino.read_text(encoding="utf-8", errors="replace")[:600])
    return m.group(1) if m else None


def avisos_de(texto, ext):
    res = []
    if ext not in {".pdf", ".pptx", ".docx"}:
        return res  # en tablas y datos chicos, poco texto es normal
    limpio = re.sub(r"\s+", " ", texto).strip()
    if len(limpio) < MIN_TEXTO:
        res.append("casi sin texto: probablemente son imágenes; leer el archivo original directamente")
    elif len(limpio) > MIN_PARA_ENCABEZADOS and not re.search(r"(?m)^#{1,6}\s", texto):
        res.append("sin encabezados: la estructura (títulos, tablas, figuras) probablemente no se conservó; "
                   "contrastar con el original si importa el diseño")
    return res


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rutas", nargs="+")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--salida", default="docs/fuentes")
    ap.add_argument("--forzar", action="store_true", help="reconvertir aunque el archivo no haya cambiado")
    ap.add_argument("--lista", action="store_true", help="solo mostrar qué se convertiría")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    archivos, imagenes = recolectar(args.rutas)
    if imagenes:
        print(f"Imágenes sin convertir ({len(imagenes)}): se leen directo, no necesitan conversión.")
    if not archivos:
        print("Fuentes: no hay documentos convertibles en las rutas indicadas.")
        return 0
    if args.lista:
        for a in archivos:
            print(f"  convertiría: {a}")
        print(f"Fuentes: {len(archivos)} documentos (nada se escribió).")
        return 0
    try:
        from markitdown import MarkItDown
    except ImportError:
        print('Falta la biblioteca opcional `markitdown`. Instalarla con: pip install "markitdown[all]"\n'
              "(este script no instala nada por su cuenta).")
        return 2
    conversor = MarkItDown()
    destino_dir = raiz / args.salida
    destino_dir.mkdir(parents=True, exist_ok=True)
    usados, hechos, omitidos, errores, avisos = set(), 0, 0, 0, []
    for origen in archivos:
        destino = destino_dir / nombre_de_salida(origen, usados)
        h = hash_de(origen)
        if not args.forzar and hash_guardado(destino) == h:
            omitidos += 1
            continue
        try:
            texto = conversor.convert(str(origen)).text_content
        except Exception as e:  # noqa: BLE001 - se informa cualquier fallo del conversor
            print(f"  ERROR {origen.name}: {str(e)[:120]}")
            errores += 1
            continue
        try:
            rel = origen.resolve().relative_to(raiz).as_posix()
        except ValueError:
            rel = origen.name  # fuera del proyecto: no se publica la ruta completa
        encabezado = (f"---\nid: FUENTE-{destino.stem}\ntipo: fuente\ntitulo: {origen.stem}\n"
                      f"resumen: Conversión automática de {origen.name}\norigen: {rel}\nsha256: {h}\n"
                      f"convertido: {date.today().isoformat()}\n---\n\n")
        destino.write_text(encabezado + texto, encoding="utf-8", newline="\n")
        hechos += 1
        for a in avisos_de(texto, origen.suffix.lower()):
            avisos.append(f"  AVISO {origen.name}: {a}")
        print(f"  convertido: {origen.name} -> {destino.relative_to(raiz).as_posix()} "
              f"(~{len(texto) // 4:,} tokens de texto)")
    print(f"Fuentes: {hechos} convertidos, {omitidos} sin cambios, {errores} con error.")
    for a in avisos:
        print(a)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
