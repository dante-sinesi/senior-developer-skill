#!/usr/bin/env python3
"""Conversión OBLIGATORIA de documentos e imágenes externos: ningún original se lee sin pasar por aquí.

Uso:
    python convertir_fuentes.py [rutas...] [--raiz .] [--salida docs/fuentes] [--max-px 1024] [--forzar] [--lista] [--estado]
    python convertir_fuentes.py --importar <archivos...>     # copia a documentos-externos/ y convierte
    python convertir_fuentes.py --iniciar                    # al abrir un proyecto: crea la carpeta y procesa lo pendiente

La carpeta de entrada es `documentos-externos/`, en la raíz del proyecto: el usuario deja ahí sus archivos.
Sin rutas se recorre esa carpeta. Con `--importar` se COPIAN a ella los archivos que llegan de otro lado (por
ejemplo, los que el usuario manda por el chat) y se procesan: copiar no es leer, y el original nunca se abre.
Con `--iniciar` se crea la carpeta si falta (solo en un proyecto: con .git o docs/) y se procesa lo pendiente;
no imprime nada si no hay nada que hacer.

DOCUMENTOS (pdf, docx, pptx, xlsx, xls, html, htm, csv, json, xml, txt, md, epub) -> Markdown:
  - Se convierten localmente con la biblioteca `markitdown` (OBLIGATORIA: `pip install "markitdown[all]"`).
  - Se guardan como docs/fuentes/<nombre>.md con un encabezado (origen, hash, fecha). Lo único que se lee es ese .md.
  - Avisan cuando la conversión probablemente perdió información (casi sin texto, texto largo sin encabezados):
    son los casos de excepción (PDF escaneado, diseño visual); NO se lee el original por cuenta propia.
IMÁGENES (png, jpg, gif, webp, bmp, tiff) -> reducidas a un máximo de --max-px píxeles en el lado más largo
(1024 por defecto: ahorra entre 50 % y 75 % de tokens de visión sin perder legibilidad en casi todos los casos):
  - Se reducen con la biblioteca `Pillow` (OBLIGATORIA para imágenes: `pip install pillow`), respetando la
    orientación EXIF y sin agrandar nunca. Se guardan en docs/fuentes/imagenes/ y esa copia es la que se lee.
  - Si hace falta más detalle (texto pequeño que no se lee), el usuario puede pedir un máximo mayor con --max-px.
  - Los SVG son texto vectorial: no se reducen.
No instala nada por su cuenta, no envía nada a la red y no usa ningún modelo para describir imágenes.
Nunca borra nada y no reprocesa lo que no cambió (compara el hash) salvo con --forzar.
Con --lista solo muestra qué haría y con --estado qué está al día, pendiente o cambiado
(sin escribir nada; devuelve 1 si hay algo sin procesar).

Códigos de salida: 0 bien, 1 hubo errores o (con --estado) archivos sin procesar, 2 falta `markitdown` o
`Pillow`. Si falta, no se lee ningún original como alternativa: se pide al usuario que apruebe la instalación.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

CARPETA_ENTRADA = "documentos-externos"
FORMATOS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".html", ".htm", ".csv", ".json", ".xml", ".txt", ".md", ".epub"}
IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
VECTORIALES = {".svg"}
IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", "docs"}
MIN_TEXTO = 200
MIN_PARA_ENCABEZADOS = 3000
MAX_PX = 1024
SUBCARPETA_IMAGENES = "imagenes"
MANIFIESTO = "manifiesto.json"
LEEME = """# Documentos externos

Dejar aquí los archivos del cliente o de referencia (HTML, PDF, Word, Excel, PowerPoint, JSON, CSV, imágenes…) y avisar.
Lo que llegue por el chat se copia aquí con `convertir_fuentes.py --importar`.

