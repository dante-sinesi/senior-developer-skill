#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): nada se crea fuera del directorio del proyecto sin autorización.

Regla máxima del paquete senior: los archivos, carpetas y descargas que Claude crea viven dentro del proyecto. Lo
temporal (muestras, capturas, pruebas, borradores) va en `.temporal/`, una carpeta que git ignora y que prepara
`temporal.py`. Si un caso puntual necesita salir del proyecto (un servidor local, una carpeta de otro programa),
el usuario lo autoriza de antemano.

Qué cuenta como «dentro del proyecto» (para no frenar trabajo legítimo):
  - la raíz de la sesión (CLAUDE_PROJECT_DIR) y la raíz del repositorio git del directorio de trabajo;
  - los proyectos hermanos: otros repositorios git que viven en la misma carpeta que el proyecto de la sesión
    (por ejemplo, otro proyecto del usuario dentro de su carpeta de trabajo). Se puede apagar con `permisos_hooks.py hermanos no`;
  - lo que el usuario autorizó de antemano (`/permitir <ruta>` en el chat o `permisos_hooks.py permitir`);
  - la memoria y los planes de Claude Code (`~/.claude/projects/*/memory/`, `~/.claude/plans/`).

Qué cubre:
  - Write, Edit y NotebookEdit: la ruta del archivo.
  - Bash y PowerShell, de forma aproximada: redirecciones (`>`, `>>`), mkdir, touch, New-Item, cp, mv, copy, move,
    tee, Set-Content, Add-Content, Out-File, curl -o, wget -O, Invoke-WebRequest -OutFile y `git clone <url> <destino>`.
    Las variables del propio comando (`D=.temporal/x; cp a $D/b`) se resuelven; una variable que no se puede resolver no
    se juzga (se deja pasar), salvo las del sistema como TEMP o APPDATA, que son siempre «afuera».
  - No ve lo que escribe un programa por dentro (por ejemplo, un script de Python que abre un archivo): para eso
    está la regla escrita en la skill.

Qué decide: según el modo de `modo_hooks.py`. Por defecto («denegar») NO interrumpe: bloquea y le dice a Claude que escriba
en `.temporal/` y siga, y deja registrado lo bloqueado. En modo «preguntar» le pregunta al usuario y espera. La configuración de
los hooks la edita el usuario, no Claude: cualquier intento de cambiarla se deniega, pero LEERLA está permitido. Si algo falla
o no se puede juzgar, deja pasar. Solo biblioteca estándar.
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
VARIABLE = re.compile(r"^(?:\$env:|\$\{env:|\$\{|\$|%)([A-Za-z_]\w*)")
ASIGNACION = re.compile(r"(?:^|[;&\n]\s*|\|\|\s*)(?:export\s+|set\s+)?\$?([A-Za-z_]\w*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s;&|=]+)")
SISTEMA = {"temp", "tmp", "tmpdir", "appdata", "localappdata", "userprofile", "homepath", "homedrive", "home", "programfiles",
           "programdata", "windir", "systemroot", "public", "systemdrive", "onedrive"}
DEL_PROYECTO = {"claude_project_dir", "pwd", "cd", "oldpwd"}
LECTURA = {"cat", "type", "get-content", "gc", "head", "tail", "less", "more", "ls", "dir", "get-childitem", "gci", "grep", "rg",
           "select-string", "findstr", "wc", "stat", "file", "jq", "test-path"}


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


def raices_propias(cwd, raiz):
    """La raíz de la sesión y la del repositorio git del directorio de trabajo (si es otra)."""
    raices = [Path(raiz)]
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or ".", capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            raices.append(Path(r.stdout.strip()))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return raices


def normal(ruta):
    return os.path.normcase(os.path.normpath(str(ruta))).replace("\\", "/")


def adentro(ruta, raiz):
    a, b = normal(ruta), normal(raiz).rstrip("/")
    return a == b or a.startswith(b + "/")


def de_claude(ruta):
    base = normal(Path.home() / ".claude")
    r = normal(ruta)
    return r.startswith(base + "/plans/") or bool(re.match(re.escape(base) + r"/projects/[^/]+/memory/", r))


def variables_del_comando(comando):
    """{nombre en minúscula: valor} de las asignaciones del propio comando (`D=.temporal/x`, `$d = "..."`)."""
    return {m.group(1).lower(): m.group(2).strip("\"'") for m in ASIGNACION.finditer(comando)}


def sustituir(texto, variables):
    """Reemplaza $NOMBRE y ${NOMBRE} por lo asignado en el mismo comando (hasta tres niveles)."""
    for _ in range(3):
        nuevo = re.sub(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)",
                       lambda m: variables.get((m.group(1) or m.group(2)).lower(), m.group(0)), texto)
        if nuevo == texto:
            break
        texto = nuevo
    return texto


