#!/usr/bin/env python3
"""Segunda capa para «nada fuera del proyecto»: qué tiene activado Claude Code por su cuenta y qué conviene sumar. Solo lee.

El hook `hook_fuera_del_proyecto.py` es una lista de patrones: frena las formas conocidas de escribir fuera del proyecto, pero un
script guardado en un archivo, una ruta armada con código o un comando que no está en la lista pasan. Es una barrera contra
descuidos, no contra una evasión deliberada. Claude Code trae dos defensas propias que sí actúan por otro camino, y este script dice
cuál tenés activa (según la documentación oficial de Claude Code):

  permissions.blockWritesOutsideWorkingDirectories: true
      Write, Edit y NotebookEdit rechazan escribir fuera de los directorios de trabajo, en cualquier modo de permisos. NO limita
      los comandos de shell, los servidores MCP ni los programas que corre un hook. Exige Claude Code 2.1.314 o posterior.
      Ojo con el costo: también frena lo que `/permitir <ruta>` autoriza y los proyectos hermanos, salvo que se agreguen como
      directorios de trabajo (`/add-dir`).
  sandbox.enabled: true
      Restringe a nivel del sistema operativo lo que escriben Bash y PowerShell y todos sus procesos hijos: por defecto solo el
      directorio de trabajo y el temporal del usuario. Es la única capa que cubre cualquier comando. Funciona en macOS, Linux y WSL2;
      en Windows nativo NO existe (los comandos corren sin restricción): para usarlo hay que correr Claude Code dentro de WSL2.

Las reglas `deny` de Bash (`Bash(cmd *)`) NO sirven como frontera: coinciden con el texto del comando que escribe Claude, y la propia
documentación advierte que se esquivan con otra forma de invocar lo mismo (`/usr/bin/curl`, `sh -c '...'`).

Este script no cambia ningún ajuste: son ajustes de seguridad con consecuencias, y los decide el usuario.

Uso:
    python capas_extra.py [--raiz .]
"""
import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

VERSION_MINIMA = (2, 1, 314)
FRAGMENTOS = {
    "bloqueo": '{\n  "permissions": {\n    "blockWritesOutsideWorkingDirectories": true\n  }\n}',
    "sandbox": '{\n  "sandbox": {\n    "enabled": true,\n    "failIfUnavailable": true,\n    "allowUnsandboxedCommands": false\n  }\n}',
}


def leer_json(ruta):
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def valor(ajustes_en_orden, camino):
    """El valor de un ajuste (p. ej. ('permissions', 'blockWritesOutsideWorkingDirectories')) en el primer archivo de ajustes que lo defina."""
    for ajustes in ajustes_en_orden:
        actual = ajustes
        for clave in camino:
            actual = actual.get(clave) if isinstance(actual, dict) else None
        if actual is not None:
            return actual
    return None


def sistema_actual():
    """'windows', 'macos', 'linux' o 'wsl2' (WSL1 se cuenta como linux sin sandbox: no se distingue y se avisa)."""
    nombre = platform.system()
    if nombre == "Windows":
        return "windows"
    if nombre == "Darwin":
        return "macos"
    try:
        if "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower():
            return "wsl2"
    except OSError:
        pass
    return "linux"


def version_de_claude():
    """(2, 1, 314) o None si `claude` no está o no responde."""
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=15, shell=(platform.system() == "Windows"))
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", r.stdout + r.stderr)
        return tuple(int(x) for x in m.groups()) if m else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def evaluar(ajustes, sistema, version):
    """Líneas del informe para unos ajustes (lista de dicts, del más específico al más general), un sistema y una versión de Claude Code."""
    bloqueo = valor(ajustes, ("permissions", "blockWritesOutsideWorkingDirectories")) is True
    sandbox = valor(ajustes, ("sandbox", "enabled")) is True
    soporta_sandbox = sistema in ("macos", "linux", "wsl2")
    lineas = ["Segunda capa para «nada fuera del proyecto» (la primera es el hook de senior, una lista de patrones):"]
    if bloqueo:
        lineas.append("  - `blockWritesOutsideWorkingDirectories`: ACTIVO. Write, Edit y NotebookEdit no pueden escribir fuera de los directorios de trabajo "
                      "(tampoco lo que autorizás con /permitir: agregá esas carpetas con /add-dir).")
    else:
        extra = ""
        if version is not None and version < VERSION_MINIMA:
            extra = f" Tu Claude Code es {'.'.join(map(str, version))} y la clave exige {'.'.join(map(str, VERSION_MINIMA))} o posterior: actualizarlo primero."
        elif version is None:
            extra = " No se pudo leer la versión de Claude Code: la clave exige 2.1.314 o posterior."
        lineas.append("  - `blockWritesOutsideWorkingDirectories`: no está activo. Cubre las herramientas de archivos con una regla propia de Claude Code, no con patrones; "
                      "costo: también frena `/permitir` y los proyectos hermanos (hay que agregarlos con /add-dir). Para activarlo, en `~/.claude/settings.json`:" + extra)
        lineas += ["      " + l for l in FRAGMENTOS["bloqueo"].splitlines()]
    if sandbox and soporta_sandbox:
        lineas.append("  - `sandbox`: ACTIVO. Los comandos de Bash y PowerShell y sus procesos hijos solo escriben donde el sistema operativo lo permite: es la capa que cubre cualquier comando.")
    elif sandbox and not soporta_sandbox:
        lineas.append("  - `sandbox`: figura activado, pero en Windows nativo no existe: los comandos corren SIN restricción. Para usarlo hay que correr Claude Code dentro de WSL2.")
    elif soporta_sandbox:
        lineas.append(f"  - `sandbox`: no está activo y tu sistema ({sistema}) lo soporta. Es la única capa que cubre cualquier comando de shell. Para activarlo, en `~/.claude/settings.json`:")
        lineas += ["      " + l for l in FRAGMENTOS["sandbox"].splitlines()]
    else:
        lineas.append("  - `sandbox`: no existe en Windows nativo (los comandos de shell corren sin restricción del sistema operativo). Para tenerlo, correr Claude Code dentro de WSL2. "
                      "Mientras tanto, lo que escribe un script guardado en un archivo o una ruta armada con código solo lo cubre la regla escrita de senior.")
    lineas.append("  - Las reglas `deny` de Bash no son una frontera: se esquivan cambiando la forma de invocar el mismo comando. No se usan para esto.")
    lineas.append("Esto solo informa: los ajustes de seguridad los cambia el usuario, no Claude.")
    return lineas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    ajustes = [leer_json(raiz / ".claude" / "settings.local.json"), leer_json(raiz / ".claude" / "settings.json"), leer_json(Path.home() / ".claude" / "settings.json")]
    print("\n".join(evaluar(ajustes, sistema_actual(), version_de_claude())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
