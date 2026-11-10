#!/usr/bin/env python3
"""Revisa la calidad de los comentarios del código (política "solo el porqué").

Uso:
    python comentarios.py [--raiz .] [--base HEAD] [--todo] [--max 20]

Por defecto revisa SOLO las líneas agregadas o modificadas respecto de --base
(el código que no se está tocando no se juzga). Con --todo revisa el proyecto
entero, útil para armar una propuesta de limpieza como cambio aparte.

Qué marca:
  COM-CODIGO     código comentado (para eso está git)
  COM-BANNER     banners decorativos (=====, -----)
  COM-HISTORIAL  comentarios de historial o autoría ("agregado hoy", fechas, @author)
  COM-TODO       TODO/FIXME sin motivo
  COM-REPITE     comentario que repite la línea de código que acompaña
  COM-PROPORCION demasiados comentarios en proporción al código

Permitido sin marca: el porqué de una decisión, advertencias, IDs de requisito
(RN-001), directivas de herramientas (eslint, noqa, @ts-...) y cabeceras de licencia.
Para descartar un falso positivo: `senior-ignore` en el propio comentario.

Son heurísticas: cada marca es algo para REVISAR. Código de salida: 0 sin
marcas, 1 con marcas. Solo biblioteca estándar.
"""
import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

PREF = {
    ".py": ["#"], ".sh": ["#"], ".rb": ["#"], ".ps1": ["#"], ".yml": ["#"], ".yaml": ["#"],
    ".js": ["//"], ".mjs": ["//"], ".cjs": ["//"], ".ts": ["//"], ".tsx": ["//"], ".jsx": ["//"],
    ".java": ["//"], ".kt": ["//"], ".cs": ["//"], ".go": ["//"], ".rs": ["//"], ".c": ["//"], ".cc": ["//"],
    ".cpp": ["//"], ".h": ["//"], ".hpp": ["//"], ".swift": ["//"], ".vue": ["//"], ".scss": ["//"],
    ".php": ["//", "#"], ".sql": ["--"], ".lua": ["--"], ".css": [], ".html": [], ".htm": [],
}
BLOQUES = {
    ".css": ("/*", "*/"), ".scss": ("/*", "*/"), ".html": ("<!--", "-->"), ".htm": ("<!--", "-->"),
    ".py": None, ".sh": None, ".rb": None, ".ps1": None, ".yml": None, ".yaml": None,
    ".sql": ("/*", "*/"), ".lua": None,
}
BLOQUE_C = ("/*", "*/")  # por defecto para lenguajes de la familia C
IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".idea",
           ".vscode", "coverage", ".next", "docs"}
EXENTO = re.compile(r"(?i)(^#!|coding[:=]|eslint|prettier|noqa|pylint|@ts-|istanbul|phpcs|phpstan|psalm|"
                    r"type:\s*ignore|senior-ignore|license|licencia|copyright|spdx|@var\b|@param|@return|@throws)")
PORQUE = re.compile(r"(?i)\b(porque|ya que|para evitar|debido|because|why|nota|ojo|cuidado|atenci[oó]n|warning|"
                    r"importante|workaround|requisito|regla|ver )\b|\b(RN|RF|RNF|RU|RD|RT|RI|ADR)-\d+")
BANNER = re.compile(r"([=\-*#_~+/])\1{4,}")
HISTORIAL = re.compile(r"(?i)^\s*(added|fixed|changed|modified|updated|removed|agregad|a[ñn]adid|corregid|modificad|"
                       r"actualizad|eliminad|arreglad|cambi[eé]\b|agregu[eé]\b|arregl[eé]\b|creado por|created by|"
                       r"autor:|author:|\d{4}-\d{2}-\d{2}\b|\d{1,2}/\d{1,2}/\d{2,4}\b)|@author")
TODO = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b(.*)")
CODIGO_FUERTE = re.compile(
    r"(;\s*$|\{\s*$|^\s*\}|^\s*(if|else|elseif|for|foreach|while|switch|return|function|def|class|import|require|"
    r"include|var|let|const|echo|print|console\.|\$\w+\s*=)\b.*[(){};=])")


