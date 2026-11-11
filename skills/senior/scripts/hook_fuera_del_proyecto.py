#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): nada se crea fuera del directorio del proyecto sin autorización.

Regla máxima del paquete senior: los archivos, carpetas y descargas que Claude crea viven dentro del proyecto. Lo
temporal (muestras, capturas, pruebas, borradores) va en `.temporal/`, una carpeta que git ignora y que prepara
`temporal.py`. Si un caso puntual necesita salir del proyecto (un servidor local, una carpeta de otro programa),
se le pide permiso al usuario cada vez.

Qué cubre:
  - Write, Edit y NotebookEdit: la ruta del archivo.
  - Bash y PowerShell, de forma aproximada: redirecciones (`>`, `>>`), mkdir, touch, New-Item, cp, mv, copy, move,
    tee, Set-Content, Add-Content, Out-File, curl -o, wget -O, Invoke-WebRequest -OutFile y `git clone <url> <destino>`.
  - No ve lo que escribe un programa por dentro (por ejemplo, un script de Python que abre un archivo): para eso
    está la regla escrita en la skill.

Qué decide: le PREGUNTA AL USUARIO en la interfaz de Claude Code (nunca bloquea del todo). Si algo falla o no se
puede juzgar, deja pasar.
Quedan permitidas, porque son del propio Claude Code y no del proyecto, la memoria (`~/.claude/projects/*/memory/`)
y los planes (`~/.claude/plans/`).
La raíz del proyecto es CLAUDE_PROJECT_DIR; si no está, la raíz del repositorio git del directorio actual.
Solo biblioteca estándar.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SEPARADORES = re.compile(r"\|\||&&|[|;\n]")
TOKEN = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")
REDIRECCION = re.compile(r"(?<![<>&\w-])(?:\d?>>?)\s*(?!&)[\"']?([^\s\"'|;&<>]+)")
CREAN = {"mkdir", "md", "touch", "new-item", "ni", "tee", "set-content", "sc", "add-content", "ac", "out-file"}
COPIAN = {"cp", "copy", "copy-item", "mv", "move", "move-item", "robocopy", "xcopy", "rsync", "ren", "rename-item"}
DESCARGAN = {"curl", "wget", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"}
OPCION_DESTINO = {"-o", "-O", "--output", "--output-document", "-outfile", "-out-file"}
SIN_EFECTO = {"/dev/null", "/dev/stdout", "/dev/stderr", "nul", "$null", "con"}
VARIABLE = re.compile(r"^(\$env:|\$\{?env:|%[A-Za-z_]+%|\$\{?[A-Za-z_]+\}?)")
DEL_PROYECTO = ("claude_project_dir", "$pwd", "${pwd}", "%cd%")


def raiz_del_proyecto(cwd):
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


def normal(ruta):
    return os.path.normcase(os.path.normpath(str(ruta))).replace("\\", "/")


def adentro(ruta, raiz):
    a, b = normal(ruta), normal(raiz).rstrip("/")
    return a == b or a.startswith(b + "/")


def de_claude(ruta):
    base = normal(Path.home() / ".claude")
    r = normal(ruta)
    return r.startswith(base + "/plans/") or bool(re.match(re.escape(base) + r"/projects/[^/]+/memory/", r))


def a_ruta(token, cwd):
    """Ruta absoluta del token o None si no es una ruta. Un token con variable de entorno ajena es 'afuera'."""
    t = token.strip("\"'")
    if not t or t.startswith("-") and not t.startswith("-/"):
        return None
    if t.lower() in SIN_EFECTO or re.match(r"^[a-z][a-z0-9+.-]*://", t, re.IGNORECASE):
        return None
    if VARIABLE.match(t):
        return None if any(d in t.lower() for d in DEL_PROYECTO) else Path("/__variable_de_entorno__")
    if t.startswith("~"):
        t = str(Path.home()) + t[1:]
    m = re.match(r"^/([a-zA-Z])(/.*)?$", t)  # /c/Users/... de Git Bash
    if m:
        t = f"{m.group(1).upper()}:{m.group(2) or '/'}"
    p = Path(t)
    if not p.is_absolute() and not os.path.isabs(t):
        p = Path(cwd or ".") / t
    return Path(os.path.abspath(str(p)))


def objetivos_de_shell(comando):
    """Textos que el comando usa como destino de una escritura (aproximado)."""
    res = []
    for seg in SEPARADORES.split(comando):
        res.extend(REDIRECCION.findall(seg))
        tokens = [t.strip("\"'") for t in TOKEN.findall(seg)]
        if not tokens:
            continue
        verbo = Path(tokens[0].replace("\\", "/")).name.lower().removesuffix(".exe")
        args = [t for t in tokens[1:] if not t.startswith("-") or t.startswith("-/")]
        if verbo in CREAN:
            res.extend(args)
        elif verbo in COPIAN and len(args) >= 2:
            res.append(args[-1])
        elif verbo in DESCARGAN:
            for i, t in enumerate(tokens[1:-1], 1):
                if t in OPCION_DESTINO or t.lower() in OPCION_DESTINO:
                    res.append(tokens[i + 1])
        elif verbo == "git" and len(tokens) > 3 and tokens[1] == "clone":
            posicionales = [t for t in tokens[2:] if not t.startswith("-")]
            if len(posicionales) >= 2:
                res.append(posicionales[-1])
    return res


def fuera_del_proyecto(textos, cwd, raiz):
    fuera = []
    for t in textos:
        ruta = a_ruta(t, cwd)
        if ruta is not None and not adentro(ruta, raiz) and not de_claude(ruta):
            fuera.append(t.strip("\"'"))
    return fuera


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        herramienta = datos.get("tool_name")
        entrada = datos.get("tool_input") or {}
        cwd = datos.get("cwd") or os.getcwd()
        raiz = raiz_del_proyecto(cwd)
        if herramienta in ("Write", "Edit", "NotebookEdit"):
            textos = [str(entrada.get("file_path") or entrada.get("notebook_path") or "")]
        elif herramienta in ("Bash", "PowerShell"):
            textos = objetivos_de_shell(str(entrada.get("command", "")))
        else:
            return 0
        fuera = fuera_del_proyecto([t for t in textos if t], cwd, raiz)
    except Exception:  # noqa: BLE001 - si algo falla, no se frena nada
        return 0
    if not fuera:
        return 0
    lista = ", ".join(fuera[:3]) + (f" y {len(fuera) - 3} más" if len(fuera) > 3 else "")
    mensaje = (f"Claude quiere crear algo fuera del proyecto ({raiz}): {lista}. La regla máxima de senior es trabajar "
               "dentro del proyecto: lo temporal va en `.temporal/` (git lo ignora; lo prepara temporal.py). "
               "¿Autorizás esta excepción?")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                             "permissionDecisionReason": mensaje}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
