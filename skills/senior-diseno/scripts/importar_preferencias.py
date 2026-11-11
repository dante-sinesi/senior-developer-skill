#!/usr/bin/env python3
"""Copia las preferencias de diseño de otro proyecto a este, cuando el usuario lo pide.

Uso:
    python importar_preferencias.py <carpeta_del_otro_proyecto> [--raiz .] [--solo aprobados|rechazados]
    python importar_preferencias.py --listar [--raiz .]

Lee <otro>/diseno/notas/preferencias.md y agrega a <raiz>/diseno/notas/preferencias.md las líneas
que todavía no estén (compara el texto del patrón sin distinguir mayúsculas). Cada línea importada
queda marcada con su origen y la fecha. No modifica el otro proyecto ni nada fuera de docs/diseno/.
Las preferencias son datos del usuario: se copian solo cuando él lo pide. Solo biblioteca estándar.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

SECCIONES = {"aprobados": "## Aprobados", "rechazados": "## Rechazados"}
PLANTILLA = Path(__file__).resolve().parents[1] / "plantillas" / "preferencias.md"


def leer_secciones(ruta):
    """Devuelve {'aprobados': [lineas], 'rechazados': [lineas]} de un archivo de preferencias."""
    res = {"aprobados": [], "rechazados": []}
    if not ruta.exists():
        return res
    actual = None
    for linea in ruta.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = linea.strip().lower()
        if s.startswith("## aprobados"):
            actual = "aprobados"
        elif s.startswith("## rechazados"):
            actual = "rechazados"
        elif s.startswith("## "):
            actual = None
        elif actual and re.match(r"^\s*-\s+\S", linea) and "(ejemplo)" not in linea.lower():
            res[actual].append(linea.rstrip())
    return res


def clave(linea):
    patron = re.sub(r"^\s*-\s*", "", linea)
    patron = re.split(r"\s+[—–-]\s+", patron, maxsplit=1)[0]
    return re.sub(r"\W+", " ", patron.lower()).strip()


def insertar(texto, seccion, lineas):
    encabezado = SECCIONES[seccion]
    partes = texto.split("\n")
    try:
        i = next(k for k, l in enumerate(partes) if l.strip().lower().startswith(encabezado.lower()))
    except StopIteration:
        return texto.rstrip("\n") + f"\n\n{encabezado}\n" + "\n".join(lineas) + "\n"
    j = i + 1
    while j < len(partes) and not partes[j].strip().startswith("## "):
        j += 1
    while j > i + 1 and not partes[j - 1].strip():
        j -= 1
    partes[j:j] = lineas
    return "\n".join(partes)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origen", nargs="?")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--solo", choices=["aprobados", "rechazados"])
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    destino = raiz / "docs" / "diseno" / "notas" / "preferencias.md"
    if args.listar:
        datos = leer_secciones(destino)
        for k in ("aprobados", "rechazados"):
            print(f"{k.capitalize()} ({len(datos[k])}):")
            for l in datos[k]:
                print(f"  {l.strip()}")
        return
    if not args.origen:
        ap.error("indicar la carpeta del otro proyecto (o --listar)")
    origen = Path(args.origen).resolve() / "docs" / "diseno" / "notas" / "preferencias.md"
    if not origen.exists():
        sys.exit(f"No hay preferencias en {origen}.")
    fuente = leer_secciones(origen)
    existente = leer_secciones(destino)
    texto = destino.read_text(encoding="utf-8-sig", errors="replace") if destino.exists() else PLANTILLA.read_text(encoding="utf-8")
    nombre_origen = Path(args.origen).resolve().name
    agregadas = 0
    for seccion in ("aprobados", "rechazados"):
        if args.solo and args.solo != seccion:
            continue
        ya = {clave(l) for l in existente["aprobados"] + existente["rechazados"]}
        nuevas = []
        for l in fuente[seccion]:
            if clave(l) not in ya:
                nuevas.append(f"{l.rstrip()} [importado de {nombre_origen}, {date.today().isoformat()}]")
                ya.add(clave(l))
        if nuevas:
            texto = insertar(texto, seccion, nuevas)
            agregadas += len(nuevas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto if texto.endswith("\n") else texto + "\n", encoding="utf-8", newline="\n")
    print(f"Preferencias: {agregadas} líneas importadas de {nombre_origen} a {destino.relative_to(raiz).as_posix()}.")


if __name__ == "__main__":
    main()
