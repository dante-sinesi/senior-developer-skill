#!/usr/bin/env python3
"""Orden de las fuentes de la documentación: mandan los requisitos y las decisiones; el código es evidencia, no fuente.

Cada caso de uso (`docs/casos-de-uso/`) y cada diagrama de secuencia (`docs/secuencias/`, o un `sequenceDiagram` en
`docs/diagramas/`) tiene que citar un requisito o una decisión que exista (en `docs/requisitos/`, `docs/decisiones/` o un
documento de decisiones) o decir que fue inferido del código. Un requisito provisorio sacado del código no respalda.
Los que ya estaban solo se avisan; fallan los que agrega la rama. Lo corre `verificar.py fuentes`. Solo lectura y solo
biblioteca estándar.
"""
import re
import subprocess
from pathlib import Path

ID = r"(?:RNF|RN|RU|RD|RF|RT|RI|ADR|D)-\d{1,4}"
CITA = re.compile(rf"\b{ID}\b")
DEFINE = re.compile(rf"(?m)^(?:id:\s*|#{{1,6}}\s+.*?|\|\s*\**\[*|\s*[-*]\s+\**\[*)({ID})\b")
INFERIDO = re.compile(r"(?i)inferid[oa]s?\s+(?:del|desde\s+el|leyendo\s+el)\s+c[oó]digo")
MARCA = "inferido del código, por confirmar"


def leer(f):
    return f.read_text(encoding="utf-8-sig", errors="replace")


def definidos(docs):
    """Los identificadores de requisitos y decisiones que respaldan: por nombre de archivo, encabezado, tabla o lista."""
    archivos = [f for carpeta in ("requisitos", "decisiones") for f in (docs / carpeta).rglob("*.md")]
    archivos += [f for f in docs.rglob("*.md") if "decisiones" in f.stem.lower()]
    hallados = set()
    for f in archivos:
        texto = leer(f)
        if INFERIDO.search(texto) and re.search(r"(?i)\bprovisori[oa]\b", texto):
            continue
        nombre = re.match(ID, f.stem)
        hallados.update(DEFINE.findall(texto))
        if nombre:
            hallados.add(nombre.group(0))
    return hallados


def documentos(docs):
    """Los casos de uso y las secuencias del proyecto, sin los índices."""
    res = [f for carpeta in ("casos-de-uso", "secuencias") for f in (docs / carpeta).rglob("*.md")]
    res += [f for f in (docs / "diagramas").rglob("*.md") if "sequenceDiagram" in leer(f)]
    return sorted(f for f in res if f.name.lower() not in ("readme.md", "index.md"))


def git(raiz, *args):
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def agregados(raiz, base="HEAD"):
    """Rutas que la rama agrega: respecto de la rama principal (o de `base`, si se indica otra) más lo que no está en git."""
    if base == "HEAD":
        for principal in ("origin/main", "origin/master", "main", "master"):
            comun = git(raiz, "merge-base", principal, "HEAD")
            if comun:
                base = comun
                break
    nuevos = git(raiz, "diff", "--name-only", "--diff-filter=A", base).splitlines()
    nuevos += git(raiz, "ls-files", "--others", "--exclude-standard").splitlines()
    return set(nuevos)


def evaluar(raiz, base="HEAD"):
    """(líneas, ok). Sin casos de uso ni secuencias no dice nada."""
    raiz = Path(raiz)
    lista = documentos(raiz / "docs")
    if not lista:
        return [], True
    existen = definidos(raiz / "docs")
    sin = [f.relative_to(raiz).as_posix() for f in lista
           if not INFERIDO.search(leer(f)) and not existen & set(CITA.findall(leer(f)))]
    if not sin:
        return [f"Fuentes: {len(lista)} casos de uso y secuencias citan un requisito o una decisión, o avisan que salen del código."], True
    nuevos = agregados(raiz, base)
    fallan, avisan = [r for r in sin if r in nuevos], [r for r in sin if r not in nuevos]
    pide = f"citar un requisito o una decisión que exista, o marcarlo «{MARCA}»"
    lineas = []
    if fallan:
        lineas.append(f"Fuentes: {len(fallan)} documentos nuevos sin respaldo ({pide}):")
        lineas += [f"  {r}" for r in fallan[:8]]
    if avisan:
        lineas.append(f"Fuentes: AVISO, {len(avisan)} ya existentes sin respaldo (no bloquea; {pide}): " + ", ".join(avisan[:4]) + (" …" if len(avisan) > 4 else ""))
    return lineas, not fallan
