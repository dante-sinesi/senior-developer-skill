#!/usr/bin/env python3
"""Descripción y Topics del repositorio de GitHub: se completan al empezar y se mantienen al día.

Es la "portada" del repositorio: lo primero que se lee en GitHub y lo que usan las búsquedas. Este script mira el
proyecto (lenguajes, bibliotecas, README), lo compara con lo que dice GitHub y, si se lo pide `--aplicar`, lo
actualiza con `gh repo edit`. Solo toca la descripción y los Topics: nunca la visibilidad, la página web ni otros
ajustes.

Uso:
    python repo_meta.py [--raiz .]
        Informe: lo que detecta, lo que dice GitHub hoy, la propuesta y si está al día. No escribe nada.
    python repo_meta.py --descripcion "..." --topics a,b,c
        Muestra qué cambiaría con esos valores (el texto y los temas de dominio los decide quien llama, a partir
        del README; el script agrega los que detecta solo).
    python repo_meta.py --descripcion "..." --topics a,b,c --aplicar
        Aplica el cambio y lo comprueba leyendo GitHub de nuevo.
Opciones: --reemplazar-descripcion (pisa una descripción que no puso senior), --simular archivo.json (no usa la red
ni escribe nada: el JSON trae el estado de GitHub {repo, description, topics, permiso, privado}).

Reglas:
  - Descripción de una línea, hasta 350 caracteres, sin correos ni claves. Topics: minúsculas, números y guiones,
    hasta 50 caracteres cada uno y hasta 20 en total.
  - Una descripción que ya existe y no escribió senior no se pisa sin `--reemplazar-descripcion`.
  - Solo se quitan los Topics que senior agregó antes (los registra en `.git/senior-repo-meta.json`, que no se
    sube); los que puso el usuario se conservan.
  - Hace falta permiso de administrador o de mantenimiento sobre el repositorio y la sesión de `gh` iniciada.
Código de salida 0 salvo error.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IGNORAR = {".git", ".temporal", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv",
           "documentos-externos", ".claude"}
LENGUAJES = {".py": "python", ".js": "javascript", ".mjs": "javascript", ".ts": "typescript", ".tsx": "typescript",
             ".jsx": "javascript", ".php": "php", ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".go": "go",
             ".rs": "rust", ".rb": "ruby", ".sql": "sql", ".sh": "shell", ".swift": "swift", ".c": "c",
             ".cpp": "cpp", ".lua": "lua", ".vue": "vue", ".svelte": "svelte", ".html": "html", ".css": "css"}
PAQUETES_JS = {"react": "react", "vue": "vue", "svelte": "svelte", "next": "nextjs", "express": "express",
               "tailwindcss": "tailwindcss", "vite": "vite", "@angular/core": "angular", "typescript": "typescript"}
PAQUETES_PY = {"django": "django", "flask": "flask", "fastapi": "fastapi", "pytest": "pytest"}
MAX_DESC, MAX_TOPICS = 350, 20
RE_TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
RE_PELIGROSO = re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{12,}|(?i:password|contraseña|secret|token)\s*[:=]"
                          r"|[\w.+-]+@[\w-]+\.[\w.]+")


def tecnologias(raiz):
    """Topics que se deducen del código: lenguajes con peso real, bibliotecas, Docker, CI y skills de Claude Code."""
    cuenta, topics = {}, []
    for base, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR]
        for a in archivos:
            t = LENGUAJES.get(Path(a).suffix.lower())
            if t:
                cuenta[t] = cuenta.get(t, 0) + 1
    total = sum(cuenta.values())
    for t, n in sorted(cuenta.items(), key=lambda x: -x[1]):
        if n >= 2 and n / total >= 0.1:
            topics.append(t)
    pj = raiz / "package.json"
    if pj.exists():
        try:
            d = json.loads(pj.read_text(encoding="utf-8-sig"))
            deps = {**d.get("dependencies", {}), **d.get("devDependencies", {})}
            topics += [PAQUETES_JS[k] for k in deps if k in PAQUETES_JS]
        except ValueError:
            pass
    cj = raiz / "composer.json"
    if cj.exists():
        texto = cj.read_text(encoding="utf-8-sig", errors="replace").lower()
        topics += [t for k, t in (("laravel/framework", "laravel"), ("symfony/", "symfony")) if k in texto]
    for nombre in ("requirements.txt", "pyproject.toml"):
        f = raiz / nombre
        if f.exists():
            texto = f.read_text(encoding="utf-8-sig", errors="replace").lower()
            topics += [t for k, t in PAQUETES_PY.items() if re.search(r"(?m)^\W*" + k + r"\b", texto)]
    if (raiz / "Dockerfile").exists() or (raiz / "docker-compose.yml").exists():
        topics.append("docker")
    if (raiz / ".github" / "workflows").is_dir():
        topics.append("github-actions")
    if (raiz / ".claude-plugin").is_dir() or list((raiz / "skills").glob("*/SKILL.md")) or list(raiz.glob("*/SKILL.md")):
        topics += ["claude-code", "agent-skills"]
    return list(dict.fromkeys(topics))


def presentacion(raiz):
    """(título, primer párrafo) del README, sin formato."""
    f = raiz / "README.md"
    if not f.exists():
        return "", ""
    titulo, parrafo = "", []
    for linea in f.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = linea.strip()
        if not titulo and s.startswith("# "):
            titulo = s[2:].strip()
            continue
        if not titulo or s.startswith(("#", "!", "[!", "<", "|", ">", "```", "---")) or re.match(r"^[-*+] |^\d+\. ", s):
            if parrafo:
                break
            continue
        if not s:
            if parrafo:
                break
            continue
        parrafo.append(s)
    if not titulo:  # un README sin título (empieza con una imagen) igual tiene presentación: el primer párrafo de texto
        for linea in f.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            s = linea.strip()
            if not s or s.startswith(("#", "!", "[!", "<", "|", ">", "```", "---")) or re.match(r"^[-*+] |^\d+\. ", s):
                if parrafo:
                    break
                continue
            parrafo.append(s)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", " ".join(parrafo))
    texto = re.sub(r"[*_`]", "", texto)
    return titulo, texto


def borrador_descripcion(texto):
    """Primera oración del README, hasta unos 180 caracteres: solo un punto de partida."""
    if not texto:
        return ""
    primera = re.split(r"(?<=[.!?])\s", texto, maxsplit=1)[0]
    if len(primera) > 180:
        primera = primera[:180].rsplit(" ", 1)[0].rstrip(",;: ") + "…"
    return primera


def huella(tecs, titulo, intro):
    return hashlib.sha1(json.dumps([sorted(tecs), titulo, intro], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def gh_cmd():
    """El comando de `gh` como lista, o None si no está instalado. La variable SENIOR_GH (una lista JSON) lo reemplaza: sirve para probar sin red."""
    env = os.environ.get("SENIOR_GH")
    if env:
        return list(json.loads(env))
    ruta = shutil.which("gh")
    return [ruta] if ruta else None


def correr(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def actual_de_github(raiz, simular):
    """Estado del repositorio en GitHub, o (None, motivo)."""
    if simular:
        d = json.loads(Path(simular).read_text(encoding="utf-8-sig"))
        return {"repo": d.get("repo", "simulado/repo"), "description": d.get("description") or "",
                "topics": list(d.get("topics") or []), "permiso": d.get("permiso", "ADMIN"),
                "privado": bool(d.get("privado", False))}, ""
    gh = gh_cmd()
    if not gh:
        return None, "no está instalado `gh`"
    rc, salida = correr([*gh, "repo", "view", "--json", "nameWithOwner,description,repositoryTopics,viewerPermission,isPrivate"], cwd=raiz)
    if rc != 0:
        return None, "este proyecto todavía no tiene un repositorio en GitHub, o `gh` no tiene la sesión iniciada"
    try:
        d = json.loads(salida)
    except ValueError:
        return None, "`gh` devolvió una respuesta que no se pudo leer"
    temas = [t.get("name") or (t.get("topic") or {}).get("name") for t in (d.get("repositoryTopics") or [])]
    return {"repo": d["nameWithOwner"], "description": d.get("description") or "", "topics": [t for t in temas if t],
            "permiso": d.get("viewerPermission", ""), "privado": bool(d.get("isPrivate"))}, ""


def ruta_registro(raiz):
    rc, salida = correr(["git", "rev-parse", "--git-dir"], cwd=raiz)
    if rc != 0:
        return None
    g = Path(salida.strip().splitlines()[0])
    return (g if g.is_absolute() else raiz / g) / "senior-repo-meta.json"


def leer_registro(raiz):
    r = ruta_registro(raiz)
    if r and r.exists():
        try:
            return json.loads(r.read_text(encoding="utf-8"))
        except ValueError:
            return None
    return None


def validar(descripcion, topics):
    errores = []
    if descripcion is not None:
        if not descripcion.strip():
            errores.append("la descripción está vacía")
        if "\n" in descripcion or "\r" in descripcion:
            errores.append("la descripción debe ser de una sola línea")
        if len(descripcion) > MAX_DESC:
            errores.append(f"la descripción tiene {len(descripcion)} caracteres (máximo {MAX_DESC})")
        if RE_PELIGROSO.search(descripcion):
            errores.append("la descripción parece tener un correo, una clave o un token: no va en un texto público")
    for t in topics or []:
        if not RE_TOPIC.match(t):
            errores.append(f"el topic «{t}» no es válido (minúsculas, números y guiones; hasta 50 caracteres)")
    return errores


def calcular(actual, previo, descripcion, topics, reemplazar):
    """(cambios, notas): qué se escribiría y qué se deja de lado a propósito."""
    cambios, notas = {}, []
    if descripcion is not None and descripcion != actual["description"]:
        propia = not actual["description"] or bool(previo and previo.get("descripcion") == actual["description"])
        if propia or reemplazar:
            cambios["descripcion"] = descripcion
        else:
            notas.append("La descripción actual no la puso senior, así que no se pisa (con --reemplazar-descripcion sí).")
    if topics is not None:
        agregar = [t for t in topics if t not in actual["topics"]]
        quitar = [t for t in (previo or {}).get("topics", []) if t in actual["topics"] and t not in topics]
        if agregar:
            cambios["agregar"] = agregar
        if quitar:
            cambios["quitar"] = quitar
        total = len(actual["topics"]) + len(agregar) - len(quitar)
        if total > MAX_TOPICS:
            notas.append(f"Quedarían {total} topics y GitHub admite {MAX_TOPICS}: sacar algunos de la lista.")
            cambios.pop("agregar", None)
    return cambios, notas


def comando(repo, cambios):
    c = ["gh", "repo", "edit", repo]
    if "descripcion" in cambios:
        c += ["--description", cambios["descripcion"]]
    for t in cambios.get("agregar", []):
        c += ["--add-topic", t]
    for t in cambios.get("quitar", []):
        c += ["--remove-topic", t]
    return c


def main():
    for f in (sys.stdout, sys.stderr):
        if hasattr(f, "reconfigure"):
            f.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--descripcion")
    ap.add_argument("--topics", help="lista separada por comas")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--reemplazar-descripcion", action="store_true")
    ap.add_argument("--simular")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()

    tecs = tecnologias(raiz)
    titulo, intro = presentacion(raiz)
    actual, motivo = actual_de_github(raiz, a.simular)
    print(f"Detectado en el proyecto: {', '.join(tecs) or 'sin tecnologías reconocibles'}.")
    if actual is None:
        print(f"Repositorio de GitHub: no disponible ({motivo}). Cuando exista, volver a correr este script.")
        return 0
    previo = leer_registro(raiz)
    print(f"Repositorio: {actual['repo']} ({'privado' if actual['privado'] else 'público'}), permiso: {actual['permiso'] or 'desconocido'}.")
    print(f"Descripción actual: {actual['description'] or '(vacía)'}")
    print(f"Topics actuales: {', '.join(actual['topics']) or '(ninguno)'}")

    pedido = a.descripcion is not None or a.topics is not None
    if not pedido:
        borrador = borrador_descripcion(intro)
        print(f"Borrador de descripción (del README): {borrador or '(el README no tiene un párrafo de presentación)'}")
        print(f"Topics que se deducen solos: {', '.join(tecs) or '(ninguno)'}. Faltan los de dominio, que se eligen leyendo el README.")
        if previo and previo.get("huella") != huella(tecs, titulo, intro):
            print("Estado: el proyecto cambió desde la última vez (tecnologías o presentación): revisar la descripción y los topics.")
        elif previo:
            print("Estado: sin cambios en el proyecto desde la última vez que senior lo actualizó.")
        else:
            print("Estado: senior todavía no actualizó este repositorio." if not actual["description"] and not actual["topics"]
                  else "Estado: hay datos puestos por el usuario; senior solo agrega lo que falta y no pisa la descripción.")
        print("Siguiente paso: decidir la descripción y los topics de dominio y volver a correr con --descripcion y --topics.")
        return 0

    topics = None
    if a.topics is not None:
        topics = list(dict.fromkeys([t.strip().lower() for t in a.topics.split(",") if t.strip()] + tecs))
    errores = validar(a.descripcion, topics)
    if errores:
        for e in errores:
            print(f"NO VÁLIDO: {e}.")
        return 1
    cambios, notas = calcular(actual, previo, a.descripcion, topics, a.reemplazar_descripcion)
    for n in notas:
        print(n)
    if not cambios:
        print("Sin cambios: la descripción y los topics ya están al día.")
        return 0
    print("Cambios:")
    if "descripcion" in cambios:
        print(f"  descripción → {cambios['descripcion']}")
    if cambios.get("agregar"):
        print(f"  topics a agregar → {', '.join(cambios['agregar'])}")
    if cambios.get("quitar"):
        print(f"  topics a quitar (los había puesto senior) → {', '.join(cambios['quitar'])}")
    if not a.aplicar:
        print("No se escribió nada. Con --aplicar se aplica.")
        return 0
    if actual["permiso"] not in ("ADMIN", "MAINTAIN"):
        print(f"NO se aplicó: hace falta permiso de administrador o de mantenimiento y la sesión tiene «{actual['permiso']}».")
        return 1
    cmd = comando(actual["repo"], cambios)
    if a.simular:
        print("Simulación, comando que se ejecutaría: " + " ".join(f'"{x}"' if " " in x else x for x in cmd))
        return 0
    cmd = [*(gh_cmd() or ["gh"]), *cmd[1:]]
    rc, salida = correr(cmd, cwd=raiz)
    if rc != 0:
        print("NO se aplicó: " + salida.strip()[:300])
        return 1
    nuevo, _ = actual_de_github(raiz, None)
    ok = nuevo is not None and all(t in nuevo["topics"] for t in cambios.get("agregar", [])) and \
        ("descripcion" not in cambios or nuevo["description"] == cambios["descripcion"])
    print("Aplicado y comprobado en GitHub." if ok else "Se envió el cambio pero GitHub todavía no lo refleja: revisar.")
    reg = ruta_registro(raiz)
    if reg and ok:
        reg.write_text(json.dumps({"descripcion": (nuevo or actual)["description"], "topics": topics if topics is not None else (previo or {}).get("topics", []),
                                   "huella": huella(tecs, titulo, intro)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
