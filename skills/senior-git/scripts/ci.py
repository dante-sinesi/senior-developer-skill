#!/usr/bin/env python3
"""Integración continua (CI) en GitHub Actions: mirar los chequeos de un Pull Request antes de proponer fusionarlo, armar el flujo de un proyecto y revisar el que ya tiene.

  estado   Resume los chequeos del Pull Request (`gh pr checks`): cuántos están en verde y cuáles fallan o siguen corriendo. Código de salida 0 todo en verde
           (o el proyecto no tiene CI), 1 hay chequeos en rojo, 2 hay pendientes, 3 no se pudo saber (sin `gh`, sin respuesta o ilegible). Un PR sin chequeos en un proyecto que SÍ tiene flujos de
           Pull Request cuenta como pendiente: justo después de un push los chequeos todavía no arrancaron.
  generar  Arma `.github/workflows/ci.yml` con las pruebas del proyecto (Python con unittest o pytest, Node con `npm test`, PHP con Composer: un trabajo por
           lenguaje), con permisos de solo lectura y la rama principal detectada. Sin --aplicar solo muestra el plan. Es configuración persistente del
           repositorio: se aplica solo con el visto bueno del usuario, nunca pisa un flujo existente y, si no encuentra cómo correr pruebas, no escribe nada.
  auditar  Lee los flujos existentes y avisa: sin pruebas, `continue-on-error`, `|| true`, acciones por rama móvil (@master o @main) y sin disparo en Pull Request.
           Es una lectura de texto (sin analizador de YAML): ignora las líneas comentadas y puede equivocarse con bloques `run` largos.

Uso:
    python ci.py estado [--pr N|URL|rama] [--repo dueño/nombre] [--raiz .]
    python ci.py generar [--raiz .] [--os ubuntu-latest] [--aplicar]
    python ci.py auditar [--raiz .]
Solo biblioteca estándar. `gh` se busca en el PATH; la variable SENIOR_GH (una lista JSON) lo reemplaza para probar sin red.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PRUEBAS = re.compile(r"\b(test|tests|pytest|unittest|phpunit|jest|vitest|mocha|go test|cargo test|dotnet test|rspec|correr_todo)\b", re.I)
EN_PR = re.compile(r"^\s*pull_request(_target)?\s*:|\bpull_request\b\s*[,\]]", re.M)


def gh_cmd():
    env = os.environ.get("SENIOR_GH")
    if env:
        return list(json.loads(env))
    ruta = shutil.which("gh")
    return [ruta] if ruta else None


def flujos(raiz):
    carpeta = Path(raiz) / ".github" / "workflows"
    return sorted(p for p in carpeta.glob("*.y*ml")) if carpeta.is_dir() else []


def sin_comentarios(texto):
    return "\n".join(l for l in texto.splitlines() if not l.strip().startswith("#"))


def tiene_ci_en_pr(raiz):
    return any(EN_PR.search(sin_comentarios(p.read_text(encoding="utf-8-sig", errors="replace"))) for p in flujos(raiz))


# ---------------------------------------------------------------- estado
def resumir(chequeos):
    """(texto, código) a partir de la lista que da `gh pr checks --json name,bucket,link`."""
    buckets = {"pass": [], "fail": [], "pending": [], "otros": []}
    for c in chequeos:
        b = (c.get("bucket") or "").lower()
        buckets[b if b in ("pass", "fail", "pending") else "otros"].append(c)
    total = len(chequeos)
    verdes = len(buckets["pass"]) + len([c for c in buckets["otros"] if (c.get("bucket") or "").lower() in ("skipping",)])
    partes = [f"{verdes} de {total} en verde"]
    for c in buckets["fail"]:
        partes.append(f"FALLA {c.get('name')}" + (f" ({c.get('link')})" if c.get("link") else ""))
    for c in buckets["pending"]:
        partes.append(f"pendiente {c.get('name')}")
    for c in buckets["otros"]:
        if (c.get("bucket") or "").lower() not in ("skipping",):
            partes.append(f"{(c.get('bucket') or 'sin estado')} {c.get('name')}")
    if buckets["fail"]:
        return "; ".join(partes), 1
    if buckets["pending"] or (total - verdes):
        return "; ".join(partes), 2
    return "; ".join(partes), 0


def cmd_estado(a):
    gh = gh_cmd()
    if not gh:
        print("No se pudo mirar los chequeos: `gh` no está instalado. Se le dice al usuario y decide él.")
        return 3
    cmd = gh + ["pr", "checks"] + ([str(a.pr)] if a.pr else []) + (["--repo", a.repo] if a.repo else []) + ["--json", "name,state,bucket,link"]
    try:
        r = subprocess.run(cmd, cwd=a.raiz, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"No se pudo mirar los chequeos: {e!r}")
        return 3
    salida = (r.stdout or "").strip()
    if salida.startswith("["):
        try:
            texto, codigo = resumir(json.loads(salida))
        except ValueError:
            print("No se pudo leer la respuesta de `gh pr checks`.")
            return 3
        print(("Chequeos del Pull Request: " if codigo == 0 else "Chequeos del Pull Request, NO fusionar sin hablar con el usuario: ") + texto)
        return codigo
    texto_err = ((r.stderr or "") + salida).lower()
    if "no checks reported" in texto_err:
        if tiene_ci_en_pr(a.raiz):
            print("El Pull Request todavía no tiene chequeos, pero el proyecto tiene flujos de CI para Pull Request: están por arrancar. "
                  "No fusionar todavía: esperar y volver a mirar.")
            return 2
        print("El proyecto no tiene chequeos de CI para Pull Request (no hay flujos en .github/workflows): no hay nada que esperar. "
              "Conviene `ci.py generar` para tener una.")
        return 0
    print("No se pudo mirar los chequeos: " + (texto_err.strip()[:200] or "sin respuesta de gh") + ". Se le dice al usuario y decide él.")
    return 3


# ---------------------------------------------------------------- generar
def detectar(raiz):
    """[(lenguaje, plan)] con cómo instalar y correr las pruebas de cada lenguaje que se reconozca."""
    raiz = Path(raiz)
    res = []
    py_tests = any(raiz.glob("tests/*.py")) or any(raiz.glob("test/*.py")) or any(raiz.glob("test_*.py"))
    textos_py = " ".join((raiz / n).read_text(encoding="utf-8-sig", errors="replace") for n in ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "tox.ini", "pytest.ini", "setup.cfg") if (raiz / n).exists())
    if py_tests or "pytest" in textos_py.lower():
        pytest = "pytest" in textos_py.lower() or (raiz / "pytest.ini").exists()
        instalar = "pip install -r requirements.txt" if (raiz / "requirements.txt").exists() else ("pip install ." if (raiz / "pyproject.toml").exists() else None)
        res.append(("python", {"instalar": instalar, "probar": "python -m pytest" if pytest else "python -m unittest discover -s tests -t ."}))
    pkg = raiz / "package.json"
    if pkg.exists():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8-sig")).get("scripts", {})
        except ValueError:
            scripts = {}
        prueba = scripts.get("test", "")
        if prueba and "no test specified" not in prueba:
            res.append(("node", {"instalar": "npm ci" if (raiz / "package-lock.json").exists() else "npm install", "probar": "npm test"}))
    comp = raiz / "composer.json"
    if comp.exists():
        try:
            d = json.loads(comp.read_text(encoding="utf-8-sig"))
        except ValueError:
            d = {}
        if "test" in (d.get("scripts") or {}):
            res.append(("php", {"instalar": "composer install --no-interaction", "probar": "composer test"}))
        elif "phpunit/phpunit" in (d.get("require-dev") or {}):
            res.append(("php", {"instalar": "composer install --no-interaction", "probar": "vendor/bin/phpunit"}))
    return res


def rama_principal(raiz):
    r = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=raiz, capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split("/", 1)[-1]
    actual = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=raiz, capture_output=True, text=True).stdout.strip()  # sirve aunque no haya commits
    if actual in ("main", "master"):
        return actual
    ramas = [x.strip(" *") for x in subprocess.run(["git", "branch", "--list", "main", "master"], cwd=raiz, capture_output=True, text=True).stdout.splitlines()]
    return "master" if "master" in ramas and "main" not in ramas else "main"


PASOS = {
    "python": ['      - uses: actions/setup-python@v5', '        with:', '          python-version: "3.12"'],
    "node": ['      - uses: actions/setup-node@v4', '        with:', '          node-version: "20"'],
    "php": ['      - uses: shivammathur/setup-php@v2', '        with:', '          php-version: "8.3"'],
}


def construir(plan, rama, so):
    lineas = ["name: Pruebas", "", "on:", "  push:", f"    branches: [{rama}]", "  pull_request:", "", "permissions:", "  contents: read", "", "jobs:"]
    for lenguaje, p in plan:
        lineas += [f"  {lenguaje}:", f"    runs-on: {so}", "    steps:", "      - uses: actions/checkout@v4"] + PASOS[lenguaje]
        if p["instalar"]:
            lineas += [f"      - run: {p['instalar']}"]
        lineas += [f"      - run: {p['probar']}"]
    return "\n".join(lineas) + "\n"


def cmd_generar(a):
    raiz = Path(a.raiz)
    existentes = flujos(raiz)
    if (raiz / ".github" / "workflows" / "ci.yml").exists() or any(PRUEBAS.search(sin_comentarios(p.read_text(encoding="utf-8-sig", errors="replace"))) for p in existentes):
        print("El proyecto ya tiene un flujo de CI con pruebas: no se pisa. Usar `ci.py auditar` para revisarlo.")
        return 1
    plan = detectar(raiz)
    if not plan:
        print("No se encontró cómo correr las pruebas (Python con tests/, Node con un script `test`, PHP con Composer): no se escribe ningún flujo. "
              "Un CI que no corre nada da una falsa seguridad.")
        return 1
    texto = construir(plan, rama_principal(raiz), a.os)
    destino = raiz / ".github" / "workflows" / "ci.yml"
    print("Plan (nada escrito todavía):" if not a.aplicar else "Se escribe:", destino.relative_to(raiz).as_posix())
    print("  trabajos: " + ", ".join(f"{l} → {p['probar']}" for l, p in plan))
    print("  se dispara en cada Pull Request y en cada push a la rama principal; permisos: solo lectura")
    if not a.aplicar:
        print("Con el visto bueno del usuario: `ci.py generar --aplicar`.")
        print(texto)
        return 0
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8", newline="\n")
    print("Listo. Queda sin commitear: el commit y el push los aprueba el usuario.")
    return 0


# ---------------------------------------------------------------- auditar
def cmd_auditar(a):
    archivos = flujos(a.raiz)
    if not archivos:
        print("El proyecto no tiene flujos de CI (.github/workflows). `ci.py generar` arma uno.")
        return 0
    hallazgos = []
    for p in archivos:
        texto = sin_comentarios(p.read_text(encoding="utf-8-sig", errors="replace"))
        if not PRUEBAS.search(texto):
            hallazgos.append(f"{p.name}: no corre pruebas (no se ve ningún comando de tests)")
        if not EN_PR.search(texto):
            hallazgos.append(f"{p.name}: no se dispara en Pull Request: un cambio llega a fusionarse sin chequeos")
        if re.search(r"continue-on-error\s*:\s*true", texto):
            hallazgos.append(f"{p.name}: tiene `continue-on-error: true`: un paso rojo no frena nada")
        if re.search(r"\|\|\s*true\b", texto):
            hallazgos.append(f"{p.name}: tiene `|| true`: un comando que falla se da por bueno")
        for m in re.finditer(r"uses:\s*([\w./-]+)@(master|main)\b", texto):
            hallazgos.append(f"{p.name}: la acción {m.group(1)} está por rama móvil (@{m.group(2)}): fijar una versión")
    if not hallazgos:
        print(f"CI: {len(archivos)} flujo(s) revisados, sin avisos (lectura de texto: no reemplaza mirar el flujo).")
        return 0
    print("CI: " + str(len(hallazgos)) + " aviso(s):")
    for h in hallazgos:
        print("  " + h)
    return 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    for nombre in ("estado", "generar", "auditar"):
        s = sub.add_parser(nombre)
        s.add_argument("--raiz", default=".")
        if nombre == "estado":
            s.add_argument("--pr")
            s.add_argument("--repo")
        if nombre == "generar":
            s.add_argument("--os", default="ubuntu-latest")
            s.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    sys.exit({"estado": cmd_estado, "generar": cmd_generar, "auditar": cmd_auditar}[a.orden](a))


if __name__ == "__main__":
    main()