Nada de lo que hay aquí se lee directo: los documentos se convierten a Markdown (se lee `docs/fuentes/`) y las
imágenes se reducen a un máximo de 1024 px (se lee `docs/fuentes/imagenes/`), todo con
`senior-relevar/scripts/convertir_fuentes.py`.
Excepciones: PDF escaneados sin texto y documentos donde importa el diseño visual (se usa el original o capturas,
con el usuario al tanto).
"""


def hash_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def nombre_de_salida(ruta, usados, extension=".md"):
    base = re.sub(r"[^\w\-.]+", "_", ruta.stem, flags=re.UNICODE).strip("_") or "documento"
    nombre = base
    if nombre.lower() in usados:
        nombre = f"{base}_{hashlib.sha256(str(ruta).encode()).hexdigest()[:6]}"
    usados.add(nombre.lower())
    return nombre + extension


def es_proyecto(raiz):
    """Solo se crea la carpeta de entrada dentro de un proyecto (no en el home ni en una carpeta cualquiera)."""
    return raiz != Path.home() and raiz.parent != raiz and ((raiz / ".git").exists() or (raiz / "docs").is_dir())


def asegurar_carpeta(raiz):
    """Crea documentos-externos/ si falta. Devuelve True si la creó."""
    carpeta = raiz / CARPETA_ENTRADA
    if carpeta.is_dir():
        return False
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "LEEME.md").write_text(LEEME, encoding="utf-8", newline="\n")
    return True


def recolectar(rutas):
    """Devuelve (documentos, imágenes, vectoriales, otros)."""
    archivos, imagenes, vectoriales, otros = [], [], [], []
    for r in rutas:
        p = Path(r)
        candidatos = [p] if p.is_file() else sorted(p.rglob("*")) if p.is_dir() else []
        for c in candidatos:
            if not c.is_file() or set(c.parts) & IGNORAR or c.name.startswith(".") or \
                    (c.name.lower() == "leeme.md" and c.parent.name == CARPETA_ENTRADA):
                continue
            ext = c.suffix.lower()
            if ext in FORMATOS:
                archivos.append(c)
            elif ext in IMAGENES:
                imagenes.append(c)
            elif ext in VECTORIALES:
                vectoriales.append(c)
            elif c.name.lower() != "desktop.ini":
                otros.append(c)
    return archivos, imagenes, vectoriales, otros


def hash_guardado(destino):
    if not destino.exists():
        return None
    m = re.search(r"(?m)^sha256:\s*([0-9a-f]{64})\s*$", destino.read_text(encoding="utf-8", errors="replace")[:600])
    return m.group(1) if m else None


def plan_de_conversion(archivos, destino_dir):
    """Lista de (origen, destino, estado) con estado «al-dia», «pendiente» (sin convertir) o «cambiado»."""
    usados, plan = set(), []
    for origen in archivos:
        destino = destino_dir / nombre_de_salida(origen, usados)
        guardado = hash_guardado(destino)
        if guardado is None:
            estado = "pendiente"
        elif guardado == hash_de(origen):
            estado = "al-dia"
        else:
            estado = "cambiado"
        plan.append((origen, destino, estado))
    return plan


def extension_de_salida(origen):
    return ".jpg" if origen.suffix.lower() in {".jpg", ".jpeg"} else ".png"


def leer_manifiesto(dir_imagenes):
    ruta = dir_imagenes / MANIFIESTO
    try:
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    except ValueError:
        return {}


def plan_de_imagenes(imagenes, destino_dir):
    """Lista de (origen, destino, estado) para las imágenes; el estado sale del manifiesto de docs/fuentes/imagenes/."""
    dir_imagenes = destino_dir / SUBCARPETA_IMAGENES
    manifiesto = leer_manifiesto(dir_imagenes)
    usados, plan = set(), []
    for origen in imagenes:
        destino = dir_imagenes / nombre_de_salida(origen, usados, extension_de_salida(origen))
        previo = manifiesto.get(destino.name)
        if not previo or not destino.exists():
            estado = "pendiente"
        elif previo.get("sha256") == hash_de(origen):
            estado = "al-dia"
        else:
            estado = "cambiado"
        plan.append((origen, destino, estado))
    return plan


def estado_de_fuentes(raiz, salida="docs/fuentes"):
    """(archivos sin procesar o cambiados, total) de la carpeta de entrada; para verificar.py."""
    carpeta = raiz / CARPETA_ENTRADA
    archivos, imagenes, _, _ = recolectar([carpeta] if carpeta.is_dir() else [])
    plan = plan_de_conversion(archivos, raiz / salida) + plan_de_imagenes(imagenes, raiz / salida)
    return [(o, e) for o, _, e in plan if e != "al-dia"], len(plan)


def importar(rutas, raiz):
    """Copia los archivos a documentos-externos/ sin abrirlos (solo se calcula su hash).
    Devuelve (copiados, vectoriales, sin_soporte)."""
    asegurar_carpeta(raiz)
    carpeta = raiz / CARPETA_ENTRADA
    copiados, vectoriales, otros = [], [], []
    for r in rutas:
        p = Path(r)
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in VECTORIALES:
            vectoriales.append(p)
            continue
        if ext not in FORMATOS and ext not in IMAGENES:
            otros.append(p)
            continue
        destino = carpeta / p.name
        if destino.exists() and hash_de(destino) != hash_de(p):
            destino = carpeta / f"{p.stem}_{hash_de(p)[:6]}{p.suffix}"
        if not destino.exists():
            shutil.copy2(p, destino)
        copiados.append(destino)
    return copiados, vectoriales, otros


def avisos_de(texto, ext):
    res = []
    if ext not in {".pdf", ".pptx", ".docx"}:
        return res  # en tablas y datos chicos, poco texto es normal
    limpio = re.sub(r"\s+", " ", texto).strip()
    if len(limpio) < MIN_TEXTO:
        res.append("casi sin texto: probablemente es un PDF escaneado o son imágenes. Es una excepción: NO leer el original "
                   "por cuenta propia; avisar al usuario y preguntarle si lo lee como imagen o si lo pasa con OCR")
    elif len(limpio) > MIN_PARA_ENCABEZADOS and not re.search(r"(?m)^#{1,6}\s", texto):
        res.append("sin encabezados: la estructura (títulos, tablas, figuras) probablemente no se conservó; "
                   "si importa el diseño, avisar al usuario (es la otra excepción) en lugar de abrir el original")
    return res


def convertir(plan, raiz, destino_dir, forzar, silencioso=False):
    """Convierte lo pendiente de los documentos. Devuelve (código, líneas de salida)."""
    pendientes = [p for p in plan if p[2] != "al-dia" or forzar]
    if not pendientes:
        return 0, ([] if silencioso or not plan else [f"Fuentes: {len(plan)} documentos sin cambios."])
    try:
        from markitdown import MarkItDown
    except ImportError:
        return 2, ['Falta `markitdown`, que es OBLIGATORIA: ningún documento externo se lee sin convertirlo antes.',
                   'NO leer los originales como alternativa. Pedir al usuario que apruebe la instalación: '
                   'pip install "markitdown[all]" (este script no instala nada por su cuenta).']
    conversor = MarkItDown()
    destino_dir.mkdir(parents=True, exist_ok=True)
    salida, avisos, hechos, omitidos, errores = [], [], 0, 0, 0
    for origen, destino, estado in plan:
        if estado == "al-dia" and not forzar:
            omitidos += 1
            continue
        h = hash_de(origen)
        try:
            texto = conversor.convert(str(origen)).text_content
        except Exception as e:  # noqa: BLE001 - se informa cualquier fallo del conversor
            salida.append(f"  ERROR {origen.name}: {str(e)[:120]}")
            errores += 1
            continue
        try:
            rel = origen.resolve().relative_to(raiz).as_posix()
        except ValueError:
            rel = origen.name  # fuera del proyecto: no se publica la ruta completa
        notas = avisos_de(texto, origen.suffix.lower())
        sugerida = ""
        if notas:
            motivo = "PDF escaneado o casi sin texto" if "casi sin texto" in " ".join(notas) else "estructura perdida"
            sugerida = f"lectura-directa: sugerida ({motivo})\n"
        encabezado = (f"---\nid: FUENTE-{destino.stem}\ntipo: fuente\ntitulo: {origen.stem}\n"
                      f"resumen: Conversión automática de {origen.name}\norigen: {rel}\nsha256: {h}\n"
                      f"convertido: {date.today().isoformat()}\n{sugerida}---\n\n")
        destino.write_text(encabezado + texto, encoding="utf-8", newline="\n")
        hechos += 1
        for a in notas:
            avisos.append(f"  AVISO {origen.name}: {a}")
        salida.append(f"  convertido: {origen.name} -> {destino.relative_to(raiz).as_posix()} "
                      f"(~{len(texto) // 4:,} tokens de texto)")
    salida.append(f"Fuentes: {hechos} convertidos, {omitidos} sin cambios, {errores} con error. "
                  f"Leer solo los .md de {destino_dir.relative_to(raiz).as_posix()}/.")
    return (1 if errores else 0), salida + avisos


def tokens_de_vision(ancho, alto):
    """Estimación de los tokens de una imagen: píxeles / 750."""
    return max(1, round(ancho * alto / 750))


def reducir_imagenes(plan, raiz, destino_dir, max_px, forzar, silencioso=False):
    """Reduce las imágenes pendientes a max_px en el lado más largo. Devuelve (código, líneas de salida)."""
    pendientes = [p for p in plan if p[2] != "al-dia" or forzar]
    if not pendientes:
        return 0, ([] if silencioso or not plan else [f"Imágenes: {len(plan)} sin cambios."])
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return 2, ["Falta `Pillow`, que es OBLIGATORIA para las imágenes: ninguna imagen externa se lee sin reducirla antes.",
                   "NO leer la imagen original como alternativa. Pedir al usuario que apruebe la instalación: "
                   "pip install pillow (este script no instala nada por su cuenta)."]
    dir_imagenes = destino_dir / SUBCARPETA_IMAGENES
    dir_imagenes.mkdir(parents=True, exist_ok=True)
    manifiesto = leer_manifiesto(dir_imagenes)
    salida, hechas, errores = [], 0, 0
    for origen, destino, estado in plan:
        if estado == "al-dia" and not forzar:
            continue
        try:
            with Image.open(origen) as im:
                im.seek(0)  # animaciones o TIFF de varias páginas: se usa el primer cuadro
                im = ImageOps.exif_transpose(im)
                ancho, alto = im.size
                escala = min(1.0, max_px / max(ancho, alto))
                if escala < 1.0:
                    im = im.resize((max(1, round(ancho * escala)), max(1, round(alto * escala))), Image.LANCZOS)
                if destino.suffix == ".jpg":
                    im.convert("RGB").save(destino, "JPEG", quality=85, optimize=True)
                else:
                    im.convert("RGBA" if "A" in im.getbands() else "RGB").save(destino, "PNG", optimize=True)
                nuevo = im.size
        except Exception as e:  # noqa: BLE001 - se informa cualquier fallo de Pillow
            salida.append(f"  ERROR {origen.name}: {str(e)[:120]}")
            errores += 1
            continue
        manifiesto[destino.name] = {"origen": origen.name, "sha256": hash_de(origen), "original_px": [ancho, alto],
                                    "px": list(nuevo), "reducida": escala < 1.0, "fecha": date.today().isoformat()}
        hechas += 1
        antes, despues = tokens_de_vision(ancho, alto), tokens_de_vision(*nuevo)
        if escala < 1.0:
            detalle = f"{ancho}x{alto} -> {nuevo[0]}x{nuevo[1]} (~{despues:,} tokens en vez de ~{antes:,})"
        else:
            detalle = f"{ancho}x{alto}, ya era chica (~{despues:,} tokens)"
        salida.append(f"  imagen: {origen.name} -> {destino.relative_to(raiz).as_posix()} {detalle}")
    (dir_imagenes / MANIFIESTO).write_text(json.dumps(manifiesto, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    salida.append(f"Imágenes: {hechas} procesadas, {errores} con error. Leer solo las copias de "
                  f"{dir_imagenes.relative_to(raiz).as_posix()}/ (máximo {max_px} px).")
    return (1 if errores else 0), salida


def procesar(archivos, imagenes, raiz, destino_dir, args, silencioso=False):
    """Convierte los documentos y reduce las imágenes. Devuelve (código, líneas)."""
    c1, l1 = convertir(plan_de_conversion(archivos, destino_dir), raiz, destino_dir, args.forzar, silencioso)
    c2, l2 = reducir_imagenes(plan_de_imagenes(imagenes, destino_dir), raiz, destino_dir, args.max_px, args.forzar, silencioso)
    return max(c1, c2), l1 + l2


def mostrar(lineas):
    if lineas:
        print("\n".join(lineas))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rutas", nargs="*", help=f"archivos o carpetas; por defecto, {CARPETA_ENTRADA}/")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--salida", default="docs/fuentes")
    ap.add_argument("--max-px", type=int, default=MAX_PX, help="lado más largo de las imágenes reducidas (1024 por defecto)")
    ap.add_argument("--forzar", action="store_true", help="reprocesar aunque el archivo no haya cambiado")
    ap.add_argument("--lista", action="store_true", help="solo mostrar qué se haría")
    ap.add_argument("--estado", action="store_true", help="mostrar qué está al día, pendiente o cambiado")
    ap.add_argument("--importar", nargs="+", metavar="ARCHIVO",
                    help=f"copiar estos archivos a {CARPETA_ENTRADA}/ y procesarlos (sin leer los originales)")
    ap.add_argument("--iniciar", action="store_true",
                    help=f"crear {CARPETA_ENTRADA}/ si falta y procesar lo pendiente; mudo si no hay nada que hacer")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    destino_dir = raiz / args.salida
    carpeta = raiz / CARPETA_ENTRADA

    if args.iniciar:
        if not es_proyecto(raiz):
            return 0
        if asegurar_carpeta(raiz):
            print(f"Fuentes: creé {CARPETA_ENTRADA}/. Los documentos e imágenes externos van ahí y no se leen directo: "
                  "se convierten o se reducen primero con convertir_fuentes.py.")
        archivos, imagenes, _, _ = recolectar([carpeta])
        codigo, lineas = procesar(archivos, imagenes, raiz, destino_dir, args, silencioso=True)
        mostrar(lineas)
        return codigo

    if args.importar:
        copiados, vectoriales, otros = importar(args.importar, raiz)
        for c in copiados:
            print(f"  copiado a {c.relative_to(raiz).as_posix()} (el original no se leyó)")
        if vectoriales:
            print(f"SVG ({len(vectoriales)}): es texto vectorial, no se reduce y se puede leer directo.")
        if otros:
            print("Formato sin soporte: " + ", ".join(o.name for o in otros[:5]) +
                  ". No se leen directo; avisar al usuario para decidir cómo pasarlos a texto.")
        if not copiados:
            return 0
        archivos, imagenes, _, _ = recolectar([carpeta])
        codigo, lineas = procesar(archivos, imagenes, raiz, destino_dir, args)
        mostrar(lineas)
        return codigo

    rutas = args.rutas or ([str(carpeta)] if carpeta.is_dir() else [])
    if not rutas:
        if args.lista or args.estado:
            print(f"Fuentes: no existe {CARPETA_ENTRADA}/ (nada que procesar).")
            return 0
        asegurar_carpeta(raiz)
        print(f"Fuentes: creé {CARPETA_ENTRADA}/. Dejar ahí los archivos y avisar; no se leen directo: se procesan primero.")
        return 0
    archivos, imagenes, vectoriales, otros = recolectar(rutas)
    if vectoriales:
        print(f"SVG ({len(vectoriales)}): es texto vectorial, no se reduce y se puede leer directo.")
    if otros:
        print(f"Formato sin soporte ({len(otros)}): " + ", ".join(o.name for o in otros[:5]) +
              ". No se leen directo; avisar al usuario para decidir cómo pasarlos a texto.")
    if not archivos and not imagenes:
        print("Fuentes: no hay documentos ni imágenes procesables en las rutas indicadas.")
        return 0
    if args.lista or args.estado:
        plan = plan_de_conversion(archivos, destino_dir) + plan_de_imagenes(imagenes, destino_dir)
        for origen, _, estado in plan:
            etiqueta = {"al-dia": "al día", "pendiente": "SIN PROCESAR", "cambiado": "CAMBIÓ (reprocesar)"}[estado]
            print(f"  {etiqueta}: {origen.name}")
        pendientes = sum(e != "al-dia" for _, _, e in plan)
        print(f"Fuentes: {len(plan)} archivos, {pendientes} por procesar (nada se escribió).")
        return 1 if args.estado and pendientes else 0
    codigo, lineas = procesar(archivos, imagenes, raiz, destino_dir, args)
    mostrar(lineas)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
