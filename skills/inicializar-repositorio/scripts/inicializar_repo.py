#!/usr/bin/env python3
"""Inicializa un proyecto como repositorio de GitHub y sube lo que haya, sin tener que armar cada paso a mano.

Dado el repositorio (un enlace, `dueño/nombre` o solo el nombre), deja la carpeta lista y publicada:
  1. identidad de Git del repositorio, solo local, con la sesión de GitHub (`gh`): nunca la configuración global;
  2. `git init` en `main` si la carpeta todavía no es un repositorio, y el `.gitignore` con los archivos de secretos;
  3. `README.md`, si no hay (título, descripción y lo que contiene la carpeta);
  4. el repositorio remoto: si no existe, se crea (público o privado: hay que decirlo) y se lo asocia como `origin`;
  5. la DESCRIPCIÓN y los TOPICS, que son obligatorios (`senior-git/scripts/repo_meta.py`: valida, no pisa lo ajeno y comprueba);
  6. los hooks de Git del repositorio (autoría y secretos) y un escaneo de claves y datos personales ANTES de commitear;
  7. los commits (`chore: inicializa el repositorio` y, si ya había archivos, `chore: agrega el contenido existente`) y el push.

Uso:
    python inicializar_repo.py <repo> [--raiz .] [--publico | --privado] --descripcion "…" --topics a,b,c [--aplicar] [--sin-subir]

  <repo>       https://github.com/dueño/nombre, git@github.com:dueño/nombre.git, dueño/nombre, o solo el nombre (el dueño es
               el usuario de la sesión de `gh`).
  Sin --aplicar solo muestra el plan y no escribe nada. Con --aplicar hace todo lo anterior; si algo BLOQUEA, no hace nada.
  --publico / --privado  obligatorio solo si el repositorio hay que crearlo: no se decide por el usuario.
  --sin-subir  hace todo menos el push.
  --anidado    la carpeta está dentro de OTRO repositorio de Git (no es su raíz) y se quiere uno propio acá; sin esto bloquea,
               porque inicializar o commitear ahí tocaría el repositorio de afuera.

Lo que NUNCA hace: forzar un push, mezclar la historia local con un remoto que ya tiene contenido distinto, pisar una
descripción que no puso senior, subir una carpeta con claves o datos personales a la vista, tocar la configuración global de
git ni abrir Pull Requests. Código de salida: 0 todo listo, 1 hay algo que bloquea o falló.
Solo biblioteca estándar; usa `gh` y `git`.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
GITIGNORE_BASE = ["__pycache__/", "*.pyc", ".DS_Store", "Thumbs.db"]
MAX_ENTRADAS_README = 15


def cargar(skill, archivo):
    ruta = SKILLS / skill / "scripts" / archivo
    if not ruta.exists():
        sys.exit(f"Falta {ruta}: este comando necesita las skills senior-git y senior instaladas juntas.")
    espec = importlib.util.spec_from_file_location(f"ir_{ruta.stem}", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


def gh_cmd():
    """`gh` como lista; la variable SENIOR_GH (una lista JSON) lo reemplaza para poder probar sin red."""
    env = os.environ.get("SENIOR_GH")
    if env:
        return list(json.loads(env))
    ruta = shutil.which("gh")
    return [ruta] if ruta else None


def correr(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def gh(*args, cwd=None):
    base = gh_cmd()
    if not base:
        return 127, "no está instalado `gh`"
    return correr([*base, *args], cwd=cwd)


def git(raiz, *args):
    return correr(["git", *args], cwd=raiz)


def interpretar_repo(texto, login):
    """(dueño, nombre) de un enlace, `dueño/nombre` o un nombre solo; None si no se entiende."""
    t = texto.strip()
    m = re.match(r"^(?:https?://github\.com/|git@github\.com:)([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", t)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9._-]+)$", t)
    if m:
        return m.group(1), m.group(2)
    if re.match(r"^[A-Za-z0-9._-]+$", t) and login:
        return login, t
    return None


def sesion_de_github():
    """(login, correo noreply) de la sesión de gh, o (None, None)."""
    rc, salida = gh("api", "user", "--jq", '.login + " " + (.id|tostring)')
    partes = salida.split()
    if rc != 0 or len(partes) != 2:
        return None, None
    return partes[0], f"{partes[1]}+{partes[0]}@users.noreply.github.com"


def estado_remoto(dueno, nombre):
    """{'existe', 'vacio', 'privado', 'url', 'permiso'} o {'error': texto}."""
    rc, salida = gh("repo", "view", f"{dueno}/{nombre}", "--json", "isEmpty,isPrivate,url,viewerPermission")
    if rc != 0:
        if "Could not resolve" in salida or "not found" in salida.lower():
            return {"existe": False}
        return {"error": salida[:200]}
    try:
        d = json.loads(salida)
    except ValueError:
        return {"error": "respuesta ilegible de gh"}
    return {"existe": True, "vacio": bool(d.get("isEmpty")), "privado": bool(d.get("isPrivate")), "url": d.get("url", ""), "permiso": d.get("viewerPermission", "")}


def mismo_repo(url, dueno, nombre):
    limpio = re.sub(r"\.git$", "", url.strip().replace("\\", "/")).lower()
    return limpio.endswith(f"{dueno}/{nombre}".lower())


def entradas_de_la_carpeta(raiz):
    return sorted(p.name + ("/" if p.is_dir() else "") for p in raiz.iterdir()
                  if not p.name.startswith(".") and p.name.lower() != "readme.md" and p.name not in ("__pycache__", "node_modules"))


def escribir_readme(raiz, nombre, descripcion):
    lineas = [f"# {nombre}", "", descripcion, ""]
    entradas = entradas_de_la_carpeta(raiz)
    if entradas:
        lineas += ["## Contenido", ""] + [f"- `{e}`" for e in entradas[:MAX_ENTRADAS_README]]
        if len(entradas) > MAX_ENTRADAS_README:
            lineas.append(f"- … y {len(entradas) - MAX_ENTRADAS_README} más")
        lineas.append("")
    (raiz / "README.md").write_text("\n".join(lineas), encoding="utf-8", newline="\n")


def completar_gitignore(raiz, secretos):
    """Crea el .gitignore si falta (con lo común) y le suma el bloque de secretos. Devuelve True si cambió algo."""
    ruta = raiz / ".gitignore"
    cambio = False
    if not ruta.exists():
        ruta.write_text("\n".join(GITIGNORE_BASE) + "\n", encoding="utf-8", newline="\n")
        cambio = True
    return bool(secretos.completar_gitignore(raiz)) or cambio


def analizar(args, raiz, secretos, meta):
    """Todo lo que hace falta saber para decidir: el plan y lo que bloquea. No escribe nada."""
    r = {"bloqueos": [], "avisos": [], "acciones": [], "hallazgos": []}
    login, noreply = sesion_de_github()
    r["login"], r["noreply"] = login, noreply
    if not login:
        r["bloqueos"].append("no hay sesión de GitHub (`gh auth login`): sin ella no se puede crear el repositorio ni resolver la identidad. "
                             "Si el usuario prefiere otra identidad, preguntarle en nombre de quién se hace el trabajo.")
    destino = interpretar_repo(args.repo, login)
    if not destino:
        r["bloqueos"].append(f"no se entiende el repositorio «{args.repo}»: pasar un enlace de GitHub, `dueño/nombre` o el nombre.")
        return r
    dueno, nombre = destino
    r["dueno"], r["nombre"] = dueno, nombre
    # remoto
    remoto = estado_remoto(dueno, nombre) if login else {"error": "sin sesión de GitHub"}
    r["remoto"] = remoto
    if "error" in remoto:
        r["bloqueos"].append(f"no se pudo consultar GitHub: {remoto['error']}")
    elif not remoto["existe"]:
        if not (args.publico or args.privado):
            r["bloqueos"].append(f"el repositorio {dueno}/{nombre} no existe y hay que crearlo: decir si es público (`--publico`) o privado (`--privado`).")
        else:
            r["acciones"].append(f"crear {dueno}/{nombre} en GitHub como {'público' if args.publico else 'privado'}")
    else:
        if remoto["permiso"] not in ("ADMIN", "MAINTAIN", "WRITE"):
            r["bloqueos"].append(f"la sesión de GitHub tiene permiso «{remoto['permiso']}» sobre {dueno}/{nombre}: hace falta poder escribir.")
        if not remoto["vacio"]:
            r["avisos"].append("el repositorio remoto ya tiene contenido: solo se sube si la historia local lo contiene; nunca se mezcla ni se fuerza.")
    # local
    rc_top, top = git(raiz, "rev-parse", "--show-toplevel")
    afuera = Path(top.strip()).resolve() if rc_top == 0 and top.strip() else None
    es_git = afuera is not None and afuera == raiz.resolve()
    if afuera is not None and not es_git:  # la carpeta está DENTRO de otro repositorio: no es la raíz de uno propio
        if not args.anidado:
            r["bloqueos"].append(f"esta carpeta está dentro del repositorio de Git de {afuera.as_posix()}: sin `--anidado` no se inicializa uno propio "
                                 "(y nunca se commitea en el de afuera).")
        else:
            r["avisos"].append(f"la carpeta está dentro del repositorio de {afuera.as_posix()}; con --anidado se crea uno propio aparte.")
    r["es_git"] = es_git
    commits = int(git(raiz, "rev-list", "--count", "HEAD")[1].strip() or 0) if es_git and git(raiz, "rev-parse", "--verify", "HEAD")[0] == 0 else 0
    r["commits"] = commits
    if es_git:
        origen = git(raiz, "remote", "get-url", "origin")[1].strip() if git(raiz, "remote", "get-url", "origin")[0] == 0 else ""
        if origen and not mismo_repo(origen, dueno, nombre) and not (remoto.get("url") and origen.replace("\\", "/") == remoto["url"].replace("\\", "/")):
            r["bloqueos"].append(f"esta carpeta ya tiene un `origin` distinto ({origen}): no se cambia por su cuenta.")
        r["origen"] = origen
        r["acciones"].append(f"usar el repositorio de Git que ya hay ({commits} commits)")
    else:
        r["acciones"].append("inicializar Git en `main`")
        if remoto.get("existe") and not remoto.get("vacio"):
            r["bloqueos"].append("el remoto ya tiene contenido y esta carpeta no es un repositorio: no se mezclan. Clonar el repositorio o elegir otro nombre.")
    # descripción y topics: obligatorios
    tecs = meta.tecnologias(raiz)
    titulo, intro = meta.presentacion(raiz)
    r["tecs"], r["borrador"] = tecs, meta.borrador_descripcion(intro)
    topics = list(dict.fromkeys([t.strip().lower() for t in (args.topics or "").split(",") if t.strip()] + tecs)) if args.topics is not None else None
    r["descripcion"], r["topics"] = args.descripcion, topics
    if not args.descripcion or not topics:
        faltan = [x for x, v in (("--descripcion", args.descripcion), ("--topics", topics)) if not v]
        r["bloqueos"].append(f"la descripción y los topics son obligatorios: falta {' y '.join(faltan)}. Propuesta: "
                             f"descripción «{r['borrador'] or '(el README no tiene un párrafo de presentación: redactarla)'}»; topics que se deducen solos: {', '.join(tecs) or '(ninguno)'} "
                             "más los de dominio, que se eligen leyendo el proyecto.")
    else:
        for e in meta.validar(args.descripcion, topics):
            r["bloqueos"].append(f"descripción o topics no válidos: {e}.")
    # archivos y secretos
    r["falta_readme"] = not (raiz / "README.md").exists()
    r["acciones"].append("crear el README.md" if r["falta_readme"] else "conservar el README.md que hay")
    r["acciones"].append("completar el .gitignore con los archivos de secretos y activar los hooks de Git (autoría y secretos)")
    if es_git:
        hallazgos = secretos.versionados_que_no_deben(raiz) + secretos.escanear_todo(raiz)
    else:  # sin git todavía: lo que el .gitignore de secretos va a dejar afuera no se cuenta
        hallazgos = []
        for p in sorted(raiz.rglob("*")):
            rel = p.relative_to(raiz).as_posix()
            if not p.is_file() or set(p.relative_to(raiz).parts) & secretos.IGNORAR or secretos.hallazgos_de_ruta(rel):
                continue
            try:
                hallazgos += secretos.escanear_texto(rel, p.read_text(encoding="utf-8", errors="replace")) if p.stat().st_size < secretos.MAX_BYTES else []
            except OSError:
                continue
    r["hallazgos"] = hallazgos
    if hallazgos:
        r["bloqueos"].append(f"hay {len(hallazgos)} claves, credenciales o datos personales a la vista: no se sube nada hasta resolverlos "
                             f"(ver `secretos.py todo`; una clave que ya estuvo a la vista se rota).")
    r["acciones"].append("commitear lo que haya (README y .gitignore, y el contenido existente)" + ("" if not args.sin_subir else " (sin subir)"))
    if not args.sin_subir:
        r["acciones"].append("subir a `origin/main` (sin forzar)")
    return r


def mostrar(r, raiz, aplicar):
    print(f"Inicializar {r.get('dueno', '?')}/{r.get('nombre', '?')} desde {raiz}")
    remoto = r.get("remoto") or {}
    if remoto.get("existe"):
        print(f"  Remoto: existe ({'vacío' if remoto['vacio'] else 'con contenido'}, {'privado' if remoto['privado'] else 'público'}).")
    elif "existe" in remoto:
        print("  Remoto: no existe.")
    if "es_git" in r:
        print("  Local: " + (f"repositorio de Git con {r['commits']} commits." if r["es_git"] else "no es un repositorio de Git."))
    if r.get("descripcion"):
        print(f"  Descripción: {r['descripcion']}")
    if r.get("topics"):
        print(f"  Topics: {', '.join(r['topics'])}")
    for a in r["acciones"]:
        print(f"  - {a}")
    for a in r["avisos"]:
        print(f"  AVISO {a}")
    for h in r["hallazgos"][:8]:
        print(f"  SECRETO {h['id']} {h['archivo']}" + (f":{h['linea']}" if h["linea"] else "") + f" ({h['descripcion']})")  # senior-ignore: SEC-LOG-SENSIBLE motivo: muestra el id y el archivo, nunca el valor
    for b in r["bloqueos"]:
        print(f"  BLOQUEA {b}")
    if r["bloqueos"]:
        print("Resultado: todavía no se puede aplicar." if not aplicar else "Resultado: no se hizo nada porque hay algo que bloquea.")
    elif not aplicar:
        print("Resultado: listo. Nada se escribió; con --aplicar se hace todo.")


def ejecutar(args, raiz, r, secretos, meta):
    """Aplica el plan. Devuelve (código, líneas). Se detiene en el primer fallo y dice dónde quedó."""
    sal = []
    dueno, nombre = r["dueno"], r["nombre"]
    guardia = SKILLS / "senior-git" / "scripts" / "guardia_autoria.py"
    # 1. Git, identidad y .gitignore
    if not r["es_git"]:
        rc, o = git(raiz, "init", "-q", "-b", "main")
        if rc != 0:
            return 1, sal + [f"FALLÓ git init: {o}"]
        sal.append("LISTO git init en main")
    if not git(raiz, "config", "--local", "--get", "user.name")[1].strip() or not git(raiz, "config", "--local", "--get", "user.email")[1].strip():
        git(raiz, "config", "--local", "user.name", r["login"])
        git(raiz, "config", "--local", "user.email", r["noreply"])
        sal.append(f"LISTO identidad local de Git: {r['login']}")
    else:
        sal.append(f"LISTO identidad local de Git: {git(raiz, 'config', '--local', '--get', 'user.name')[1].strip()}")
    cambio_ignore = completar_gitignore(raiz, secretos)
    sal.append("LISTO .gitignore con los archivos de secretos" if cambio_ignore else "LISTO .gitignore ya cubría los secretos")
    # 2. escaneo con el .gitignore ya aplicado (ahora git sabe qué se ignora)
    hallazgos = secretos.versionados_que_no_deben(raiz) + secretos.escanear_todo(raiz)
    if hallazgos:
        sal.append(f"BLOQUEA aparecieron {len(hallazgos)} claves o datos personales con el .gitignore ya aplicado; no se commitea nada. Ver `secretos.py todo`.")
        return 1, sal
    # 3. README
    if r["falta_readme"]:
        escribir_readme(raiz, nombre, args.descripcion)
        sal.append("LISTO README.md creado")
    # 4. hooks de Git
    rc, o = correr([sys.executable, str(guardia), "instalar", "--raiz", str(raiz)])
    sal.append("LISTO hooks de Git (autoría y secretos)" if rc == 0 else f"AVISO no se pudieron instalar los hooks de Git: {o[:160]}")
    # 5. remoto
    remoto = r["remoto"]
    if not remoto["existe"]:
        rc, o = gh("repo", "create", f"{dueno}/{nombre}", "--public" if args.publico else "--private")
        if rc != 0:
            return 1, sal + [f"FALLÓ al crear el repositorio: {o[:300]}"]
        remoto = estado_remoto(dueno, nombre)
        if not remoto.get("existe"):
            return 1, sal + ["FALLÓ: el repositorio se creó pero gh no lo encuentra todavía; repetir en unos segundos."]
        sal.append(f"LISTO repositorio creado: {remoto['url']}")
    else:
        sal.append(f"LISTO repositorio existente: {remoto['url']}")
    if not r.get("origen"):
        rc, o = git(raiz, "remote", "add", "origin", remoto["url"])
        if rc != 0:
            return 1, sal + [f"FALLÓ al asociar origin: {o}"]
        sal.append("LISTO origin asociado")
    # 6. descripción y topics (obligatorios)
    rc, o = correr([sys.executable, str(SKILLS / "senior-git" / "scripts" / "repo_meta.py"), "--raiz", str(raiz), "--descripcion", args.descripcion,
                    "--topics", ",".join(r["topics"]), "--aplicar"])
    if rc != 0:
        return 1, sal + [f"FALTA la descripción y los topics: {o[-300:]}"]
    sal.append("LISTO descripción y topics aplicados y comprobados en GitHub")
    # 7. commits
    git(raiz, "add", "README.md", ".gitignore")
    if git(raiz, "diff", "--cached", "--quiet")[0] != 0:
        rc, o = git(raiz, "commit", "-q", "-m", "chore: inicializa el repositorio")
        if rc != 0:
            return 1, sal + [f"FALLÓ el commit inicial (lo suele frenar un hook): {o[-400:]}"]
        sal.append("LISTO commit: chore: inicializa el repositorio")
    git(raiz, "add", "-A")
    if git(raiz, "diff", "--cached", "--quiet")[0] != 0:
        rc, o = git(raiz, "commit", "-q", "-m", "chore: agrega el contenido existente")
        if rc != 0:
            return 1, sal + [f"FALLÓ el commit del contenido existente (lo suele frenar un hook): {o[-400:]}"]
        sal.append("LISTO commit: chore: agrega el contenido existente")
    if git(raiz, "rev-parse", "--verify", "HEAD")[0] != 0:
        return 1, sal + ["AVISO no hay nada para commitear."]
    # 8. push
    if args.sin_subir:
        sal.append("LISTO sin subir (--sin-subir)")
    else:
        if not remoto.get("vacio", True):
            git(raiz, "fetch", "-q", "origin")
            if git(raiz, "merge-base", "--is-ancestor", "origin/main", "HEAD")[0] != 0:
                return 1, sal + ["BLOQUEA la historia local no contiene la del remoto: no se sube ni se fuerza nada."]
        rc, o = git(raiz, "push", "-u", "origin", "HEAD")
        if rc != 0:
            return 1, sal + [f"FALLÓ el push (no se fuerza): {o[-500:]}"]
        sal.append("LISTO subido a origin")
    # 9. verificación
    actual, motivo = meta.actual_de_github(raiz, None)
    if not actual or not actual["description"] or not actual["topics"]:
        return 1, sal + ["FALTA la descripción o los topics no figuran en GitHub: revisar."]
    limpio = git(raiz, "status", "--porcelain")[1].strip() == ""
    sal.append(f"LISTO verificado: {remoto['url']} | descripción: {actual['description']} | topics: {', '.join(actual['topics'])} | árbol {'limpio' if limpio else 'con cambios'}")
    return 0, sal


def main():
    for f in (sys.stdout, sys.stderr):
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--raiz", default=".")
    visibilidad = ap.add_mutually_exclusive_group()
    visibilidad.add_argument("--publico", action="store_true")
    visibilidad.add_argument("--privado", action="store_true")
    ap.add_argument("--descripcion")
    ap.add_argument("--topics")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--sin-subir", action="store_true")
    ap.add_argument("--anidado", action="store_true", help="la carpeta está dentro de otro repositorio de Git y se quiere uno propio acá")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if not raiz.is_dir():
        sys.exit(f"{raiz} no es una carpeta.")
    secretos = cargar("senior", "secretos.py")
    meta = cargar("senior-git", "repo_meta.py")
    r = analizar(args, raiz, secretos, meta)
    mostrar(r, raiz, args.aplicar)
    if r["bloqueos"]:
        return 1
    if not args.aplicar:
        return 0
    codigo, lineas = ejecutar(args, raiz, r, secretos, meta)
    print("\n".join(lineas))
    print("Resultado: " + ("todo listo." if codigo == 0 else "quedó a medias: ver la última línea."))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
