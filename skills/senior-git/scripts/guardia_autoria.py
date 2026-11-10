#!/usr/bin/env python3
"""Guardia de autoría: en lo que se sube a GitHub figura únicamente el usuario.

REGLA INVIOLABLE: ni Claude ni ninguna herramienta de IA aparece como autor,
coautor o colaborador de commits, Pull Requests, Issues ni documentos.

Uso:
    python guardia_autoria.py comprobar [--raiz .] [--base main]   # revisa los commits nuevos de la rama
    python guardia_autoria.py mensaje <archivo>                    # revisa un texto: mensaje de commit, PR, Issue
    python guardia_autoria.py prepush                              # para el hook pre-push (lee stdin de git)
    python guardia_autoria.py instalar [--raiz .]                  # instala los hooks locales (pedir aprobación antes)

Qué se prohíbe:
  - líneas Co-Authored-By (de cualquier persona o herramienta; el usuario puede
    permitirlas a propósito con la variable SENIOR_PERMITIR_COAUTORES=1)
  - pies de atribución como "Generated with Claude Code" o el emoji 🤖
  - Signed-off-by / Reviewed-by / Assisted-by que nombren a Claude o Anthropic
  - autor o committer cuyo nombre o correo contenga "claude" o "anthropic"
Aviso (no bloquea): autor distinto de la identidad configurada en git.

Códigos de salida: 0 sin problemas, 1 con problemas. Solo biblioteca estándar.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

MARCA_HOOK = "# senior-guardia-autoria"
CEROS = "0" * 40
PROHIBIDO_TEXTO = [
    (re.compile(r"(?im)^\s*co-authored-by\s*:"), "línea Co-Authored-By"),
    (re.compile(r"(?i)generated\s+(with|by)\b.{0,40}(claude|anthropic|\bai\b)"), "pie de atribución «Generated with …»"),
    (re.compile("\U0001F916"), "emoji de atribución (robot)"),
    (re.compile(r"(?im)^\s*(signed-off-by|reviewed-by|assisted-by)\s*:.*(claude|anthropic)"), "trailer que nombra a Claude/Anthropic"),
]
IDENTIDAD_IA = re.compile(r"(?i)claude|anthropic")


def permitir_coautores():
    return os.environ.get("SENIOR_PERMITIR_COAUTORES") == "1"


def problemas_de_texto(texto):
    res = []
    for rx, nombre in PROHIBIDO_TEXTO:
        if rx.search(texto):
            if nombre == "línea Co-Authored-By" and permitir_coautores():
                continue
            res.append(nombre)
    return res


def git(raiz, *args, entrada=None):
    p = subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8", errors="replace",
                       input=entrada, timeout=60)
    return p.stdout, p.returncode


def commits(raiz, args_log):
    """Devuelve lista de dicts de los commits que produce `git log <args_log>`."""
    sep, fin = "\x1f", "\x1e"
    salida, codigo = git(raiz, "log", f"--format=%H{sep}%an{sep}%ae{sep}%cn{sep}%ce{sep}%B{fin}", *args_log)
    if codigo != 0:
        return []
    res = []
    for bloque in salida.split(fin):
        partes = bloque.strip("\n").split(sep)
        if len(partes) == 6:
            res.append({"sha": partes[0][:8], "autor": partes[1], "autor_mail": partes[2],
                        "committer": partes[3], "committer_mail": partes[4], "mensaje": partes[5]})
    return res


def revisar(raiz, lista):
    problemas, avisos = [], []
    yo_nombre = git(raiz, "config", "user.name")[0].strip()
    for c in lista:
        for p in problemas_de_texto(c["mensaje"]):
            problemas.append(f"Commit {c['sha']}: {p}")
        for rol, nombre, mail in (("autor", c["autor"], c["autor_mail"]),
                                  ("committer", c["committer"], c["committer_mail"])):
            if IDENTIDAD_IA.search(nombre) or IDENTIDAD_IA.search(mail):
                problemas.append(f"Commit {c['sha']}: el {rol} es «{nombre}» (solo debe figurar el usuario)")
        if yo_nombre and c["autor"] != yo_nombre:
            avisos.append(f"Commit {c['sha']}: autor «{c['autor']}» distinto de la identidad configurada «{yo_nombre}»")
    return problemas, avisos


def rango_por_defecto(raiz, base):
    if base:
        return [f"{base}..HEAD"]
    salida, codigo = git(raiz, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if codigo == 0 and salida.strip():
        return [f"{salida.strip()}..HEAD"]
    for candidata in ("main", "master"):
        if git(raiz, "rev-parse", "--verify", "--quiet", candidata)[1] == 0 and \
                git(raiz, "rev-parse", "--abbrev-ref", "HEAD")[0].strip() != candidata:
            return [f"{candidata}..HEAD"]
    return ["-n", "1", "HEAD"]


def cmd_comprobar(raiz, base):
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        print("Autoría: no es un repositorio git.")
        return 0
    lista = commits(raiz, rango_por_defecto(raiz, base))
    problemas, avisos = revisar(raiz, lista)
    for a in avisos:
        print(f"  aviso: {a}")
    if problemas:
        print(f"Autoría: {len(problemas)} problemas en {len(lista)} commits. En lo que se sube solo debe figurar el usuario:")
        for p in problemas:
            print(f"  {p}")
        print("  Corregir con `git commit --amend` / `git rebase -i` (sin la línea o el autor) ANTES de subir.")
        return 1
    print(f"Autoría: {len(lista)} commits revisados, sin rastro de Claude ni coautores.")
    return 0


def cmd_mensaje(archivo):
    texto = Path(archivo).read_text(encoding="utf-8-sig", errors="replace")
    texto = "\n".join(l for l in texto.splitlines() if not l.startswith("#"))  # comentarios del editor de git
    problemas = problemas_de_texto(texto)
    if problemas:
        print("Autoría: el texto no puede incluir atribuciones a Claude ni coautores:")
        for p in problemas:
            print(f"  - {p}")
        print("  Quitarlas: en lo que se sube a GitHub figura únicamente el usuario.")
        return 1
    return 0


def cmd_prepush(raiz):
    problemas, total = [], 0
    for linea in sys.stdin.read().splitlines():
        partes = linea.split()
        if len(partes) < 4 or partes[1] == CEROS:
            continue
        _, local_sha, _, remoto_sha = partes[:4]
        args_log = [local_sha, "--not", "--remotes"] if remoto_sha == CEROS else [f"{remoto_sha}..{local_sha}"]
        lista = commits(raiz, args_log)
        total += len(lista)
        p, _ = revisar(raiz, lista)
        problemas += p
    if problemas:
        print(f"PUSH BLOQUEADO: {len(problemas)} problemas de autoría en {total} commits:", file=sys.stderr)
        for p in problemas:
            print(f"  {p}", file=sys.stderr)
        print("  En lo que se sube solo debe figurar el usuario. Corregir los commits y volver a intentar.", file=sys.stderr)
        return 1
    return 0


# Se prueba que cada intérprete ejecute de verdad: en Windows `python3` suele ser un acceso directo de
# la Microsoft Store que existe pero no funciona. Si ninguno sirve, la guardia falla cerrada (bloquea y avisa).
HOOK = """#!/bin/sh
{marca}
PY=""
for c in python python3 py; do
  if "$c" -c "import sys" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Guardia de autoría: no se encontró un Python que funcione, así que no se puede comprobar la regla." >&2
  echo "Instalar Python 3 o quitar la guardia (borrar commit-msg y pre-push de .git/hooks) con aprobación del usuario." >&2
  exit 1
