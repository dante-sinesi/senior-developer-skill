#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse) que impide que Claude figure como autor o coautor en GitHub.

Bloquea, con código de salida 2 y un mensaje para Claude, los comandos de Bash o PowerShell que crean contenido
para GitHub con atribuciones: `git commit`, `git tag`, `git merge`, `git notes` y `gh pr|issue|release|api|gist`
cuando el comando (o el archivo de mensaje que usa con -F, --file, --body-file o --notes-file) contiene:
  - una línea «Co-Authored-By:» o un trailer que nombra a Claude o a Anthropic
  - un pie «Generated with Claude Code» o el emoji de robot
  - un autor o committer de Claude (--author, -c user.name, -c user.email)
Todo lo demás pasa sin tocarse. El usuario puede permitir coautores a propósito con SENIOR_PERMITIR_COAUTORES=1.

Lo activa `guardia_autoria.py asegurar` en ~/.claude/settings.json (vale para todos los proyectos).
Entrada: el JSON del hook por la entrada estándar. Solo biblioteca estándar.
"""
import json
import os
import re
import sys
from pathlib import Path

RELEVANTE = re.compile(r"(?<![\w-])(git\s+(?:-[^\s]+\s+)*(?:commit|tag|merge|notes)\b|gh\s+(?:pr|issue|release|api|gist)\b)")
ARCHIVOS = re.compile(r"""(?:-F|--file|--body-file|--notes-file|--message-file)[\s=]+("[^"]+"|'[^']+'|[^\s;&|]+)""")
PROHIBIDO = [
    (re.compile(r"(?i)co-authored-by\s*:"), "línea Co-Authored-By"),
    (re.compile(r"(?i)generated\s+(with|by)\b.{0,40}(claude|anthropic|\bai\b)"), "pie «Generated with …»"),
    (re.compile("\U0001F916"), "emoji de atribución (robot)"),
    (re.compile(r"(?i)(signed-off-by|reviewed-by|assisted-by)\s*:.*(claude|anthropic)"), "trailer que nombra a Claude o Anthropic"),
    (re.compile(r"(?i)--author[=\s]+[\"']?[^\"'\n]*(claude|anthropic)"), "autor de Claude (--author)"),
    (re.compile(r"(?i)-c\s+user\.(?:name|email)\s*=\s*[\"']?[^\"'\s]*(claude|anthropic)"), "identidad de Claude (-c user.*)"),
]


def textos_a_revisar(comando, cwd):
    textos = [comando]
    for m in ARCHIVOS.finditer(comando):
        ruta = Path(m.group(1).strip("\"'"))
        if not ruta.is_absolute():
            ruta = Path(cwd or ".") / ruta
        try:
            if ruta.is_file() and ruta.stat().st_size < 200_000:
                textos.append(ruta.read_text(encoding="utf-8-sig", errors="replace"))
        except OSError:
            pass
    return textos


def main():
    for flujo in (sys.stdin, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0  # entrada ilegible: no se bloquea nada que no se pueda juzgar
    if datos.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    comando = str((datos.get("tool_input") or {}).get("command", ""))
    if not RELEVANTE.search(comando):
        return 0
    permitir = os.environ.get("SENIOR_PERMITIR_COAUTORES") == "1"
    problemas = []
    for texto in textos_a_revisar(comando, datos.get("cwd")):
        for rx, nombre in PROHIBIDO:
            if rx.search(texto) and not (permitir and nombre == "línea Co-Authored-By") and nombre not in problemas:
                problemas.append(nombre)
    if not problemas:
        return 0
    print("BLOQUEADO por la guardia de autoría: " + "; ".join(problemas) + ". "
          "En lo que se sube a GitHub figura únicamente el usuario: sin Co-Authored-By, sin pies de generación y sin "
          "autores de Claude. Quitar esas líneas del mensaje o del texto y volver a ejecutar el comando.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
