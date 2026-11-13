#!/usr/bin/env python3
"""Detecta si Token Diet (skill independiente de ahorro de tokens) está instalada y activa.

`senior` depende de Token Diet para todo lo que tiene que ver con el consumo de tokens (objetivo principal del
paquete): la lectura de documentos e imágenes, su hook de lectura, las capturas y la auditoría son suyos.

Se considera instalada si existe `~/.claude/skills/token-diet/.install.json` con una versión igual o mayor que la
mínima. Se considera que su hook de lectura está activo si `~/.claude/settings.json` lo registra.
Solo lee: no modifica nada. `SENIOR_TOKEN_DIET_HOME` cambia la carpeta de inicio (para las pruebas).

Uso: python token_diet.py [estado]   (imprime el estado; código 0 si está instalada y al día, 1 si no)
"""
import json
import os
import sys
from pathlib import Path

VERSION_MINIMA = (1, 0, 0)
INSTRUCCION = ("Token Diet no está instalada: sin ella el consumo de tokens es mucho mayor. Se instala desde su repositorio "
               "(https://github.com/dante-sinesi/token-diet-skill) con `python instalar.py install`.")


def inicio():
    return Path(os.environ.get("SENIOR_TOKEN_DIET_HOME") or Path.home())


def _version(texto):
    try:
        return tuple(int(p) for p in str(texto).strip().split(".")[:3])
    except ValueError:
        return None


def estado(home=None):
    """{'instalada', 'version', 'al_dia', 'hook_lectura'}: lo que se sabe de Token Diet en esta máquina."""
    base = Path(home) if home else inicio()
    res = {"instalada": False, "version": None, "al_dia": False, "hook_lectura": False}
    manifiesto = base / ".claude" / "skills" / "token-diet" / ".install.json"
    try:
        res["version"] = json.loads(manifiesto.read_text(encoding="utf-8")).get("version")
        res["instalada"] = True
    except (OSError, ValueError, AttributeError):
        return res
    v = _version(res["version"])
    res["al_dia"] = v is not None and v >= VERSION_MINIMA
    try:
        ajustes = json.loads((base / ".claude" / "settings.json").read_text(encoding="utf-8"))
        for entradas in (ajustes.get("hooks") or {}).get("PreToolUse", []):
            for h in entradas.get("hooks", []):
                orden = h.get("command", "") if isinstance(h, dict) else ""
                if "token-diet" in orden and "hook_lectura_externa" in orden:
                    res["hook_lectura"] = True
    except (OSError, ValueError, AttributeError):
        pass
    return res


def aviso(home=None):
    """Texto de aviso si falta Token Diet o está desactualizada; vacío si todo está bien."""
    e = estado(home)
    if not e["instalada"]:
        return INSTRUCCION
    if not e["al_dia"]:
        minima = ".".join(map(str, VERSION_MINIMA))
        return f"Token Diet {e['version']} es anterior a la {minima} que necesita este paquete. Actualizala con `python instalar.py install` desde su repositorio."
    if not e["hook_lectura"]:
        return "Token Diet está instalada pero su hook de lectura no está registrado: ejecutá `python instalar.py install` desde su repositorio."
    return ""


def main(argv):
    e = estado()
    print(f"Token Diet: {'instalada ' + str(e['version']) if e['instalada'] else 'no instalada'}"
          f"{'' if not e['instalada'] else ('; hook de lectura ' + ('activo' if e['hook_lectura'] else 'sin registrar'))}")
    texto = aviso()
    if texto:
        print(texto)
    return 0 if not texto else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