def cambios_agregados(raiz, base):
    """Devuelve {ruta_relativa: set(lineas)} de líneas agregadas; None para archivo nuevo completo."""
    res = {}
    try:
        salida = subprocess.run(["git", "diff", "-U0", base], cwd=raiz, capture_output=True, encoding="utf-8",
                                errors="replace", timeout=60).stdout
        nuevos = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=raiz,
                                capture_output=True, encoding="utf-8", errors="replace", timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    archivo = None
    for linea in salida.splitlines():
        if linea.startswith("+++ b/"):
            archivo = linea[6:]
            res.setdefault(archivo, set())
        elif linea.startswith("@@") and archivo:
            m = re.search(r"\+(\d+)(?:,(\d+))?", linea)
            if m:
                ini, cant = int(m.group(1)), int(m.group(2) or 1)
                res[archivo].update(range(ini, ini + cant))
    for n in nuevos.splitlines():
        if n:
            res[n] = None
    return res


def palabras(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"([a-z])([A-Z])", r"\1 \2", texto)
    return {p for p in re.findall(r"[a-zA-Z]{3,}", texto.lower())}


def extraer(ext, lineas):
    """Devuelve lista de comentarios: dict(ini, fin, lineas_texto, codigo_siguiente, docblock)."""
    pref = PREF.get(ext, [])
    bloque = BLOQUES.get(ext, BLOQUE_C) if ext in BLOQUES else BLOQUE_C
    comentarios, actual, en_bloque = [], None, None

    def cerrar():
        nonlocal actual
        if actual:
            comentarios.append(actual)
            actual = None

    def codigo_despues(i):
        for j in range(i + 1, min(i + 3, len(lineas))):
            if lineas[j].strip():
                return lineas[j]
        return ""

    for i, crudo in enumerate(lineas):
        s = crudo.strip()
        n = i + 1
        if en_bloque:
            fin = en_bloque in s
            texto = s.split(en_bloque)[0].lstrip("*").strip()
            actual["fin"] = n
            actual["texto"].append(texto)
            if fin:
                actual["sig"] = codigo_despues(i)
                en_bloque = None
                cerrar()
            continue
        if bloque and s.startswith(bloque[0]):
            cerrar()
            cierre = bloque[1]
            cuerpo = s[len(bloque[0]):]
            doc = cuerpo.startswith("*") and not cuerpo.startswith("**/") and bloque[0] == "/*"
            actual = {"ini": n, "fin": n, "texto": [cuerpo.split(cierre)[0].lstrip("*").strip()], "sig": "", "doc": doc}
            if cierre in cuerpo:
                actual["sig"] = codigo_despues(i)
                cerrar()
            else:
                en_bloque = cierre
            continue
        marca = next((p for p in pref if s.startswith(p)), None)
        if marca and not (marca == "#" and ext == ".php" and s.startswith("#[")):
            texto = s[len(marca):].strip()
            if actual and actual["fin"] == n - 1 and not actual.get("bloque"):
                actual["fin"] = n
                actual["texto"].append(texto)
            else:
                cerrar()
                actual = {"ini": n, "fin": n, "texto": [texto], "sig": "", "doc": False}
            actual["sig"] = codigo_despues(i)
            continue
        cerrar()
        # comentario al final de una línea de código
        for p in pref:
            m = re.search(r"\s" + re.escape(p) + r"\s+(\S.*)$", crudo)
            if m and not (p in ("//",) and "://" in crudo):
                previo = crudo[:m.start()]
                if previo.count('"') % 2 == 0 and previo.count("'") % 2 == 0 and previo.strip():
                    comentarios.append({"ini": n, "fin": n, "texto": [m.group(1)], "sig": previo, "doc": False})
                break
    cerrar()
    return comentarios


