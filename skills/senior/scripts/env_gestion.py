#!/usr/bin/env python3
"""Estructura y variables nuevas de `.env`, sin que Claude vea los valores y con permiso del usuario para tocar `.env`.

Un `.env` tiene secretos: leerlo pone las claves en el contexto y en el historial de la sesión, y escribirlo mal las pierde. Por
eso los hooks de senior frenan que Claude lo lea o lo edite, salvo que el usuario lo autorice de antemano. Este script es la vía
normal para el trabajo de todos los días: Claude necesita saber qué variables hay o declarar una nueva, y lo hace sin leer valores.

Uso:
    python env_gestion.py estructura [--raiz .]
        # los nombres de las variables de `.env` y de `.env.example`, con los valores ocultos, y lo que falta en cada uno
    python env_gestion.py declarar NOMBRE [NOMBRE …] [--ejemplo "valor falso"] [--comentario "para qué sirve"] [--raiz .]
        # agrega la variable a `.env.example` (siempre; es un archivo de ejemplo que se sube, con un valor falso) y, si el
        # usuario autorizó `.env` (`/permitir .env`), también a `.env` con el valor vacío para que lo complete él

El valor real de un secreto lo escribe el usuario en `.env`; Claude no lo necesita. Si `.env` no está autorizado, el script lo
dice y Claude le propone al usuario las variables (nombre y para qué sirven) y cómo autorizar. Solo biblioteca estándar.
"""
import argparse
import re
import sys
from pathlib import Path

NOMBRE_VALIDO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ASIGNACION = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")
EJEMPLO_POR_DEFECTO = "cambiar_este_valor"


def leer_variables(ruta):
    """{nombre: tiene_valor} en el orden del archivo; nunca devuelve un valor."""
    res = {}
    if ruta.exists():
        for l in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
            m = ASIGNACION.match(l)
            if m:
                res[m.group(1)] = bool(m.group(2).strip().strip("\"'"))
    return res


def esta_autorizado(raiz, archivo):
    """True si el usuario autorizó de antemano `.env` (`/permitir .env`)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import modo_hooks
    return modo_hooks.esta_permitido(modo_hooks.raiz_del_proyecto(str(raiz)), archivo) or modo_hooks.esta_permitido(raiz, archivo)


def agregar(ruta, nombres, valor, comentario):
    previo = ruta.read_text(encoding="utf-8", errors="replace") if ruta.exists() else ""
    existentes = set(leer_variables(ruta))
    nuevos = [n for n in nombres if n not in existentes]
    if not nuevos:
        return []
    bloque = ("" if not previo or previo.endswith("\n") else "\n") + ("\n" if previo else "")
    if comentario:
        bloque += f"# {comentario}\n"
    bloque += "".join(f"{n}={valor}\n" for n in nuevos)
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        f.write(bloque)
    return nuevos


def cmd_estructura(raiz):
    env, ejemplo = leer_variables(raiz / ".env"), leer_variables(raiz / ".env.example")
    if not env and not ejemplo:
        print("No hay `.env` ni `.env.example` con variables.")
        return 0
    print(f".env: {len(env)} variables" + ("" if (raiz / ".env").exists() else " (el archivo no existe)"))
    for n, lleno in env.items():
        print(f"  {n} = {'***' if lleno else '(vacía)'}")
    print(f".env.example: {len(ejemplo)} variables")
    for n in ejemplo:
        print(f"  {n}")
    sin_ejemplo, sin_env = [n for n in env if n not in ejemplo], [n for n in ejemplo if n not in env]
    if sin_ejemplo:
        print(f"Falta declarar en .env.example: {', '.join(sin_ejemplo)}  (`env_gestion.py declarar`)")
    if sin_env:
        print(f"Falta en .env: {', '.join(sin_env)}")
    return 0


def cmd_declarar(raiz, nombres, ejemplo, comentario):
    invalidos = [n for n in nombres if not NOMBRE_VALIDO.match(n)]
    if invalidos:
        print(f"Nombres inválidos: {', '.join(invalidos)} (letras, números y guion bajo; no empiezan con número).")
        return 1
    nuevos_ej = agregar(raiz / ".env.example", nombres, ejemplo, comentario)
    print(f".env.example: " + (f"se agregó {', '.join(nuevos_ej)} con el valor falso «{ejemplo}»." if nuevos_ej else "ya tenía esas variables."))
    destino = raiz / ".env"
    if esta_autorizado(raiz, destino):
        nuevos_env = agregar(destino, nombres, "", comentario)
        print(".env: " + (f"se agregó {', '.join(nuevos_env)} sin valor; que lo complete el usuario." if nuevos_env else "ya tenía esas variables."))
    else:
        faltan = [n for n in nombres if n not in leer_variables(destino)]
        if faltan:
            print(f".env no está autorizado, así que no se tocó. Proponerle al usuario: «Para esta funcionalidad hace falta declarar en .env "
                  f"{', '.join(faltan)}"
                  + (f" ({comentario})" if comentario else "") + ". Si querés que lo agregue yo, escribí en el chat `/permitir .env`; "
                  "el valor real lo completás vos». Si se trabaja sin supervisión, anotarlo en `docs/pendientes.md` y seguir.")
    return 0


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["estructura", "declarar"])
    ap.add_argument("nombres", nargs="*")
    ap.add_argument("--ejemplo", default=EJEMPLO_POR_DEFECTO)
    ap.add_argument("--comentario", default="")
    ap.add_argument("--raiz", default=".")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if args.accion == "estructura":
        return cmd_estructura(raiz)
    if not args.nombres:
        print("Falta al menos un NOMBRE de variable.")
        return 1
    return cmd_declarar(raiz, args.nombres, args.ejemplo, args.comentario)


if __name__ == "__main__":
    sys.exit(main())
