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
import time
from pathlib import Path

MODOS = ("denegar", "preguntar")
NOMBRE = "senior-hooks.json"
MAX_BLOQUEOS = 60
ESCALA = 3  # a la tercera vez que se repite el mismo bloqueo, el mensaje deja de ser una explicación y pasa a ser una orden con la alternativa primero
REGLAS = (  # (nombre en el registro, qué frena, cómo se autoriza)
    ("escritura fuera del proyecto", "crear archivos o carpetas fuera de la raíz del proyecto (lo de paso va en `.temporal/`)", "`/permitir <ruta>`"),
    ("archivos protegidos", "editar `.env`, claves, el interior de `.git/` y los archivos de bloqueo de dependencias", "`/permitir <ruta>`"),
    ("secretos", "escribir claves o datos personales en archivos que van a git, leer `.env`, `git add -f` y claves en mensajes de commit", "`/permitir .env` para leer y editar `.env`"),
    ("lectura de documentos externos", "leer un PDF o un HTML externo sin convertirlo antes", "se convierten con `convertir_fuentes.py`; no se autoriza por ruta"),
    ("autoría", "commits, Pull Requests e issues con Claude o coautores", "no se autoriza: en GitHub figura solo el usuario"),
)


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
    datos = {"modo": "denegar", "permitidos": [], "bloqueos": [], "hermanos": True}
    try:
        leido = json.loads(ruta_config(raiz).read_text(encoding="utf-8-sig"))
        if isinstance(leido, dict):
            datos.update({k: leido[k] for k in datos if k in leido})
    except (OSError, ValueError):
        pass
    if datos["modo"] not in MODOS:
        datos["modo"] = "denegar"
    datos["hermanos"] = datos["hermanos"] is not False
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


def proyecto_hermano(raiz, ruta):
    """True si la ruta está dentro de otro repositorio git que vive en la misma carpeta que el proyecto de la sesión
    (otro proyecto del usuario en su carpeta de trabajo). Escribir ahí es trabajar en un proyecto, no dejar archivos sueltos."""
    padre, propia = normal(Path(raiz).parent), normal(raiz)
    p = Path(ruta)
    for a in [p, *p.parents]:
        try:
            if (a / ".git").exists():
                return normal(a.parent) == padre and normal(a) != propia
        except OSError:
            return False
    return False


def demasiado_amplia(ruta):
    """Una raíz de disco, la carpeta del usuario o una ruta de menos de tres niveles no se autoriza de antemano."""
    p = Path(ruta).resolve()
    return p == Path(p.anchor) or p == Path.home().resolve() or len(p.parts) < 3


def permitir_ruta(raiz, ruta, motivo=""):
    """Autoriza de antemano una ruta (y lo que contiene). Devuelve (ok, mensaje)."""
    ruta = Path(ruta.strip("\"'"))
    ruta = ruta if ruta.is_absolute() else Path(raiz) / ruta
    if demasiado_amplia(ruta):
        return False, f"{ruta.as_posix()} es demasiado amplia (un disco, la carpeta del usuario o una ruta casi en la raíz): indicar la carpeta concreta."
    datos = cargar(raiz)
    if any(normal(p["ruta"] if isinstance(p, dict) else p) == normal(ruta) for p in datos["permitidos"]):
        return True, "Ya estaba autorizada."
    datos["permitidos"].append({"ruta": ruta.as_posix(), "motivo": motivo, "fecha": ahora()})
    guardar(raiz, datos)
    return True, f"Autorizada de antemano: {ruta.as_posix()} (y todo lo que contiene)."


def ahora():
    return time.strftime("%Y-%m-%d %H:%M")


def registrar_bloqueo(raiz, hook, detalle):
    """Deja constancia de lo bloqueado para que el usuario lo revise cuando vuelva y cuenta las veces que se repite. Devuelve cuántas van."""
    try:
        datos = cargar(raiz)
        for b in datos["bloqueos"]:
            if b.get("hook") == hook and b.get("detalle") == detalle:
                b["veces"] = int(b.get("veces", 1)) + 1
                b["ultima"] = ahora()
                guardar(raiz, datos)
                return b["veces"]
        datos["bloqueos"] = (datos["bloqueos"] + [{"hook": hook, "detalle": detalle, "veces": 1, "primera": ahora(), "ultima": ahora()}])[-MAX_BLOQUEOS:]
        guardar(raiz, datos)
        return 1
    except (OSError, ValueError):
        return 1