def evaluar(c):
    """Devuelve lista de (id, mensaje) para un comentario."""
    textos = [t for t in c["texto"] if t]
    todo = " ".join(textos)
    if not todo or EXENTO.search(todo):
        return []
    res = []
    if any(BANNER.search(t) for t in textos):
        res.append(("COM-BANNER", "banner decorativo"))
    primera = next((t for t in textos if t and not BANNER.search(t)), "")
    if HISTORIAL.search(primera):
        res.append(("COM-HISTORIAL", "comentario de historial o autoría; eso lo guarda git"))
    for t in textos:
        m = TODO.search(t)
        if m and len(re.findall(r"\w+", m.group(2))) < 3:
            res.append(("COM-TODO", "TODO/FIXME sin motivo claro"))
            break
    fuertes = [t for t in textos if CODIGO_FUERTE.search(t) and not (len(t.split()) > 10 and t.endswith("."))]
    if fuertes and (len(fuertes) >= max(1, len(textos) // 2)):
        res.append(("COM-CODIGO", "parece código comentado; borrarlo (git lo conserva)"))
    elif not PORQUE.search(todo) and not c["doc"] and len(textos) == 1:
        pc = palabras(textos[0])
        if pc and len(textos[0].split()) <= 6 and len(pc & palabras(c["sig"])) / len(pc) >= 0.5:
            res.append(("COM-REPITE", "repite lo que ya dice el código; comentar solo el porqué"))
    return res


def analizar_archivo(ruta, ext, permitidas):
    try:
        lineas = ruta.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return [], 0, 0
    comentarios = extraer(ext, lineas)
    hallazgos, lineas_com = [], 0
    for c in comentarios:
        rango = range(c["ini"], c["fin"] + 1)
        if permitidas is not None and not any(n in permitidas for n in rango):
            continue
        lineas_com += len(rango)
        for id_c, msg in evaluar(c):
            hallazgos.append((id_c, c["ini"], msg))
    total = len(permitidas) if permitidas is not None else len([l for l in lineas if l.strip()])
    return hallazgos, lineas_com, total


def analizar(raiz, base="HEAD", todo=False):
    """Devuelve (lista de hallazgos, archivos_revisados, modo)."""
    cambios = None if todo else cambios_agregados(raiz, base)
    if not todo and cambios is None:
        return [], 0, "sin-git"
    hallazgos, revisados = [], 0
    if todo:
        candidatos = []
        for actual, carpetas, nombres in os.walk(raiz):
            carpetas[:] = [c for c in carpetas if c not in IGNORAR]
            candidatos += [(Path(actual) / n, None) for n in nombres]
    else:
        candidatos = [(raiz / rel, lineas) for rel, lineas in cambios.items()]
    for ruta, permitidas in candidatos:
        ext = ruta.suffix.lower()
        if ext not in PREF or not ruta.is_file() or ruta.name.endswith((".min.js", ".min.css")):
            continue
        if set(ruta.relative_to(raiz).parts) & IGNORAR:
            continue
        revisados += 1
        encontrados, n_com, total = analizar_archivo(ruta, ext, permitidas)
        rel = ruta.relative_to(raiz).as_posix()
        hallazgos += [(id_c, rel, linea, msg) for id_c, linea, msg in encontrados]
        if n_com >= 20 and total and n_com / total > 0.35:
            hallazgos.append(("COM-PROPORCION", rel, 1,
                              f"{n_com} de {total} líneas son comentarios ({n_com * 100 // total}%); dejar solo el porqué"))
    return hallazgos, revisados, "todo" if todo else "cambios"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--todo", action="store_true", help="revisar todo el proyecto y no solo lo modificado")
    ap.add_argument("--max", type=int, default=20)
    args = ap.parse_args()
    hallazgos, revisados, modo = analizar(Path(args.raiz).resolve(), args.base, args.todo)
    if modo == "sin-git":
        print("Comentarios: no es un repositorio git; usar --todo para revisar todo el proyecto.")
        sys.exit(0)
    alcance = "código modificado" if modo == "cambios" else "todo el proyecto"
    if not hallazgos:
        print(f"Comentarios: {revisados} archivos revisados ({alcance}), sin marcas.")
        sys.exit(0)
    print(f"Comentarios: {len(hallazgos)} marcas en {revisados} archivos ({alcance}).")
    for id_c, rel, linea, msg in hallazgos[:args.max]:
        print(f"  {id_c} {rel}:{linea} — {msg}")
    if len(hallazgos) > args.max:
        print(f"  … y {len(hallazgos) - args.max} más (usar --max).")
    sys.exit(1)


if __name__ == "__main__":
    main()
