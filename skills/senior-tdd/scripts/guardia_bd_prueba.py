#!/usr/bin/env python3
"""Guardia: impide correr tests contra una base de datos que no sea de prueba.

Uso:
    python guardia_bd_prueba.py [--nombre NOMBRE | --url URL | --variable VAR]
    python guardia_bd_prueba.py -- <comando de tests ...>

Comprueba el NOMBRE de la base de datos (o el de la URL de conexión) y se niega
a continuar si no parece de prueba, es decir, si no contiene alguna de las
marcas: test, prueba, testing, tmp, ci. Con "--" ejecuta el comando de tests
solo si la comprobación pasó.

Ejemplos:
    python guardia_bd_prueba.py --variable DB_NAME -- vendor/bin/phpunit
    python guardia_bd_prueba.py --url mysql://usuario@localhost/tienda_test

Es una red de seguridad: la base de prueba debe tener un nombre que lo diga.
Códigos de salida: 0 permitido, 2 bloqueado. Solo biblioteca estándar.
"""
import argparse
import os
import re
import subprocess
import sys
from urllib.parse import urlparse

MARCAS = ("test", "prueba", "testing", "tmp", "ci")
MARCAS_PELIGRO = ("prod", "produccion", "production", "live")


def nombre_desde_url(url):
    if ":memory:" in url:
        return "test_memoria"
    analizada = urlparse(url)
    ruta = analizada.path.lstrip("/")
    return ruta or os.path.basename(url)


def es_de_prueba(nombre):
    n = nombre.lower()
    if any(p in n for p in MARCAS_PELIGRO):
        return False
    partes = re.split(r"[^a-z0-9]+", n)
    return any(m in n for m in ("test", "prueba")) or any(p in MARCAS for p in partes)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    comando = []
    argv = sys.argv[1:]
    if "--" in argv:
        i = argv.index("--")
        argv, comando = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre")
    ap.add_argument("--url")
    ap.add_argument("--variable", help="variable de entorno con el nombre o la URL de la base")
    args = ap.parse_args(argv)
    origen = None
    if args.nombre:
        nombre, origen = args.nombre, "--nombre"
    elif args.url:
        nombre, origen = nombre_desde_url(args.url), "--url"
    elif args.variable:
        valor = os.environ.get(args.variable, "")
        if not valor:
            print(f"BLOQUEADO: la variable {args.variable} no está definida; no se sabe contra qué base se probaría.")
            sys.exit(2)
        nombre = nombre_desde_url(valor) if "://" in valor else valor
        origen = f"variable {args.variable}"
    else:
        ap.error("indicar --nombre, --url o --variable")
    if not es_de_prueba(nombre):
        print(f"BLOQUEADO: la base '{nombre}' ({origen}) no parece de prueba. "
              f"Su nombre debe incluir 'test' o 'prueba'. Nunca se prueba contra desarrollo ni producción.")
        sys.exit(2)
    print(f"Guardia: la base '{nombre}' es de prueba; se permite continuar.")
    if comando:
        sys.exit(subprocess.call(comando))


if __name__ == "__main__":
    main()
