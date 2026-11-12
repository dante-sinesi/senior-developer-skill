#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): pregunta antes de editar archivos que no se tocan a mano.

Protege tres grupos, porque equivocarse en ellos sale caro y casi nunca es lo que se quería:
  - Secretos: `.env` y `.env.*` (salvo `.example`, `.sample`, `.template`, `.dist`), claves y certificados
    (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.keystore`, `id_rsa*`, `id_ed25519*`), `.netrc` y `.pgpass`.
  - Interior de `.git/`: ahí manda git, no un editor.
  - Archivos de bloqueo de dependencias (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `composer.lock`,
    `Cargo.lock`, `poetry.lock`, `Pipfile.lock`, `uv.lock`, `go.sum`, `Gemfile.lock`): los genera el gestor de
    paquetes; editarlos a mano deja versiones que nadie resolvió.

Cubre Write, Edit y NotebookEdit. No ve lo que cambia un comando (por ejemplo `npm install` actualizando el
archivo de bloqueo, que es lo correcto). Según el modo de `modo_hooks.py`: por defecto («denegar») no interrumpe y le explica a Claude qué hacer; en modo «preguntar»
le pregunta al usuario en la interfaz y espera. Una ruta autorizada de antemano con `permisos_hooks.py permitir` pasa.
Se ignora lo que está dentro de `.temporal/` (muestras y pruebas del propio trabajo). Si algo falla, deja pasar.
Solo biblioteca estándar.
"""
import json
import re
import sys
from pathlib import Path

SECRETOS = re.compile(
    r"^(\.env(\..+)?|.+\.(pem|key|p12|pfx|keystore)|id_rsa.*|id_ed25519.*|\.netrc|\.pgpass)$", re.IGNORECASE)
PLANTILLAS = re.compile(r"\.(example|sample|template|dist|defaults)$", re.IGNORECASE)
BLOQUEO = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "composer.lock",
           "cargo.lock", "poetry.lock", "pipfile.lock", "uv.lock", "go.sum", "gemfile.lock"}


def categoria(ruta):
    """'secreto', 'bloqueo', 'git' o None según la ruta."""
    partes = [p for p in re.split(r"[\\/]+", ruta) if p]
    if not partes:
        return None
    if ".temporal" in partes[:-1]:
        return None
    nombre = partes[-1]
    if ".git" in partes[:-1]:
        return "git"
    if SECRETOS.match(nombre) and not PLANTILLAS.search(nombre):
        return "secreto"
    if nombre.lower() in BLOQUEO:
        return "bloqueo"
    return None


MENSAJES = {
    "secreto": "contiene o puede contener claves y credenciales. Un secreto escrito acá o copiado a otro archivo se considera comprometido",
    "bloqueo": "lo genera el gestor de paquetes (npm, composer, cargo...). A mano deja versiones que nadie resolvió; lo normal es "
               "cambiar las dependencias y regenerarlo con el gestor",
    "git": "es el interior de .git: ahí manda git, no un editor. Editarlo puede dejar el repositorio roto",
}


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        if datos.get("tool_name") not in ("Write", "Edit", "NotebookEdit"):
            return 0
        entrada = datos.get("tool_input") or {}
        ruta = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
        cat = categoria(ruta)
        if cat:
            import modo_hooks
            raiz = modo_hooks.raiz_del_proyecto(datos.get("cwd"))
            if modo_hooks.esta_permitido(raiz, Path(datos.get("cwd") or ".") / ruta if not Path(ruta).is_absolute() else ruta):
                return 0
    except Exception:  # noqa: BLE001 motivo: si algo falla, el hook deja pasar y no frena nada
        return 0
    if not cat:
        return 0
    pregunta = f"Claude quiere editar {ruta}, que {MENSAJES[cat]}. ¿Autorizás esta edición?"
    instruccion = ("no se edita a mano. Si hace falta cambiarlo, hacelo por la vía correcta (el gestor de paquetes para un archivo de bloqueo; "
                   "variables de entorno o un archivo de ejemplo para un secreto) o anotá en `docs/pendientes.md` qué cambio necesita autorización del usuario y seguí sin ese paso.")
    if cat == "secreto":
        env_gestion = (Path(__file__).resolve().parent / "env_gestion.py").as_posix()
        instruccion = ("un archivo de secretos se modifica con el permiso del usuario, y puede dártelo de antemano escribiendo en el chat `/permitir <ruta>` "
                       "(vos no podés). Mientras tanto: para declarar una variable nueva usá `python \"" + env_gestion + "\" declarar NOMBRE --comentario \"para qué sirve\"` "
                       "(la agrega a `.env.example` con un valor falso y, si `.env` está autorizado, también a `.env` sin valor), y proponele al usuario lo que necesitás "
                       "cambiar en `.env` (qué variables y para qué) para que lo autorice o lo complete él. Si trabajás sin supervisión, anotalo en `docs/pendientes.md` y "
                       "seguí con el código leyendo la variable de entorno.")
    print(modo_hooks.respuesta(raiz, "archivos protegidos", f"se intentó editar {ruta}", pregunta, instruccion))
    return 0


if __name__ == "__main__":
    sys.exit(main())