def a_ruta(token, cwd):
    """Ruta absoluta del token o None si no es una ruta o no se puede juzgar. Una variable del sistema (TEMP, APPDATA…) es 'afuera'."""
    t = token.strip("\"'")
    if not t or t.startswith("-") and not t.startswith("-/"):
        return None
    if t.lower() in SIN_EFECTO or re.match(r"^[a-z][a-z0-9+.-]*://", t, re.IGNORECASE):
        return None
    m_var = VARIABLE.match(t)
    if m_var:
        nombre = m_var.group(1).lower()
        if nombre in DEL_PROYECTO:
            return None
        return Path("/__variable_de_entorno__") if nombre in SISTEMA else None  # una variable desconocida no se puede juzgar
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


def fuera_del_proyecto(textos, cwd, raices, hermano=None):
    """Los textos que apuntan fuera de todas las raíces propias (y de un proyecto hermano, si `hermano` lo acepta)."""
    fuera = []
    for t in textos:
        ruta = a_ruta(t, cwd)
        if ruta is None or de_claude(ruta) or any(adentro(ruta, r) for r in raices):
            continue
        if hermano is not None and hermano(ruta):
            continue
        fuera.append(t.strip("\"'"))
    return fuera


def toca_configuracion(herramienta, entrada, comando, nombre):
    """True si se intenta CAMBIAR la configuración de los hooks. Leerla (cat, type, Get-Content…) está permitido."""
    if herramienta in ("Write", "Edit", "NotebookEdit"):
        return Path(str(entrada.get("file_path") or entrada.get("notebook_path") or "")).name == nombre
    for seg in SEPARADORES.split(comando):
        if re.search(r"permisos_hooks\.py\s+(?:--raiz\s+\S+\s+)?(modo|permitir|quitar|limpiar|hermanos)\b", seg):
            return True
        if nombre in seg:
            tokens = [t.strip("\"'") for t in TOKEN.findall(seg)]
            while tokens and tokens[0].lower() in ("sudo", "env", "command", "time"):
                tokens = tokens[1:]
            verbo = Path(tokens[0].replace("\\", "/")).name.lower().removesuffix(".exe") if tokens else ""
            if verbo in LECTURA and ">" not in seg:
                continue
            return True
    return False


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
            comando = ""
        elif herramienta in ("Bash", "PowerShell"):
            comando = str(entrada.get("command", ""))
            variables = variables_del_comando(comando)
            textos = [sustituir(t, variables) for t in objetivos_de_shell(comando)]
        else:
            return 0
        import modo_hooks
        toca_config = toca_configuracion(herramienta, entrada, comando, modo_hooks.NOMBRE)
        config = modo_hooks.cargar(raiz)

        def hermano(ruta):
            return bool(config.get("hermanos", True)) and modo_hooks.proyecto_hermano(raiz, ruta)
        fuera = [] if toca_config else fuera_del_proyecto([t for t in textos if t], cwd, raices_propias(cwd, raiz), hermano)
        fuera = [t for t in fuera if not modo_hooks.esta_permitido(raiz, a_ruta(t, cwd))]
    except Exception:  # noqa: BLE001 motivo: si algo falla, no se frena nada
        return 0
    if toca_config:
        print(modo_hooks.respuesta_fija("deny", "Los permisos de los hooks de senior los configura el usuario (`permisos_hooks.py` o escribiendo "
                                                 "`/permitir <ruta>` en el chat); no se pueden cambiar desde Claude, pero sí leer. Seguí con el resto del trabajo."))
        return 0
    if not fuera:
        return 0
    lista = ", ".join(fuera[:3]) + (f" y {len(fuera) - 3} más" if len(fuera) > 3 else "")
    pregunta = (f"Claude quiere crear algo fuera del proyecto ({raiz}): {lista}. La regla máxima de senior es trabajar "
                "dentro del proyecto: lo temporal va en `.temporal/` (git lo ignora; lo prepara temporal.py). "
                "¿Autorizás esta excepción?")
    destinos = ", ".join(f"{t} → {(Path(raiz) / '.temporal' / Path(t).name).as_posix()}" for t in fuera[:3])
    instruccion = (f"rehacé exactamente lo mismo dentro del proyecto y seguí desde ahí ({destinos}). Lo de paso va en `.temporal/` "
                   "(git lo ignora; `temporal.py` la prepara; se crea sola al escribir ahí): ni la carpeta de trabajo del entorno "
                   "ni la temporal del sistema, y los comandos posteriores usan esa ruta nueva. Si de verdad hace falta salir del proyecto "
                   "(un servidor local, la carpeta de otro programa), seguí sin ese paso, anotalo en `docs/pendientes.md` (o en `.temporal/pendientes.md` "
                   "si no hay docs/) y avisale al usuario, en tu resumen, que puede autorizarlo de antemano escribiendo en el chat "
                   "`/permitir <ruta>` (vos no podés).")
    print(modo_hooks.respuesta(raiz, "escritura fuera del proyecto", f"se intentó crear algo fuera del proyecto: {lista}", pregunta, instruccion))
    return 0


if __name__ == "__main__":
    sys.exit(main())
