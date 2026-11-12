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
    python guardia_autoria.py asegurar [--raiz .] [--silencioso] [--solo-verificar]  # también avisa si lo instalado se desalineó del repositorio
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
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
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


def cargar_secretos():
    """El módulo de secretos: la copia que está junto a este hook o, en el repositorio de la skill, el de la skill `senior`."""
    import importlib.util
    aqui = Path(__file__).resolve().parent
    for ruta in (aqui / "senior_secretos.py", aqui.parent.parent / "senior" / "scripts" / "secretos.py"):
        if ruta.exists():
            spec = importlib.util.spec_from_file_location("senior_secretos", ruta)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            return modulo
    return None


def cmd_prepush(raiz):
    problemas, total = [], 0
    entrada = sys.stdin.read().splitlines()
    secretos = cargar_secretos()
    if secretos is not None:
        hallazgos = secretos.revisar_push(raiz, entrada)
        if hallazgos:
            print(f"PUSH BLOQUEADO: {len(hallazgos)} claves, credenciales o datos personales en lo que se va a subir:", file=sys.stderr)  # senior-ignore: SEC-LOG-SENSIBLE motivo: mensaje fijo, no imprime valores
            secretos.imprimir(hallazgos, sys.stderr)
            print("  " + secretos.mensaje_de_arreglo(hallazgos), file=sys.stderr)  # senior-ignore: SEC-LOG-SENSIBLE motivo: mensaje fijo, no imprime valores
            print("  Quitarlos de los commits (no alcanza con borrarlos en uno nuevo: viajan en el historial) y volver a intentar.", file=sys.stderr)
            return 1
    for linea in entrada:
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
  echo "Guardia de senior: no se encontró un Python que funcione, así que no se pueden comprobar las reglas." >&2
  echo "Instalar Python 3 o quitar la guardia (borrar commit-msg, pre-commit y pre-push de .git/hooks) con aprobación del usuario." >&2
  exit 1
fi
exec "$PY" "$(dirname "$0")/{script}" {modo} "$@"
"""


HOOKS_GIT = (("commit-msg", "mensaje", "senior_guardia_autoria.py"), ("pre-push", "prepush", "senior_guardia_autoria.py"),
             ("pre-commit", "staged", "senior_secretos.py"))


def ruta_secretos():
    """El `secretos.py` de la skill `senior` (instalada o de este repositorio) que se copia junto a los hooks."""
    for ruta in (Path.home() / ".claude" / "skills" / "senior" / "scripts" / "secretos.py", Path(__file__).resolve().parents[2] / "senior" / "scripts" / "secretos.py"):
        if ruta.exists():
            return ruta
    return None


def cmd_instalar(raiz):
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        print("No es un repositorio git.")
        return 1
    ruta_hooks = Path(git(raiz, "rev-parse", "--git-path", "hooks")[0].strip())
    if not ruta_hooks.is_absolute():
        ruta_hooks = (raiz / ruta_hooks).resolve()
    ruta_hooks.mkdir(parents=True, exist_ok=True)
    hechos = []
    for nombre, modo, script in HOOKS_GIT:
        destino = ruta_hooks / nombre
        if destino.exists() and MARCA_HOOK not in destino.read_text(encoding="utf-8", errors="replace"):
            print(f"No se pisa el hook existente {nombre}; integrarlo a mano llamando a senior_guardia_autoria.py {modo}.")
            continue
        destino.write_text(HOOK.format(marca=MARCA_HOOK, modo=modo, script=script), encoding="utf-8", newline="\n")
        destino.chmod(0o755)
        hechos.append(nombre)
    copia = ruta_hooks / "senior_guardia_autoria.py"
    copia.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    origen = ruta_secretos()
    if origen is not None:
        (ruta_hooks / "senior_secretos.py").write_text(origen.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    print(f"Guardia instalada en {ruta_hooks}: {', '.join(hechos) or 'ningún hook nuevo'}. "
          "Bloquea commits y push con atribuciones a Claude, coautores, claves, credenciales y datos personales.")
    return 0


HOOKS_CLAUDE = (  # hooks globales de Claude Code que esta guardia mantiene activos
    {"script": "hook_autoria_claude.py", "skill": "senior-git", "matcher": "Bash|PowerShell",
     "nombre": "de autoría"},
    {"script": "hook_lectura_externa.py", "skill": "senior-relevar", "matcher": "Read|Bash|PowerShell|Write|Edit",
     "nombre": "de lectura de documentos externos"},
    {"script": "hook_fuera_del_proyecto.py", "skill": "senior", "matcher": "Write|Edit|NotebookEdit|Bash|PowerShell",
     "nombre": "de escritura fuera del proyecto"},
    {"script": "hook_archivos_protegidos.py", "skill": "senior", "matcher": "Write|Edit|NotebookEdit",
     "nombre": "de archivos protegidos"},
    {"script": "hook_secretos_claude.py", "skill": "senior", "matcher": "Read|Grep|Write|Edit|NotebookEdit|Bash|PowerShell",
     "nombre": "de secretos y datos personales"},
    {"script": "hook_permisos_chat.py", "skill": "senior", "evento": "UserPromptSubmit", "matcher": None,
     "nombre": "de permisos desde el chat"},
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
    for nombre, _, _ in HOOKS_GIT:
        f = ruta / nombre
        if not f.exists() or MARCA_HOOK not in f.read_text(encoding="utf-8", errors="replace"):
            return False
    origen = ruta_secretos()
    secretos_al_dia = origen is None or ((ruta / "senior_secretos.py").exists()
                                         and (ruta / "senior_secretos.py").read_text(encoding="utf-8", errors="replace") == origen.read_text(encoding="utf-8"))
    return secretos_al_dia and copia.exists() and copia.read_text(encoding="utf-8", errors="replace") == Path(__file__).read_text(encoding="utf-8")


def asegurar_git(raiz, solo_verificar):
    """Devuelve (lineas, falta). `falta` es True si algo no está activo."""
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        return [], False
    if hooks_git_al_dia(raiz):
        return ["hook de Git activo en este repositorio"], False
    if solo_verificar:
        return ["FALTA el hook de Git de este repositorio (commit-msg, pre-commit y pre-push)"], True
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = cmd_instalar(raiz)
    if codigo == 0 and hooks_git_al_dia(raiz):
        return ["activé el hook de Git de este repositorio (commit-msg, pre-commit y pre-push)"], False
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
    lineas, falta, cambio = [], False, False
    for hook in HOOKS_CLAUDE:
        previos = ajustes.setdefault("hooks", {}).setdefault(hook.get("evento", "PreToolUse"), [])
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
            grupo_nuevo = {"hooks": [{"type": "command", "command": comando}]}
            if hook.get("matcher"):
                grupo_nuevo = {"matcher": hook["matcher"], **grupo_nuevo}
            previos.append(grupo_nuevo)
        lineas.append(f"activé el hook global de Claude Code {hook['nombre']} (se aplica al abrir una sesión nueva)")
        cambio = True
    if cambio:
        destino.parent.mkdir(parents=True, exist_ok=True)
        respaldo = destino.with_name("settings.json.bak-senior")
        if destino.exists() and not respaldo.exists():
            shutil.copyfile(destino, respaldo)
        destino.write_text(json.dumps(ajustes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return lineas, falta


SUFIJOS_TEXTO = {".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".sh", ".yml", ".yaml"}


def huella_archivo(ruta):
    """Huella de un archivo con el fin de línea normalizado (así es como `instalar.py` lo copia)."""
    datos = Path(ruta).read_bytes()
    if Path(ruta).suffix.lower() in SUFIJOS_TEXTO:
        datos = datos.replace(b"\r\n", b"\n")
    return hashlib.sha256(datos).hexdigest()


def huella_skill(carpeta):
    h = hashlib.sha256()
    for f in sorted(p for p in Path(carpeta).rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(f.relative_to(carpeta).as_posix().encode("utf-8"))
        h.update(huella_archivo(f).encode())
    return h.hexdigest()


def huellas_de(carpeta, nombres=None):
    """{skill: huella} de las skills de una carpeta (solo las de `nombres`, si se indican)."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return {}
    return {d.name: huella_skill(d) for d in sorted(carpeta.iterdir()) if d.is_dir() and (nombres is None or d.name in nombres)}


