#!/usr/bin/env python3
"""Visor de propuestas: UNA página HTML para ver todas las propuestas de una carpeta en desktop, mobile o ambas a la vez, sin abrir archivo por archivo.

Sirve para las direcciones de una ronda de diseño, las pantallas conceptuales de una app y las imágenes o SVG de una comparación de estilos. No tiene estilo propio
del proyecto ni genera imágenes: muestra los HTML tal cual (en marcos de 1280 y 390 px, escalados al ancho de la ventana) y las imágenes o SVG que ya existan.

Uso:
    python ver_propuestas.py crear <carpeta> [--titulo T] [--modos desktop,mobile|desktop|mobile] [--manifiesto m.json] [--salida ver.html]
        Arma <carpeta>/ver.html (se puede volver a correr: se regenera). Sin manifiesto, agrupa los archivos por nombre.
    python ver_propuestas.py estado <carpeta>
        Lista qué propuestas tiene cada pantalla y cuáles están pendientes en algún modo.

Nombres de archivo (sin manifiesto):  [pantalla__]propuesta[__desktop|__mobile].html|svg|png|jpg|webp
    inicio__a.html                una propuesta «a» de la pantalla «inicio»; un mismo HTML responsivo se ve en los dos modos
    inicio__a__desktop.svg        la misma propuesta con una imagen por modo
    inicio__a__mobile.svg
    direccion-b.html              sin «pantalla__»: va a la pantalla «General»
Se ignoran comparar.html, los visores (ver.html, ver-*.html) y los que empiezan con «_».

Modos de la app (--modos): una app solo mobile (`--modos mobile`) o solo desktop (`--modos desktop`) bloquea el otro botón con un aviso y no marca nada como pendiente.
Si la app tiene los dos modos y a una propuesta le falta uno, el visor lo marca «pendiente» (la estructura para completarlo ya está: basta sumar el archivo `__mobile` o `__desktop`).

Manifiesto explícito (JSON):
    {"titulo": "…", "modos": ["desktop", "mobile"], "viewports": {"desktop": [1280, 800], "mobile": [390, 844]},
     "pantallas": [{"id": "inicio", "titulo": "Inicio", "propuestas": [{"id": "a", "titulo": "Dirección A", "archivo": "a.html"},
                                                                       {"id": "b", "titulo": "Dirección B", "desktop": "b-d.svg", "mobile": "b-m.svg"}]}]}
Solo biblioteca estándar.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLANTILLA = Path(__file__).resolve().parents[1] / "plantillas" / "visor-propuestas.html"
EXTENSIONES = {".html", ".htm", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
IGNORADOS = {"ver.html", "comparar.html"}
MODOS_VALIDOS = ("desktop", "mobile")


class VisorError(ValueError):
    pass


def bonito(texto):
    t = re.sub(r"[-_]+", " ", texto).strip()
    return (t[:1].upper() + t[1:]) if t else texto


def leer_modos(texto):
    modos = [m.strip() for m in texto.split(",") if m.strip()]
    if not modos or any(m not in MODOS_VALIDOS for m in modos):
        raise VisorError("--modos va con desktop, mobile o desktop,mobile")
    return list(dict.fromkeys(modos))


def manifiesto_de_carpeta(carpeta, titulo, modos):
    """Agrupa los archivos de la carpeta por pantalla y propuesta según su nombre."""
    pantallas = {}
    for f in sorted(carpeta.iterdir()):
        if not f.is_file() or f.suffix.lower() not in EXTENSIONES or f.name in IGNORADOS or f.name.startswith("_") or re.fullmatch(r"ver(-[\w-]+)?\.html", f.name):
            continue
        partes = f.stem.split("__")
        modo = partes.pop() if len(partes) > 1 and partes[-1] in MODOS_VALIDOS else None
        pantalla, propuesta = (partes[0], "__".join(partes[1:])) if len(partes) > 1 else ("general", partes[0])
        grupo = pantallas.setdefault(pantalla, {"id": pantalla, "titulo": bonito(pantalla) if pantalla != "general" else "General", "propuestas": {}})
        p = grupo["propuestas"].setdefault(propuesta, {"id": propuesta, "titulo": bonito(propuesta)})
        p[modo or "archivo"] = f.name
    if not pantallas:
        raise VisorError(f"No hay propuestas en {carpeta} (HTML, SVG o imágenes).")
    return {"titulo": titulo, "modos": modos,
            "pantallas": [{**g, "propuestas": list(g["propuestas"].values())} for g in pantallas.values()]}


def validar(m, carpeta):
    """(errores, pendientes): los archivos que no existen son errores; los modos sin propuesta, pendientes."""
    errores, pendientes = [], []
    if not m.get("pantallas"):
        raise VisorError("El manifiesto no tiene pantallas.")
    for modo in m.get("modos", []):
        if modo not in MODOS_VALIDOS:
            raise VisorError(f"modo desconocido: {modo}")
    ids = set()
    for pn in m["pantallas"]:
        if not pn.get("propuestas"):
            raise VisorError(f"la pantalla «{pn.get('titulo', pn.get('id'))}» no tiene propuestas")
        for p in pn["propuestas"]:
            clave = (pn.get("id"), p.get("id"))
            if clave in ids:
                raise VisorError(f"propuesta repetida: {clave[0]} / {clave[1]}")
            ids.add(clave)
            for campo in ("archivo", "desktop", "mobile"):
                if p.get(campo) and not (carpeta / p[campo]).is_file():
                    errores.append(f"{pn.get('titulo')} / {p.get('titulo')}: no existe {p[campo]}")
            for modo in m.get("modos", []):
                if not (p.get(modo) or p.get("archivo")):
                    pendientes.append(f"{pn.get('titulo')} / {p.get('titulo')}: falta {modo}")
    return errores, pendientes


def pagina(m):
    texto = PLANTILLA.read_text(encoding="utf-8")
    datos = json.dumps(m, ensure_ascii=False).replace("</", "<\\/")
    return texto.replace("{{titulo}}", re.sub(r"[<>&\"]", "", m["titulo"])).replace("{{manifiesto}}", datos)


def crear(carpeta, titulo=None, modos=("desktop", "mobile"), manifiesto=None, salida="ver.html"):
    """Escribe <carpeta>/<salida>. Devuelve (ruta, pendientes). Lanza VisorError si algo no cuadra."""
    carpeta = Path(carpeta).resolve()
    if not carpeta.is_dir():
        raise VisorError(f"No existe la carpeta: {carpeta}")
    if manifiesto:
        m = json.loads(Path(manifiesto).read_text(encoding="utf-8-sig"))
        m.setdefault("titulo", titulo or carpeta.name)
        m.setdefault("modos", list(modos))
    else:
        m = manifiesto_de_carpeta(carpeta, titulo or bonito(carpeta.name), list(modos))
    errores, pendientes = validar(m, carpeta)
    if errores:
        raise VisorError("; ".join(errores))
    ruta = carpeta / salida
    ruta.write_text(pagina(m), encoding="utf-8", newline="\n")
    return ruta, pendientes


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["crear", "estado"])
    ap.add_argument("carpeta")
    ap.add_argument("--titulo")
    ap.add_argument("--modos", default="desktop,mobile")
    ap.add_argument("--manifiesto")
    ap.add_argument("--salida", default="ver.html")
    a = ap.parse_args()
    try:
        modos = leer_modos(a.modos)
        if a.accion == "estado":
            m = manifiesto_de_carpeta(Path(a.carpeta).resolve(), a.titulo or "", modos)
            _, pendientes = validar(m, Path(a.carpeta).resolve())
            for pn in m["pantallas"]:
                print(f"{pn['titulo']}: " + ", ".join(p["titulo"] for p in pn["propuestas"]))
            print("Pendientes: " + ("; ".join(pendientes) if pendientes else "ninguno"))
            return
        ruta, pendientes = crear(a.carpeta, a.titulo, modos, a.manifiesto, a.salida)
    except VisorError as e:
        sys.exit(f"Error: {e}")
    print(f"Visor listo: {ruta}")
    if pendientes:
        print("Pendientes (se ven marcados en el visor): " + "; ".join(pendientes))
    print("Abrirlo en una sola pestaña con: python <senior>/scripts/abrir_en_navegador.py " + str(ruta))


if __name__ == "__main__":
    main()
