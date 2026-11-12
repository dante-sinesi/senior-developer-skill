#!/usr/bin/env python3
"""Cómo responden los hooks de senior cuando algo necesita la autorización del usuario.

Preguntar en la interfaz frena el trabajo hasta que el usuario responde, y eso no sirve cuando Claude trabaja horas sin
supervisión. Por eso hay dos modos:

  denegar     (por defecto) NO interrumpe: bloquea la acción y le explica a Claude, en el mismo mensaje, qué hacer
              (escribir en `.temporal/`, anotar el pendiente y seguir con otra cosa). Lo bloqueado queda registrado para
              que el usuario lo revise cuando vuelva y, si corresponde, lo autorice de antemano.
  preguntar   pregunta en la interfaz de Claude Code y espera. Para quien trabaja delante de la pantalla.

La configuración es del usuario y vive dentro del proyecto, en `.git/senior-hooks.json` (git no la sube; si el proyecto no
tiene git, en `.temporal/senior-hooks.json`). Contiene el modo, las rutas autorizadas de antemano y los últimos bloqueos.
La edita el usuario con `permisos_hooks.py`; Claude no puede (los hooks lo impiden), para que no se autorice solo.
Si algo falla, no se frena nada. Solo biblioteca estándar.
"""
import json
import os
import subprocess
from pathlib import Path

MODOS = ("denegar", "preguntar")
NOMBRE = "senior-hooks.json"
MAX_BLOQUEOS = 60


def raiz_del_proyecto(cwd=None):
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or ".", capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path(cwd or ".")


def ruta_config(raiz):
    raiz = Path(raiz)
    git = raiz / ".git"
    return (git / NOMBRE) if git.is_dir() else (raiz / ".temporal" / NOMBRE)


def normal(ruta):
    return os.path.normcase(os.path.normpath(str(ruta))).replace("\\", "/")


def cargar(raiz):
    datos = {"modo": "denegar", "permitidos": [], "bloqueos": []}
    try:
        leido = json.loads(ruta_config(raiz).read_text(encoding="utf-8-sig"))
        if isinstance(leido, dict):
            datos.update({k: leido[k] for k in datos if k in leido})
    except (OSError, ValueError):
        pass
    if datos["modo"] not in MODOS:
        datos["modo"] = "denegar"
    return datos


def guardar(raiz, datos):
    ruta = ruta_config(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def esta_permitido(raiz, ruta):
    """True si el usuario autorizó de antemano esa ruta o una carpeta que la contiene."""
    r = normal(ruta)
    for p in cargar(raiz)["permitidos"]:
        base = normal(p["ruta"] if isinstance(p, dict) else p).rstrip("/")
        if r == base or r.startswith(base + "/"):
            return True
    return False


def registrar_bloqueo(raiz, hook, detalle):
    """Deja constancia de lo bloqueado (sin repetir) para que el usuario lo revise cuando vuelva."""
    try:
        datos = cargar(raiz)
        if any(b.get("hook") == hook and b.get("detalle") == detalle for b in datos["bloqueos"]):
            return
        datos["bloqueos"] = (datos["bloqueos"] + [{"hook": hook, "detalle": detalle}])[-MAX_BLOQUEOS:]
        guardar(raiz, datos)
    except OSError:
        pass


def respuesta(raiz, hook, detalle, pregunta, instruccion):
    """JSON de la decisión del hook: 'ask' en modo preguntar, 'deny' (con la instrucción para Claude) en modo denegar."""
    if cargar(raiz)["modo"] == "preguntar":
        decision, razon = "ask", pregunta
    else:
        registrar_bloqueo(raiz, hook, detalle)
        decision = "deny"
        razon = (f"BLOQUEADO por senior ({hook}): {detalle}. No es una pregunta ni hay que esperar al usuario: {instruccion} "
                 "Seguí con el resto del trabajo; lo bloqueado quedó registrado para que el usuario lo revise cuando vuelva.")
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                              "permissionDecisionReason": razon}}, ensure_ascii=False)


def respuesta_fija(decision, razon):
    """JSON de una decisión que no depende del modo (por ejemplo, negar un cambio de la propia configuración)."""
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                              "permissionDecisionReason": razon}}, ensure_ascii=False)
