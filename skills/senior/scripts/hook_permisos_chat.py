#!/usr/bin/env python3
"""Hook de Claude Code (UserPromptSubmit): permite configurar los hooks de senior desde el chat, sin terminal ni reiniciar.

Los hooks de senior frenan lo que sale de la regla (escribir fuera del proyecto, editar secretos, leer documentos sin
convertir) y Claude no puede cambiar esa configuración para no autorizarse solo. Este hook cubre el otro lado: un evento
UserPromptSubmit solo se dispara con lo que el USUARIO escribe, así que lo que se escribe acá no lo puede falsificar Claude.

Comandos (una línea que empiece así; el resto del mensaje sigue su curso normal):
    /permitir <ruta> [-- motivo]        autoriza de antemano una carpeta (y todo lo que contiene); entre comillas si tiene espacios
    /quitar-permiso <ruta>              la revoca
    /hooks-modo denegar|preguntar       «denegar» no interrumpe (por defecto); «preguntar» pregunta y espera
    /hooks-hermanos si|no               escribir o no en otros proyectos tuyos de la misma carpeta (por defecto sí)
    /permisos                           muestra lo configurado y lo último que se bloqueó

No autoriza raíces de disco, la carpeta del usuario ni rutas casi en la raíz. Responde con un mensaje que Claude ve como
contexto del mensaje del usuario. Si algo falla, no frena nada. Solo biblioteca estándar.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

COMANDO = re.compile(r"^\s*/(permitir|quitar-permiso|hooks-modo|hooks-hermanos|permisos)\b\s*(.*)$", re.IGNORECASE)


def separar_ruta_y_motivo(resto):
    """(ruta, motivo) de «"C:\\mi carpeta" motivo» o «C:\\carpeta -- motivo»."""
    resto = resto.strip()
    if resto and resto[0] in "\"'":
        cierre = resto.find(resto[0], 1)
        if cierre > 0:
            return resto[1:cierre], resto[cierre + 1:].strip(" -—:")
    partes = re.split(r"\s+(?:--|—)\s+", resto, maxsplit=1)
    return partes[0].strip(), (partes[1].strip() if len(partes) > 1 else "")


def aplicar(mh, raiz, orden, resto):
    orden = orden.lower()
    if orden == "permitir":
        ruta, motivo = separar_ruta_y_motivo(resto)
        if not ruta:
            return "Falta la ruta: /permitir <ruta> [-- motivo]."
        return mh.permitir_ruta(raiz, ruta, motivo)[1]
    if orden == "quitar-permiso":
        ruta, _ = separar_ruta_y_motivo(resto)
        destino = Path(ruta)
        destino = destino if destino.is_absolute() else Path(raiz) / destino
        d = mh.cargar(raiz)
        antes = len(d["permitidos"])
        d["permitidos"] = [p for p in d["permitidos"] if mh.normal(p["ruta"] if isinstance(p, dict) else p) != mh.normal(destino)]
        mh.guardar(raiz, d)
        return "Permiso quitado." if len(d["permitidos"]) < antes else "Esa ruta no estaba autorizada."
    if orden == "hooks-modo":
        valor = resto.strip().lower()
        if valor not in mh.MODOS:
            return "Modos válidos: denegar o preguntar."
        d = mh.cargar(raiz)
        d["modo"] = valor
        mh.guardar(raiz, d)
        return f"Modo de los hooks: {valor}."
    if orden == "hooks-hermanos":
        valor = resto.strip().lower()
        if valor not in ("si", "sí", "no"):
            return "Valores válidos: si o no."
        d = mh.cargar(raiz)
        d["hermanos"] = valor != "no"
        mh.guardar(raiz, d)
        return "Proyectos hermanos: " + ("permitidos." if d["hermanos"] else "no permitidos.")
    d = mh.cargar(raiz)
    permitidos = ", ".join((p["ruta"] if isinstance(p, dict) else p) for p in d["permitidos"]) or "ninguna"
    ultimos = "; ".join(f"[{b['hook']}] {b['detalle']}" for b in d["bloqueos"][-5:]) or "nada"
    return (f"Modo: {d['modo']}. Proyectos hermanos: {'sí' if d['hermanos'] else 'no'}. Rutas autorizadas: {permitidos}. "
            f"Últimos bloqueos: {ultimos}.")


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        lineas = str(datos.get("prompt") or "").splitlines()
        comandos = [m for m in (COMANDO.match(l) for l in lineas) if m]
        if not comandos:
            return 0
        import modo_hooks as mh
        raiz = mh.raiz_del_proyecto(datos.get("cwd") or os.getcwd())
        respuestas = [aplicar(mh, raiz, m.group(1), m.group(2)) for m in comandos]
    except Exception:  # noqa: BLE001 motivo: si algo falla, el mensaje del usuario sigue su curso
        return 0
    contexto = ("senior (hook de permisos, ejecutado por lo que escribió el usuario): " + " ".join(respuestas) +
                " Confirmalo en una línea y seguí con el resto del mensaje.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": contexto}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
