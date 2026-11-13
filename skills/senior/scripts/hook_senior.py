#!/usr/bin/env python3
"""Despachador de los hooks PreToolUse de senior: un solo proceso de Python en lugar de cinco.

Cada llamada de Claude a una herramienta (leer, escribir, ejecutar un comando) pasaba por hasta cinco procesos de Python, uno por hook,
y cada uno cuesta unos 180 ms: casi un segundo de espera por llamada. Este despachador se registra una sola vez, lee la llamada una vez y
corre los controles que corresponden a esa herramienta dentro del mismo proceso:

  autoría (`hook_autoria_claude.py`)                      Bash, PowerShell
  lectura de documentos externos (`hook_lectura_externa.py`)   Read, Bash, PowerShell, Write, Edit
  escritura fuera del proyecto (`hook_fuera_del_proyecto.py`)  Write, Edit, NotebookEdit, Bash, PowerShell
  archivos protegidos (`hook_archivos_protegidos.py`)     Write, Edit, NotebookEdit
  secretos y datos personales (`hook_secretos_claude.py`) Read, Grep, Write, Edit, NotebookEdit, Bash, PowerShell

Cada hook sigue funcionando solo (con la misma entrada y la misma salida) y conserva sus reglas: este script no decide nada, solo los
ejecuta y junta lo que dicen. Si alguno bloquea (código de salida 2, o una decisión «deny»), se corta ahí y esa es la respuesta; si alguno
pregunta («ask») y ninguno bloquea, se pregunta; si ninguno dice nada, la acción sigue. Un hook que falla por dentro no frena nada (como solo),
y con `SENIOR_HOOK_DEPURAR=1` el error se ve. Solo biblioteca estándar.
"""
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
HOOKS = (  # (skill, archivo, herramientas a las que aplica), en el orden en que se consultan
    ("senior-git", "hook_autoria_claude.py", {"Bash", "PowerShell"}),
    ("senior-relevar", "hook_lectura_externa.py", {"Read", "Bash", "PowerShell", "Write", "Edit"}),
    ("senior", "hook_fuera_del_proyecto.py", {"Write", "Edit", "NotebookEdit", "Bash", "PowerShell"}),
    ("senior", "hook_archivos_protegidos.py", {"Write", "Edit", "NotebookEdit"}),
    ("senior", "hook_secretos_claude.py", {"Read", "Grep", "Write", "Edit", "NotebookEdit", "Bash", "PowerShell"}),
)
HERRAMIENTAS = sorted(set().union(*(h[2] for h in HOOKS)))


def depurando():
    return os.environ.get("SENIOR_HOOK_DEPURAR") == "1"


def ejecutar(skill, archivo, bruto):
    """(código de salida, stdout, stderr) del `main()` de un hook corrido en este proceso con `bruto` como entrada; None si el hook no está."""
    ruta = SKILLS / skill / "scripts" / archivo
    if not ruta.exists():
        return None
    espec = importlib.util.spec_from_file_location("senior_hook_" + ruta.stem, ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    antes = sys.stdin, sys.stdout, sys.stderr
    sys.stdin, sys.stdout, sys.stderr = io.StringIO(bruto), io.StringIO(), io.StringIO()
    try:
        codigo = modulo.main()
        return (codigo or 0), sys.stdout.getvalue(), sys.stderr.getvalue()
    except SystemExit as salida:
        return (salida.code if isinstance(salida.code, int) else 0), sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.stdin, sys.stdout, sys.stderr = antes


def decision_de(salida):
    try:
        return json.loads(salida)["hookSpecificOutput"]["permissionDecision"]
    except (ValueError, KeyError, TypeError):
        return None


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    bruto = sys.stdin.read()
    try:
        datos = json.loads(bruto or "{}")
        if not isinstance(datos, dict):
            raise TypeError("la entrada del hook no es un objeto JSON")
        herramienta = datos.get("tool_name")
    except Exception:  # noqa: BLE001 motivo: una entrada ilegible no se puede juzgar y no se frena nada (con SENIOR_HOOK_DEPURAR=1 el error se ve)
        if depurando():
            raise
        return 0
    pregunta = None
    for skill, archivo, herramientas in HOOKS:
        if herramienta not in herramientas:
            continue
        try:
            resultado = ejecutar(skill, archivo, bruto)
        except Exception:  # noqa: BLE001 motivo: un hook que falla por dentro no frena nada, igual que solo (con SENIOR_HOOK_DEPURAR=1 el error se ve)
            if depurando():
                raise
            continue
        if resultado is None:
            continue
        codigo, salida, error = resultado
        if codigo == 2:
            sys.stderr.write(error)
            return 2
        decision = decision_de(salida)
        if decision == "deny":
            print(salida.strip())
            return 0
        if decision == "ask" and pregunta is None:
            pregunta = salida
    if pregunta:
        print(pregunta.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