def ruta_manifiesto():
    return Path.home() / ".claude" / "skills" / ".senior-instalacion.json"


def escribir_manifiesto(skills_origen):
    """Anota de dónde se instaló y la huella de cada skill, para poder avisar si el repositorio cambia o lo instalado se toca."""
    skills_origen = Path(skills_origen).resolve()
    datos = {"origen": skills_origen.parent.as_posix(), "fecha": time.strftime("%Y-%m-%d %H:%M"), "skills": huellas_de(skills_origen)}
    destino = ruta_manifiesto()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def asegurar_instalacion():
    """Líneas sobre si lo instalado en ~/.claude/skills coincide con el repositorio del que salió. Los hooks usan las copias instaladas."""
    manifiesto = ruta_manifiesto()
    if not manifiesto.exists():
        return ["AVISO: la instalación de las skills no tiene registro, así que no se puede comprobar si está al día (se crea la próxima vez que se ejecute `python instalar.py`)"]
    try:
        datos = json.loads(manifiesto.read_text(encoding="utf-8-sig"))
        registradas = dict(datos["skills"])
        origen = Path(datos["origen"])
    except (ValueError, KeyError, TypeError):
        return ["AVISO: el registro de la instalación de las skills está dañado (se rehace con `python instalar.py`)"]
    lineas = []
    instaladas = huellas_de(manifiesto.parent, set(registradas))
    a_mano = sorted(n for n in registradas if instaladas.get(n) != registradas[n])
    if a_mano:
        lineas.append("AVISO: hay skills instaladas que se modificaron después de instalarlas (" + ", ".join(a_mano[:5]) + "): los hooks usan esas copias; para volver a lo del repositorio, `python instalar.py`")
    if not (origen / "skills").is_dir():
        lineas.append(f"AVISO: no se encuentra el repositorio de origen de la instalación ({origen.as_posix()}), así que no se puede comprobar si hay cambios sin instalar")
        return lineas
    del_repo = huellas_de(origen / "skills")
    cambiadas = sorted(n for n in del_repo if registradas.get(n) != del_repo[n])
    if cambiadas:
        lineas.append(f"AVISO: el repositorio de la skill ({origen.as_posix()}) tiene cambios que no están instalados (" + ", ".join(cambiadas[:6])
                      + (f" y {len(cambiadas) - 6} más" if len(cambiadas) > 6 else "") + f"): los hooks siguen usando la versión instalada; ejecutar `python {(origen / 'instalar.py').as_posix()}`")
    return lineas


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
    lineas += asegurar_instalacion()
    cambios = [l for l in lineas if l.startswith(("activé", "NO", "FALTA", "AVISO"))]
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
