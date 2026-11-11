#!/usr/bin/env python3
"""Registro de atajos: junta los comentarios `atajo:` del código en una sola lista para que "después" no se vuelva "nunca".

Un atajo es una simplificación deliberada con un límite conocido. Se marca en el código con un comentario de una línea:

    # atajo: lee todo el archivo en memoria; cuándo: si pasa de 50 MB
    // atajo: sin paginación, 200 filas como máximo; cuándo: cuando haya más de 200 clientes

El formato es `atajo: <el límite>; cuándo: <qué lo haría insuficiente y obliga a mejorarlo>`. Un atajo sin «cuándo:»
no tiene disparador: se pudre sin que nadie lo note, y se marca SIN DISPARADOR.

Uso:
    python atajos.py [--raiz .] [--escribir]
        Lista cada atajo (archivo:línea, límite y disparador). Con --escribir deja la lista en docs/atajos.md, que es
        una vista generada: la fuente son los comentarios del código y ahí se editan.
Es solo lectura salvo con --escribir. Solo biblioteca estándar.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seguridad  # noqa: E402

EXT_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".kt", ".cs", ".go", ".rs", ".rb", ".sh", ".sql",
              ".c", ".cpp", ".h", ".swift", ".lua", ".pl", ".r", ".vue", ".svelte"}
MARCA = re.compile(r"(?:#|//|/\*|--|<!--|;)\s*atajo\s*:\s*(.+?)\s*(?:\*/|-->)?\s*$", re.IGNORECASE)
DISPARADOR = re.compile(r"[;,.]?\s*cu[aá]ndo\s*:\s*(.+)$", re.IGNORECASE)


def recolectar(raiz):
    """Lista de dicts {archivo, linea, limite, cuando} de todos los atajos marcados en el código."""
    atajos = []
    for ruta, texto in seguridad.archivos_de_texto(raiz):
        if ruta.suffix.lower() not in EXT_CODIGO or ruta.name == "atajos.py":  # su propia documentación trae ejemplos
            continue
        try:
            rel = ruta.relative_to(raiz).as_posix()
        except ValueError:
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            m = MARCA.search(linea)
            if not m:
                continue
            cuerpo = m.group(1)
            d = DISPARADOR.search(cuerpo)
            limite = (cuerpo[:d.start()] if d else cuerpo).strip(" ;,.")
            atajos.append({"archivo": rel, "linea": n, "limite": limite, "cuando": d.group(1).strip() if d else ""})
    return sorted(atajos, key=lambda a: (a["archivo"], a["linea"]))


def lineas_del_registro(atajos):
    if not atajos:
        return ["Atajos: no hay ninguno marcado con `atajo:`."]
    res = []
    for a in atajos:
        cuando = f"cuándo: {a['cuando']}" if a["cuando"] else "SIN DISPARADOR"
        res.append(f"  {a['archivo']}:{a['linea']} — {a['limite'] or '(sin límite escrito)'}. {cuando}")
    sin = sum(1 for a in atajos if not a["cuando"])
    res.append(f"Atajos: {len(atajos)} marcados, {sin} sin disparador.")
    return res


def escribir_registro(raiz, atajos):
    destino = raiz / "docs" / "atajos.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    filas = ["| Dónde | Límite | Cuándo mejorarlo |", "|---|---|---|"]
    for a in atajos:
        filas.append(f"| `{a['archivo']}:{a['linea']}` | {a['limite'] or '(sin límite escrito)'} | {a['cuando'] or '**SIN DISPARADOR**'} |")
    if not atajos:
        filas = ["No hay atajos marcados en el código."]
    texto = ("# Atajos del código\n\nVista generada por `atajos.py`: la fuente son los comentarios `atajo:` del código; "
             "se editan ahí, no en este archivo.\n\n" + "\n".join(filas) + "\n")
    destino.write_text(texto, encoding="utf-8", newline="\n")
    return destino.relative_to(raiz).as_posix()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--escribir", action="store_true", help="dejar la lista en docs/atajos.md")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    atajos = recolectar(raiz)
    print("\n".join(lineas_del_registro(atajos)))
    if args.escribir:
        print(f"Registro escrito en {escribir_registro(raiz, atajos)}.")
    return 1 if any(not a["cuando"] for a in atajos) else 0


if __name__ == "__main__":
    sys.exit(main())
