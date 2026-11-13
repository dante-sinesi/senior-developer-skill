#!/usr/bin/env python3
"""Abre un archivo local o una dirección web en el navegador, en UNA sola pestaña por destino.

Existe porque abrir archivos con comandos improvisados falla de una forma molesta: una ruta con espacios sin entrecomillar
se parte en pedazos y el navegador abre una pestaña por cada uno (con rutas como «Mis Documentos/Proyecto Nuevo» salen
cuatro o más). Acá la ruta nunca pasa por un intérprete de comandos: se convierte en una dirección `file:///…` con los
espacios codificados y se entrega como un único argumento.

Uso:
    python abrir_en_navegador.py <archivo-o-dirección> [<otro> …] [--simular]

  - Hasta 3 destinos por llamada: si hacen falta más, se abre un índice o una página que los reúna.
  - Un archivo local tiene que existir. Una dirección web debe empezar con http:// o https://.
  - Usa Edge o Chrome si están instalados (la misma búsqueda que `capturar.py` de Token Diet) y, si no, el
    navegador predeterminado.
  - Con --simular muestra qué abriría y no abre nada (sirve para probar).
Solo biblioteca estándar.
"""
import argparse
import json
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

MAX_DESTINOS = 3
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


def a_direccion(destino):
    """Dirección lista para el navegador (con los espacios codificados) o un mensaje de error."""
    if destino.lower().startswith(("http://", "https://")):
        return destino, None
    ruta = Path(destino.strip("\"'"))
    if not ruta.exists():
        return None, f"no existe: {destino}"
    return ruta.resolve().as_uri(), None


def abrir(direcciones, navegador):
    for d in direcciones:
        if navegador:
            subprocess.Popen([navegador, "--new-tab", d], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open_new_tab(d)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("destinos", nargs="+")
    ap.add_argument("--simular", action="store_true")
    args = ap.parse_args()
    if len(args.destinos) > MAX_DESTINOS:
        sys.exit(f"{len(args.destinos)} destinos: el máximo es {MAX_DESTINOS} por llamada. Si hay más, abrir una página índice que los reúna. "
                 "Si son pedazos de una sola ruta con espacios, entrecomillar la ruta completa.")
    direcciones = []
    for d in args.destinos:
        direccion, error = a_direccion(d)
        if error:
            sys.exit(error)
        direcciones.append(direccion)
    navegador = buscar_navegador()
    if args.simular:
        print(json.dumps({"navegador": navegador, "pestanas": direcciones}, ensure_ascii=False))
        return
    abrir(direcciones, navegador)
    for d in direcciones:
        print("Abierto en una pestaña: " + d)


if __name__ == "__main__":
    main()
