#!/usr/bin/env python3
"""Configuración de los hooks de senior: cómo responden y qué rutas están autorizadas de antemano. La usa el USUARIO.

Cuando Claude trabaja horas sin supervisión, una pregunta en la interfaz frena todo hasta que alguien responde. Por eso los
hooks que preguntaban (escritura fuera del proyecto, archivos protegidos, lectura directa de documentos externos) tienen dos
modos (ver modo_hooks.py): «denegar» (por defecto, no interrumpe: bloquea, le explica a Claude qué hacer y deja registro) y
«preguntar» (pregunta y espera).

Uso, desde la terminal del usuario (Claude no puede ejecutar los subcomandos que cambian algo: los hooks lo deniegan):
    python permisos_hooks.py estado   [--raiz .]          # modo, rutas autorizadas y lo último que se bloqueó
    python permisos_hooks.py bloqueos [--raiz .]          # lo bloqueado, para decidir si autorizar algo
    python permisos_hooks.py modo denegar|preguntar       [--raiz .]
    python permisos_hooks.py permitir <ruta> [--motivo "…"]   # autoriza de antemano una ruta (o una carpeta con todo lo que contiene)
    python permisos_hooks.py hermanos si|no               # escribir en otros proyectos tuyos de la misma carpeta (por defecto sí)
    python permisos_hooks.py quitar <ruta>
    python permisos_hooks.py limpiar                      # borra el registro de bloqueos
Desde el chat, sin terminal: escribir `/permitir <ruta>`, `/quitar-permiso <ruta>`, `/hooks-modo denegar|preguntar`, `/hooks-hermanos si|no` o
`/permisos` (lo recoge `hook_permisos_chat.py`, que solo actúa con lo que el usuario escribe: Claude no puede usarlo).
La configuración es por proyecto y vive en `.git/senior-hooks.json` (no se sube). Solo biblioteca estándar.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modo_hooks as mh  # noqa: E402 motivo: sys.path se ajusta justo antes de importarlo


def raiz_de(args):
    return Path(args.raiz).resolve()


def mostrar(raiz):
    d = mh.cargar(raiz)
    print(f"Modo: {d['modo']}" + (" (no interrumpe: bloquea, avisa a Claude y deja registro)" if d["modo"] == "denegar" else " (pregunta y espera tu respuesta)"))
    print("Proyectos hermanos (otros repositorios de la misma carpeta): " + ("permitidos" if d["hermanos"] else "no permitidos"))
    if d["permitidos"]:
        print("Autorizado de antemano:")
        for p in d["permitidos"]:
            ruta, motivo = (p["ruta"], p.get("motivo", "")) if isinstance(p, dict) else (p, "")
            print(f"  - {ruta}" + (f" — {motivo}" if motivo else ""))
    else:
        print("Autorizado de antemano: nada.")
    print(f"Bloqueos registrados: {len(d['bloqueos'])} (`bloqueos` los lista).")


def cmd_estado(args):
    mostrar(raiz_de(args))
    print(f"Configuración: {mh.ruta_config(raiz_de(args))}")


def cmd_bloqueos(args):
    d = mh.cargar(raiz_de(args))
    if not d["bloqueos"]:
        print("No se bloqueó nada desde la última vez.")
        return
    print("Lo que se bloqueó (para decidir si autorizar algo con `permitir <ruta>`):")
    for b in d["bloqueos"]:
        veces = int(b.get("veces", 1))
        print(f"  - [{b['hook']}] {b['detalle']}" + (f" (×{veces}{', reincide' if veces >= mh.ESCALA else ''})" if veces > 1 else ""))


def cmd_modo(args):
    raiz = raiz_de(args)
    d = mh.cargar(raiz)
    d["modo"] = args.modo
    mh.guardar(raiz, d)
    print(f"Modo: {args.modo}.")


def cmd_permitir(args):
    ok, mensaje = mh.permitir_ruta(raiz_de(args), args.ruta, args.motivo)
    print(mensaje)
    sys.exit(0 if ok else 1)


def cmd_hermanos(args):
    raiz = raiz_de(args)
    d = mh.cargar(raiz)
    d["hermanos"] = args.valor == "si"
    mh.guardar(raiz, d)
    print("Proyectos hermanos: " + ("permitidos." if d["hermanos"] else "no permitidos."))


def cmd_quitar(args):
    raiz = raiz_de(args)
    ruta = Path(args.ruta)
    ruta = ruta if ruta.is_absolute() else raiz / ruta
    d = mh.cargar(raiz)
    antes = len(d["permitidos"])
    d["permitidos"] = [p for p in d["permitidos"] if mh.normal(p["ruta"] if isinstance(p, dict) else p) != mh.normal(ruta)]
    mh.guardar(raiz, d)
    print("Quitada." if len(d["permitidos"]) < antes else "No estaba en la lista.")


def cmd_limpiar(args):
    raiz = raiz_de(args)
    d = mh.cargar(raiz)
    d["bloqueos"] = []
    mh.guardar(raiz, d)
    print("Registro de bloqueos vaciado.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    for nombre in ("estado", "bloqueos", "limpiar"):
        sub.add_parser(nombre).add_argument("--raiz", default=".")
    m = sub.add_parser("modo")
    m.add_argument("modo", choices=mh.MODOS)
    m.add_argument("--raiz", default=".")
    h = sub.add_parser("hermanos")
    h.add_argument("valor", choices=["si", "no"])
    h.add_argument("--raiz", default=".")
    p = sub.add_parser("permitir")
    p.add_argument("ruta")
    p.add_argument("--motivo", default="")
    p.add_argument("--raiz", default=".")
    q = sub.add_parser("quitar")
    q.add_argument("ruta")
    q.add_argument("--raiz", default=".")
    args = ap.parse_args()
    {"estado": cmd_estado, "bloqueos": cmd_bloqueos, "modo": cmd_modo, "permitir": cmd_permitir, "hermanos": cmd_hermanos, "quitar": cmd_quitar, "limpiar": cmd_limpiar}[args.orden](args)


if __name__ == "__main__":
    main()
