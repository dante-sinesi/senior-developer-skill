#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): no deja fusionar un Pull Request cuyos chequeos de CI no están en verde.

Una medición con agentes reales mostró que, ante «Fusioná el Pull Request 12», el agente fusiona sin mirar los chequeos (9 de 9, 4 con uno en rojo): una instrucción
de texto no alcanza porque casi nunca se carga. Este hook no depende de eso: ve cada `gh pr merge` de un comando de Bash o PowerShell (también dentro de `&&`, `;` o `|`,
con `gh.exe`, `-R dueño/nombre`, un número, una URL o una rama) y corre `ci.py estado` sobre ese Pull Request:
  - todo en verde, o el proyecto no tiene CI                 → pasa
  - algún chequeo en rojo                                      → bloquea (también con `--auto` y con `--admin`)
  - chequeos pendientes                                        → bloquea, salvo con `--auto` (GitHub fusiona solo cuando pasan)
  - no se pudo saber (sin `gh`, sin red, respuesta ilegible)   → pasa: una falla de red no debe trabar todas las fusiones
Según el modo de `modo_hooks.py`: por defecto («denegar») no interrumpe, le explica a Claude qué hacer (anotar el pendiente y seguir con otra tarea) y deja registro; en modo
«preguntar» le pregunta al usuario. Para fusionar igual, el usuario escribe en el chat `/permitir-fusion N` (Claude no puede: solo el usuario dispara ese comando). La autorización vale
para UNA fusión de ese Pull Request, se gasta solo si sirvió para saltar un bloqueo y, una vez permitido el comando, no se devuelve aunque `gh` falle después.
Si algo falla por dentro, deja pasar (con SENIOR_HOOK_DEPURAR=1 el error se ve). Solo biblioteca estándar.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CI = Path(__file__).resolve().parent / "ci.py"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "senior" / "scripts"))

FUSION = re.compile(r"(?:^|[;&|(\n])\s*(?:&\s*)?(?:\S*[\\/])?gh(?:\.exe)?\b(?P<antes>(?:\s+(?:-R|--repo)[ =]\S+)*)\s+pr\s+merge\b(?P<args>[^;&|\n]*)", re.IGNORECASE)
CON_VALOR = {"-b", "--body", "-f", "--body-file", "-t", "--subject", "--match-head-commit", "-a", "--author-email", "-r", "--repo"}
TOKEN = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")


def fusiones_de(comando):
    """[{objetivo, repo, auto}] de cada `gh pr merge` del comando. «objetivo» es lo que se le pasó (número, URL o rama) o None."""
    res = []
    for m in FUSION.finditer(comando):
        tokens = [t.strip("\"'") for t in TOKEN.findall((m.group("antes") or "") + " " + (m.group("args") or ""))]
        objetivo, repo, auto, i = None, None, False, 0
        while i < len(tokens):
            t = tokens[i]
            bajo = t.lower()
            if bajo in ("-r", "--repo") and i + 1 < len(tokens):
                repo, i = tokens[i + 1], i + 2
                continue
            if bajo.startswith("--repo="):
                repo = t.split("=", 1)[1]
            elif bajo == "--auto":
                auto = True
            elif bajo in CON_VALOR:
                i += 2
                continue
            elif not t.startswith("-") and objetivo is None:
                objetivo = t
            i += 1
        res.append({"objetivo": objetivo, "repo": repo, "auto": auto})
    return res


def numero_de(objetivo):
    if objetivo is None:
        return None
    if objetivo.isdigit():
        return objetivo
    m = re.search(r"/pull/(\d+)", objetivo)
    return m.group(1) if m else None


def estado_ci(cwd, f):
    """(código de ci.py estado, primera línea de lo que dijo). Si no se pudo correr: (3, '')."""
    cmd = [sys.executable, str(CI), "estado", "--raiz", cwd] + (["--pr", f["objetivo"]] if f["objetivo"] else []) + (["--repo", f["repo"]] if f["repo"] else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
    except (OSError, subprocess.TimeoutExpired):
        return 3, ""
    return r.returncode, (r.stdout or "").strip().splitlines()[0] if (r.stdout or "").strip() else ""


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        if datos.get("tool_name") not in ("Bash", "PowerShell"):
            return 0
        comando = str((datos.get("tool_input") or {}).get("command") or "")
        fusiones = fusiones_de(comando) if "merge" in comando else []
        if not fusiones:
            return 0
        import modo_hooks
        cwd = datos.get("cwd") or os.getcwd()
        raiz = modo_hooks.raiz_del_proyecto(cwd)
        bloqueo = None
        for f in fusiones:
            codigo, texto = estado_ci(cwd, f)
            if codigo == 1 or (codigo == 2 and not f["auto"]):
                numero = numero_de(f["objetivo"])
                if modo_hooks.consumir_fusion(raiz, numero):  # el usuario la autorizó de antemano: esta fusión pasa y la autorización se gasta
                    continue
                bloqueo = (f, numero, texto)
                break
    except Exception:  # noqa: BLE001 motivo: si algo falla, el hook deja pasar y no frena nada (con SENIOR_HOOK_DEPURAR=1 el error se ve)
        if os.environ.get("SENIOR_HOOK_DEPURAR") == "1":
            raise
        return 0
    if not bloqueo:
        return 0
    f, numero, texto = bloqueo
    cual = f"el Pull Request {numero}" if numero else ("el Pull Request " + f["objetivo"] if f["objetivo"] else "el Pull Request de la rama actual")
    clave = numero or "actual"
    detalle = f"se intentó fusionar {cual} con chequeos sin verde ({texto.split(': ', 1)[-1] if texto else 'sin detalle'})"
    pregunta = f"Claude quiere fusionar {cual}, pero sus chequeos de CI no están en verde ({texto.split(': ', 1)[-1] if texto else 'sin detalle'}). ¿Autorizás esta fusión?"
    instruccion = ("no se fusiona con chequeos sin verde. Anotá en `docs/pendientes.md`: «Fusionar " + cual + ": chequeos sin verde. Para fusionarlo igual, el usuario escribe en el chat "
                   f"`/permitir-fusion {clave}`» (vos no podés darte esa autorización) y dejalo dicho en tu resumen final. Mientras tanto seguí con otra tarea.")
    print(modo_hooks.respuesta(raiz, "fusión con CI", detalle, pregunta, instruccion))
    return 0


if __name__ == "__main__":
    sys.exit(main())