fi
exec "$PY" "$(dirname "$0")/senior_guardia_autoria.py" {modo} "$@"
"""


def cmd_instalar(raiz):
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        print("No es un repositorio git.")
        return 1
    ruta_hooks = Path(git(raiz, "rev-parse", "--git-path", "hooks")[0].strip())
    if not ruta_hooks.is_absolute():
        ruta_hooks = (raiz / ruta_hooks).resolve()
    ruta_hooks.mkdir(parents=True, exist_ok=True)
    hechos = []
    for nombre, modo in (("commit-msg", "mensaje"), ("pre-push", "prepush")):
        destino = ruta_hooks / nombre
        if destino.exists() and MARCA_HOOK not in destino.read_text(encoding="utf-8", errors="replace"):
            print(f"No se pisa el hook existente {nombre}; integrarlo a mano llamando a senior_guardia_autoria.py {modo}.")
            continue
        destino.write_text(HOOK.format(marca=MARCA_HOOK, modo=modo), encoding="utf-8", newline="\n")
        destino.chmod(0o755)
        hechos.append(nombre)
    copia = ruta_hooks / "senior_guardia_autoria.py"
    copia.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    print(f"Guardia instalada en {ruta_hooks}: {', '.join(hechos) or 'ningún hook nuevo'}. "
          "Bloquea commits y push con atribuciones a Claude o coautores.")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["comprobar", "mensaje", "prepush", "instalar"])
    ap.add_argument("archivo", nargs="?")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--base", default=None)
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if args.accion == "comprobar":
        sys.exit(cmd_comprobar(raiz, args.base))
    if args.accion == "mensaje":
        if not args.archivo:
            ap.error("'mensaje' necesita un archivo")
        sys.exit(cmd_mensaje(args.archivo))
    if args.accion == "prepush":
        sys.exit(cmd_prepush(Path.cwd()))
    sys.exit(cmd_instalar(raiz))


if __name__ == "__main__":
    main()
