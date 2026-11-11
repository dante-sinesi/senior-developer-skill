#!/usr/bin/env python3
"""Guardia de autoría: en lo que se sube a GitHub figura únicamente el usuario.

REGLA INVIOLABLE: ni Claude ni ninguna herramienta de IA aparece como autor,
coautor o colaborador de commits, Pull Requests, Issues ni documentos.

Uso:
    python guardia_autoria.py comprobar [--raiz .] [--base main]   # revisa los commits nuevos de la rama
    python guardia_autoria.py mensaje <archivo>                    # revisa un texto: mensaje de commit, PR, Issue
    python guardia_autoria.py prepush                              # para el hook pre-push (lee stdin de git)
    python guardia_autoria.py instalar [--raiz .]                  # instala los hooks de Git de este repositorio
    python guardia_autoria.py identidad [--raiz .] [--nombre <usuario> --correo <correo>]
        # resuelve en nombre de quién se hacen los commits de este repositorio (ver más abajo)
    python guardia_autoria.py asegurar [--raiz .] [--silencioso] [--solo-verificar]
        # comprueba que estén activos los hooks de Git del repositorio y el hook global de Claude Code
        # (~/.claude/settings.json: autoría y lectura de documentos externos) y, si falta alguno, lo activa. El usuario lo autorizó de forma permanente.

Identidad: NO viene fija con la skill. En nombre de quién se hace el trabajo se resuelve así, en orden: la
identidad local del repositorio (git config --local), la sesión de GitHub que ya tenga el usuario (`gh`, con su
correo noreply) y, si no hay ninguna, se le PREGUNTA al usuario (nombre de usuario de GitHub y correo) antes del
primer commit. Nunca se asume ni se inventa una identidad, y nunca se toca la configuración global de git.

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
import contextlib
import io
import json
import os
import re
import shutil
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


HOOKS_CLAUDE = (  # hooks globales de Claude Code que esta guardia mantiene activos
    {"script": "hook_autoria_claude.py", "skill": "senior-git", "matcher": "Bash|PowerShell",
     "nombre": "de autoría"},
    {"script": "hook_lectura_externa.py", "skill": "senior-relevar", "matcher": "Read|Bash|PowerShell|Write|Edit",
     "nombre": "de lectura de documentos externos"},
)


def python_que_funciona():
    """Primer intérprete que de verdad ejecuta (en Windows `python3` puede ser un acceso directo roto)."""
    for c in ("python", "python3", "py"):
        try:
            if subprocess.run([c, "-c", "import sys"], capture_output=True, timeout=20).returncode == 0:
                return c
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


def ruta_hook_claude(hook):
    """Ruta estable del hook: la instalada en ~/.claude/skills si existe; si no, la de este repositorio."""
    instalada = Path.home() / ".claude" / "skills" / hook["skill"] / "scripts" / hook["script"]
    if instalada.exists():
        return instalada
    return Path(__file__).resolve().parents[2] / hook["skill"] / "scripts" / hook["script"]


def hooks_git_al_dia(raiz):
    ruta = Path(git(raiz, "rev-parse", "--git-path", "hooks")[0].strip())
    if not ruta.is_absolute():
        ruta = (raiz / ruta).resolve()
    copia = ruta / "senior_guardia_autoria.py"
    for nombre in ("commit-msg", "pre-push"):
        f = ruta / nombre
        if not f.exists() or MARCA_HOOK not in f.read_text(encoding="utf-8", errors="replace"):
            return False
    return copia.exists() and copia.read_text(encoding="utf-8", errors="replace") == Path(__file__).read_text(encoding="utf-8")


def asegurar_git(raiz, solo_verificar):
    """Devuelve (lineas, falta). `falta` es True si algo no está activo."""
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        return [], False
    if hooks_git_al_dia(raiz):
        return ["hook de Git activo en este repositorio"], False
    if solo_verificar:
        return ["FALTA el hook de Git de este repositorio (commit-msg y pre-push)"], True
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = cmd_instalar(raiz)
    if codigo == 0 and hooks_git_al_dia(raiz):
        return ["activé el hook de Git de este repositorio (commit-msg y pre-push)"], False
    return ["NO se pudo activar el hook de Git: " + salida.getvalue().strip()[:160]], True


def asegurar_claude(solo_verificar):
    """Garantiza los hooks globales de Claude Code en ~/.claude/settings.json. Devuelve (lineas, falta)."""
    destino = Path.home() / ".claude" / "settings.json"
    ajustes = {}
    if destino.exists():
        try:
            ajustes = json.loads(destino.read_text(encoding="utf-8-sig"))
        except ValueError:
            return ["NO se tocó ~/.claude/settings.json porque no es un JSON válido; corregirlo y repetir"], True
    if not isinstance(ajustes, dict):
        return ["NO se tocó ~/.claude/settings.json: tiene una estructura inesperada"], True
    previos = ajustes.setdefault("hooks", {}).setdefault("PreToolUse", [])
    lineas, falta, cambio = [], False, False
    for hook in HOOKS_CLAUDE:
        script = ruta_hook_claude(hook)
        entrada = None
        for grupo in previos:
            for h in grupo.get("hooks", []) if isinstance(grupo, dict) else []:
                if hook["script"] in str(h.get("command", "")):
                    entrada = h
        if entrada is not None:
            m = re.search(r'"([^"]*' + re.escape(hook["script"]) + r')"', entrada["command"])
            if m and Path(m.group(1)).exists():
                lineas.append(f"hook global de Claude Code {hook['nombre']} activo")
                continue
        if solo_verificar:
            lineas.append(f"FALTA el hook global de Claude Code {hook['nombre']} (~/.claude/settings.json)")
            falta = True
            continue
        py = python_que_funciona()
        if not py or not script.exists():
            lineas.append(f"NO se pudo activar el hook global de Claude Code {hook['nombre']}: " +
                          ("no hay un Python que funcione" if not py else f"no existe {script}"))
            falta = True
            continue
        comando = f'{py} "{script.as_posix()}"'
        if entrada is not None:
            entrada["command"] = comando
        else:
            previos.append({"matcher": hook["matcher"], "hooks": [{"type": "command", "command": comando}]})
        lineas.append(f"activé el hook global de Claude Code {hook['nombre']} (se aplica al abrir una sesión nueva)")
        cambio = True
    if cambio:
        destino.parent.mkdir(parents=True, exist_ok=True)
        respaldo = destino.with_name("settings.json.bak-senior")
        if destino.exists() and not respaldo.exists():
            shutil.copyfile(destino, respaldo)
        destino.write_text(json.dumps(ajustes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return lineas, falta


def git_config_local(raiz, clave):
    return git(raiz, "config", "--local", "--get", clave)[0].strip()


def identidad_de_github():
    """(login, correo noreply) de la sesión de `gh` si está iniciada; si no, (None, None)."""
    gh = shutil.which("gh")
    if not gh:
        return None, None
    try:
        p = subprocess.run([gh, "api", "user", "--jq", '.login + " " + (.id|tostring)'], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    partes = p.stdout.split()
    if p.returncode != 0 or len(partes) != 2:
        return None, None
    return partes[0], f"{partes[1]}+{partes[0]}@users.noreply.github.com"


def asegurar_identidad(raiz, solo_verificar):
    """Garantiza en nombre de quién se hacen los commits del repositorio. Devuelve (lineas, falta)."""
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        return [], False
    nombre, correo = git_config_local(raiz, "user.name"), git_config_local(raiz, "user.email")
    if nombre and correo:
        return [f"identidad de Git del repositorio: {nombre}"], False
    login, noreply = identidad_de_github()
    if login and not solo_verificar:
        git(raiz, "config", "--local", "user.name", login)
        git(raiz, "config", "--local", "user.email", noreply)
        return [f"configuré la identidad local de Git con la sesión de GitHub ({login})"], False
    if login:
        return [f"FALTA la identidad local de Git (la sesión de GitHub es {login}: `guardia_autoria.py asegurar` la configura)"], True
    return ["FALTA la identidad de Git: no hay identidad local ni sesión de GitHub. PREGUNTAR al usuario en nombre de quién se "
            "hace el trabajo (su nombre de usuario de GitHub y su correo, mejor el noreply) y configurarla con "
            "`guardia_autoria.py identidad --nombre <usuario> --correo <correo>`; no asumir ninguna identidad"], True


def cmd_identidad(raiz, nombre, correo):
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        print("No es un repositorio git.")
        return 1
    if nombre or correo:
        if not (nombre and correo):
            print("Para fijar la identidad hacen falta --nombre y --correo.")
            return 1
        git(raiz, "config", "--local", "user.name", nombre)
        git(raiz, "config", "--local", "user.email", correo)
        print(f"Identidad local del repositorio: {nombre} <{correo}>.")
        return 0
    lineas, falta = asegurar_identidad(raiz, False)
    for l in lineas:
        print(f"Guardia de autoría: {l}.")
    return 1 if falta else 0


def cmd_asegurar(raiz, silencioso, solo_verificar):
    lineas, falta = [], False
    for l, f in (asegurar_git(raiz, solo_verificar), asegurar_identidad(raiz, solo_verificar), asegurar_claude(solo_verificar)):
        lineas += l
        falta = falta or f
    cambios = [l for l in lineas if l.startswith(("activé", "NO", "FALTA"))]
    if silencioso and not cambios:
        return 0
    for l in (cambios if silencioso else lineas):
        print(f"Guardia de autoría: {l}.")
    return 1 if falta and solo_verificar else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["comprobar", "mensaje", "prepush", "instalar", "asegurar", "identidad"])
    ap.add_argument("archivo", nargs="*")  # pre-push recibe además el nombre y la URL del remoto: se ignoran
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--base", default=None)
    ap.add_argument("--silencioso", action="store_true")
    ap.add_argument("--nombre", default=None, help="identidad: nombre de usuario de GitHub")
    ap.add_argument("--correo", default=None, help="identidad: correo (mejor el noreply de GitHub)")
    ap.add_argument("--solo-verificar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if args.accion == "comprobar":
        sys.exit(cmd_comprobar(raiz, args.base))
    if args.accion == "mensaje":
        if not args.archivo:
            ap.error("'mensaje' necesita un archivo")
        sys.exit(cmd_mensaje(args.archivo[0]))
    if args.accion == "prepush":
        sys.exit(cmd_prepush(Path.cwd()))
    if args.accion == "identidad":
        sys.exit(cmd_identidad(raiz, args.nombre, args.correo))
    if args.accion == "asegurar":
        sys.exit(cmd_asegurar(raiz, args.silencioso, args.solo_verificar))
    sys.exit(cmd_instalar(raiz))


if __name__ == "__main__":
    main()