def razon_de_bloqueo(hook, detalle, instruccion, veces):
    """El mensaje que recibe Claude cuando se bloquea algo. Pensado para sesiones largas sin supervisión: NUNCA pide parar, avisar ni esperar al
    usuario. Hasta la segunda vez explica y da la alternativa; desde la tercera, que es cuando el modelo está insistiendo, pone la alternativa
    primero, dice que repetir no sirve y manda a seguir con la tarea. El aviso para el usuario va al registro, que se resume al cerrar la sesión."""
    if veces < ESCALA:
        return (f"BLOQUEADO por senior ({hook}): {detalle}. No es una pregunta ni hay que esperar al usuario: {instruccion} "
                "Seguí con el resto del trabajo; lo bloqueado quedó registrado para que el usuario lo revise cuando vuelva.")
    return (f"BLOQUEADO por senior ({hook}), por {veces}ª vez: {detalle}. Este intento no va a funcionar por más que lo repitas, ni haciendo lo mismo de otra forma. "
            f"Hacé esto en su lugar: {instruccion} Seguí con la tarea sin detenerte y sin esperar a nadie: este bloqueo ya quedó registrado como reincidente "
            "para que el usuario lo revise cuando vuelva.")


def resumen_bloqueos(raiz, desde=None):
    """Líneas con lo bloqueado, agrupado por hook. `desde` es una fecha «AAAA-MM-DD HH:MM» y filtra los que tienen fecha."""
    bloqueos = [b for b in cargar(raiz)["bloqueos"] if not desde or b.get("ultima", "9999") >= desde]
    if not bloqueos:
        return ["Bloqueos: ninguno" + (f" desde {desde}." if desde else ".")]
    por_hook = {}
    for b in bloqueos:
        por_hook.setdefault(b["hook"], []).append(b)
    reincidentes = [b for b in bloqueos if int(b.get("veces", 1)) >= ESCALA]
    lineas = [f"Bloqueos: {len(bloqueos)} distintos" + (f", {len(reincidentes)} que reinciden (Claude insistió {ESCALA} veces o más)" if reincidentes else "") + "."]
    for hook, lista in por_hook.items():
        lineas.append(f"  [{hook}] {len(lista)}: " + "; ".join(b["detalle"] + (f" (×{b['veces']})" if int(b.get("veces", 1)) > 1 else "") for b in lista[-3:])
                      + (f" y {len(lista) - 3} más" if len(lista) > 3 else ""))
    lineas.append("  Si alguno se repite, autorizarlo de antemano (`/permitir <ruta>`) evita que Claude lo vuelva a intentar."
                  + (" Los que reinciden son la señal de que la indicación no alcanzó: conviene una barrera (principio 17 de senior)." if reincidentes else ""))
    return lineas


def explicacion(raiz):
    """Texto completo y legible de la configuración: modo, qué frena cada hook y cómo se autoriza, y lo que se bloqueó."""
    d = cargar(raiz)
    lineas = [f"Modo: {d['modo']}" + (" (no interrumpe: bloquea, le explica a Claude qué hacer y deja registro)" if d["modo"] == "denegar" else " (pregunta en la interfaz y espera tu respuesta)") + ".",
              "Proyectos hermanos (otros repositorios de la misma carpeta): " + ("cuentan como «dentro»." if d["hermanos"] else "no cuentan."),
              "Qué frena cada hook y cómo se autoriza:"]
    lineas += [f"  - {n}: {que}. Autorización: {como}." for n, que, como in REGLAS]
    if d["permitidos"]:
        lineas.append("Autorizado de antemano:")
        for p in d["permitidos"]:
            ruta, motivo, fecha = (p["ruta"], p.get("motivo", ""), p.get("fecha", "")) if isinstance(p, dict) else (p, "", "")
            lineas.append(f"  - {ruta}" + (f" — {motivo}" if motivo else "") + (f" ({fecha})" if fecha else ""))
    else:
        lineas.append("Autorizado de antemano: nada.")
    lineas += resumen_bloqueos(raiz)
    lineas.append(f"Configuración: {ruta_config(raiz)}")
    return chr(10).join(lineas)


def respuesta(raiz, hook, detalle, pregunta, instruccion):
    """JSON de la decisión del hook: 'ask' en modo preguntar, 'deny' (con la instrucción para Claude) en modo denegar."""
    if cargar(raiz)["modo"] == "preguntar":
        decision, razon = "ask", pregunta
    else:
        veces = registrar_bloqueo(raiz, hook, detalle)
        decision = "deny"
        razon = razon_de_bloqueo(hook, detalle, instruccion, veces)
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                              "permissionDecisionReason": razon}}, ensure_ascii=False)


def respuesta_fija(decision, razon):
    """JSON de una decisión que no depende del modo (por ejemplo, negar un cambio de la propia configuración)."""
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                              "permissionDecisionReason": razon}}, ensure_ascii=False)
