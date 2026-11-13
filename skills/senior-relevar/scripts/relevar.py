#!/usr/bin/env python3
"""Inventario automático de un proyecto (primer paso del relevamiento).

Uso:
    python relevar.py [--raiz .] [--salida docs/relevamiento.md]

Genera un informe en Markdown con HECHOS (no interpretaciones):
  - lenguajes por cantidad de archivos y líneas
  - manifiestos y herramientas detectadas (package.json, composer.json, etc.)
  - tests presentes y herramientas de test probables
  - integración continua, documentación existente, historial git
  - archivos más grandes y más modificados (zonas de riesgo)
  - marcas TODO/FIXME
Sin --salida imprime por pantalla. La interpretación (arquitectura, reglas de
negocio, riesgos) la hace luego quien releva, apoyándose en este informe.

Solo biblioteca estándar.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".idea",
           ".vscode", "coverage", ".next"}
LENGUAJES = {".php": "PHP", ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
             ".jsx": "JavaScript", ".py": "Python", ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".go": "Go",
             ".rs": "Rust", ".rb": "Ruby", ".c": "C", ".h": "C/C++", ".cpp": "C++", ".cc": "C++", ".hpp": "C++",
             ".swift": "Swift", ".lua": "Lua", ".sql": "SQL", ".html": "HTML", ".htm": "HTML", ".css": "CSS",
             ".scss": "CSS", ".vue": "Vue", ".sh": "Shell", ".ps1": "PowerShell", ".asm": "Ensamblador", ".s": "Ensamblador"}
MANIFIESTOS = {
    "package.json": "Node.js (npm)", "composer.json": "PHP (Composer)", "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (pyproject)", "Cargo.toml": "Rust (Cargo)", "go.mod": "Go (módulos)",
    "pom.xml": "Java (Maven)", "build.gradle": "Java/Kotlin (Gradle)", "Gemfile": "Ruby (Bundler)",
    "Makefile": "Make", "CMakeLists.txt": "CMake", "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
}
INDICIOS_TEST = ("test", "tests", "spec", "__tests__", "phpunit.xml", "jest.config", "vitest.config",
                 "playwright.config", "pytest.ini")
DOCS = ("README", "CHANGELOG", "CONTRIBUTING", "LICENSE", "docs", "arquitectura", "architecture")
MARCAS = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")


def git(raiz, *args):
    try:
        p = subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def recorrer(raiz):
    for actual, carpetas, nombres in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR]
        for nombre in nombres:
            yield Path(actual) / nombre


def construir(raiz):
    por_lenguaje_archivos, por_lenguaje_lineas = Counter(), Counter()
    grandes, manifiestos, tests, docs_presentes, marcas = [], [], [], set(), 0
    for ruta in recorrer(raiz):
        rel = ruta.relative_to(raiz).as_posix()
        if ruta.name in MANIFIESTOS:
            manifiestos.append(f"{rel} → {MANIFIESTOS[ruta.name]}")
        bajo = rel.lower()
        if any(ind in bajo.split("/") or ruta.name.lower().startswith(ind) for ind in INDICIOS_TEST) \
                or re.search(r"(test|spec)\.[a-z]+$", bajo):
            tests.append(rel)
        for d in DOCS:
            if ruta.name.upper().startswith(d.upper()) or rel.lower().startswith(d.lower() + "/"):
                docs_presentes.add(d)
        lenguaje = LENGUAJES.get(ruta.suffix.lower())
        if not lenguaje:
            continue
        try:
            texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        n = len(texto.splitlines())
        por_lenguaje_archivos[lenguaje] += 1
        por_lenguaje_lineas[lenguaje] += n
        grandes.append((n, rel))
        marcas += len(MARCAS.findall(texto))
    return por_lenguaje_archivos, por_lenguaje_lineas, sorted(grandes, reverse=True)[:8], manifiestos, tests, docs_presentes, marcas


def informe(raiz):
    archivos, lineas, grandes, manifiestos, tests, docs, marcas = construir(raiz)
    out = [f"# Relevamiento automático de {raiz.name}", "",
           "Informe generado por `relevar.py`: solo hechos, sin interpretación.", "",
           "## Lenguajes", ""]
    if archivos:
        out += ["| Lenguaje | Archivos | Líneas |", "|---|---|---|"]
        out += [f"| {l} | {archivos[l]} | {lineas[l]} |" for l, _ in archivos.most_common()]
    else:
        out.append("No se detectó código fuente.")
    out += ["", "## Herramientas y manifiestos", ""]
    out += [f"- {m}" for m in manifiestos] or ["- Ninguno detectado."]
    out += ["", "## Tests", ""]
    if tests:
        out.append(f"- {len(tests)} archivos o carpetas con indicios de tests (ej.: {', '.join(tests[:4])}).")
    else:
        out.append("- **No se detectaron tests.** Primer paso: crear la infraestructura y tests de caracterización.")
    ci = [p for p in (".github/workflows", ".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile") if (raiz / p).exists()]
    out += ["", "## Integración continua y documentación", "",
            "- Integración continua: " + (", ".join(ci) if ci else "no detectada."),
            "- Documentación presente: " + (", ".join(sorted(docs)) if docs else "ninguna detectada.")]
    out += ["", "## Historial git", ""]
    if git(raiz, "rev-parse", "--is-inside-work-tree") == "true":
        total = git(raiz, "rev-list", "--count", "HEAD")
        ultimo = git(raiz, "log", "-1", "--format=%cs %s")
        calientes = git(raiz, "log", "--name-only", "--format=", "-n", "200")
        top = Counter(l for l in calientes.splitlines() if l).most_common(5)
        out += [f"- Commits: {total or 'desconocido'}; último: {ultimo or 'n/d'}.",
                "- Archivos más modificados (últimos 200 commits): " +
                (", ".join(f"{a} ({n})" for a, n in top) if top else "sin datos.")]
    else:
        out.append("- No es un repositorio git (o no hay historial disponible).")
    out += ["", "## Zonas de riesgo (por tamaño)", ""]
    out += [f"- {rel}: {n} líneas" for n, rel in grandes] or ["- Sin datos."]
    out += ["", f"## Marcas pendientes", "", f"- {marcas} marcas TODO/FIXME/HACK en el código."]
    return "\n".join(out) + "\n"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    texto = informe(raiz)
    if args.salida:
        destino = raiz / args.salida
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8", newline="\n")
        print(f"Informe escrito en {args.salida}")
    else:
        print(texto)


if __name__ == "__main__":
    main()
