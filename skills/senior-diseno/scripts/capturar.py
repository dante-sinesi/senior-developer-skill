#!/usr/bin/env python3
"""Saca capturas de pantalla (PNG) de un HTML para mirarlas antes de entregar.

Uso:
    python capturar.py <archivo.html> [--salida carpeta] [--desktop 1280x800] [--mobile 390x844] [--pagina-completa]
                       [--max-px 1024]

Escribe <nombre>-desktop.png y <nombre>-mobile.png (por defecto junto al archivo, en capturas/). Los navegadores sin
interfaz no bajan de unos 500 px de ancho: en mobile la página se mide a 390 px dentro de un marco gris.
Usa el Edge o el Chrome que ya estén instalados, en modo sin interfaz; no descarga nada. Si no encuentra ninguno,
lo dice y sale con código 2: en ese caso se usa el navegador integrado de la herramienta o se declara que el
diseño no se vio renderizado. Las capturas se leen con la herramienta de lectura de imágenes.
Las capturas se reducen a un máximo de --max-px píxeles en el lado más largo (1024 por defecto: ahorra tokens al
leerlas, y la regla de imágenes del paquete senior no deja leer las más grandes) si está `Pillow` instalada.
Solo biblioteca estándar (Pillow es opcional aquí).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATOS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
EN_PATH = ["msedge", "microsoft-edge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]


def buscar_navegador():
    for c in CANDIDATOS:
        if Path(c).exists():
            return c
    for n in EN_PATH:
        r = shutil.which(n)
        if r:
            return r
    return None


ENVOLTURA = ("<!doctype html><meta charset=utf-8><body style='margin:0;background:#888'>"
             "<iframe src='{url}' style='border:0;background:#fff;display:block;width:{ancho}px;height:{alto}px'></iframe>")


def tamano(texto):
    ancho, alto = texto.lower().split("x")
    return int(ancho), int(alto)


def capturar(navegador, url, salida, ancho, alto):
    perfil = tempfile.mkdtemp()
    try:
        cmd = [navegador, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               f"--user-data-dir={perfil}", f"--window-size={ancho},{alto}", "--virtual-time-budget=3000",
               f"--screenshot={salida}", url]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    except subprocess.TimeoutExpired:
        pass
    finally:  # en Windows el navegador puede tardar en soltar el perfil: no se falla por eso
        shutil.rmtree(perfil, ignore_errors=True)
    return Path(salida).exists()


def reducir(ruta, max_px):
    """Reduce la imagen en el lugar a max_px en el lado más largo. Sin Pillow no hace nada."""
    try:
        from PIL import Image
    except ImportError:
        return False
    with Image.open(ruta) as im:
        ancho, alto = im.size
        if max(ancho, alto) <= max_px:
            return True
        k = max_px / max(ancho, alto)
        chica = im.resize((max(1, round(ancho * k)), max(1, round(alto * k))), Image.LANCZOS)
    chica.save(ruta)
    return True


def capturar_archivo(origen, carpeta=None, desktop="1280x800", mobile="390x844", pagina_completa=False, max_px=1024):
    """Devuelve la lista de PNG creados (desktop y mobile). Lanza RuntimeError si no hay navegador."""
    origen = Path(origen).resolve()
    navegador = buscar_navegador()
    if not navegador:
        raise RuntimeError("No se encontró Edge ni Chrome instalados: no se pueden sacar capturas.")
    carpeta = Path(carpeta) if carpeta else origen.parent / "capturas"
    carpeta.mkdir(parents=True, exist_ok=True)
    url = origen.as_uri() + "?solo=1"  # sin la barra de vistas de los bosquejos
    creados = []
    for nombre, medida in (("desktop", desktop), ("mobile", mobile)):
        ancho, alto = tamano(medida)
        if pagina_completa:
            alto = max(alto, 3000)
        destino = carpeta / f"{origen.stem}-{nombre}.png"
        objetivo, envuelto = url, False
        if ancho < 500:  # Edge y Chrome sin interfaz no bajan de unos 500 px: se mide el ancho real dentro de un marco
            marco = Path(tempfile.mkdtemp()) / "marco.html"
            marco.write_text(ENVOLTURA.format(url=url, ancho=ancho, alto=alto), encoding="utf-8")
            objetivo, envuelto = marco.as_uri(), True
        if capturar(navegador, objetivo, str(destino), max(ancho, 500) if envuelto else ancho, alto):
            if max_px:
                reducir(destino, max_px)
            creados.append(destino)
    return creados


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--salida")
    ap.add_argument("--desktop", default="1280x800")
    ap.add_argument("--mobile", default="390x844")
    ap.add_argument("--pagina-completa", action="store_true", help="altura 3000 px en lugar de la del viewport")
    ap.add_argument("--max-px", type=int, default=1024, help="lado más largo de las capturas (0 = sin reducir)")
    args = ap.parse_args()
    if not Path(args.archivo).is_file():
        sys.exit(f"No existe: {args.archivo}")
    try:
        creados = capturar_archivo(args.archivo, args.salida, args.desktop, args.mobile, args.pagina_completa, args.max_px)
    except RuntimeError as e:
        print(e)
        sys.exit(2)
    for c in creados:
        print("Captura:", c)
    if len(creados) < 2:
        print("No se pudieron sacar todas las capturas. Probar desde otra terminal (algunos entornos restringidos "
              "no dejan lanzar el navegador) o abrir el archivo en el navegador integrado; si no se vio, declararlo.")
    sys.exit(0 if len(creados) == 2 else 1)


if __name__ == "__main__":
    main()
