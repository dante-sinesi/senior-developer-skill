#!/usr/bin/env python3
"""Un `gh` de mentira para probar sin red: repositorios remotos que son carpetas `--bare` locales, con su descripción y topics.

Lo usan las pruebas con la variable SENIOR_GH (una lista JSON con el intérprete y este archivo) y GH_FALSO_DIR (dónde vive su estado).
Entiende lo que usa `inicializar_repo.py` y `repo_meta.py`: `api user`, `repo view`, `repo create` y `repo edit`.
GH_FALSO_PERMISO cambia el permiso que dice tener la sesión (por defecto ADMIN)."""
import json
import os
import subprocess
import sys
from pathlib import Path

DIR = Path(os.environ["GH_FALSO_DIR"])
ESTADO = DIR / "estado.json"
LOGIN, ID = "dante-prueba", 4242


def cargar():
    return json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"repos": {}}


def guardar(e):
    ESTADO.write_text(json.dumps(e, indent=1), encoding="utf-8")


def vacio(bare):
    r = subprocess.run(["git", "-C", bare, "rev-list", "-n", "1", "--all"], capture_output=True, text=True)
    return not r.stdout.strip()


def valor(args, opcion):
    return args[args.index(opcion) + 1] if opcion in args else None


def main():
    a = sys.argv[1:]
    e = cargar()
    permiso = os.environ.get("GH_FALSO_PERMISO", "ADMIN")
    if a[:2] == ["api", "user"]:
        print(f"{LOGIN} {ID}")
        return 0
    if a[:2] == ["repo", "create"]:
        nombre = a[2]
        if nombre in e["repos"]:
            print("GraphQL: Name already exists on this account", file=sys.stderr)
            return 1
        bare = str(DIR / "remotos" / (nombre.replace("/", "__") + ".git"))
        Path(bare).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
        e["repos"][nombre] = {"privado": "--private" in a, "descripcion": "", "topics": [], "bare": bare}
        guardar(e)
        print(f"https://github.com/{nombre}")
        return 0
    if a[:2] == ["repo", "view"]:
        nombre = a[2] if len(a) > 2 and not a[2].startswith("--") else None
        if nombre is None:  # sin nombre: el repositorio al que apunta `origin` de la carpeta actual
            origen = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip().replace("\\", "/")
            nombre = next((n for n, r in e["repos"].items() if r["bare"].replace("\\", "/") == origen), None)
        if nombre not in e["repos"]:
            print(f"GraphQL: Could not resolve to a Repository with the name '{nombre}'. (repository)", file=sys.stderr)
            return 1
        r = e["repos"][nombre]
        print(json.dumps({"isEmpty": vacio(r["bare"]), "isPrivate": r["privado"], "url": r["bare"].replace("\\", "/"), "viewerPermission": permiso,
                          "nameWithOwner": nombre, "description": r["descripcion"], "repositoryTopics": [{"name": t} for t in r["topics"]]}))
        return 0
    if a[:2] == ["repo", "edit"]:
        r = e["repos"].get(a[2])
        if r is None:
            print("not found", file=sys.stderr)
            return 1
        if "--description" in a:
            r["descripcion"] = valor(a, "--description")
        for i, x in enumerate(a):
            if x == "--add-topic" and a[i + 1] not in r["topics"]:
                r["topics"].append(a[i + 1])
            if x == "--remove-topic" and a[i + 1] in r["topics"]:
                r["topics"].remove(a[i + 1])
        guardar(e)
        return 0
    print("gh falso: comando no soportado " + " ".join(a), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
