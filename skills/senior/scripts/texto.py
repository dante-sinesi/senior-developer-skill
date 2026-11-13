#!/usr/bin/env python3
"""Vigila el exceso y la redundancia de texto en la documentación (docs/).

Uso:
    python texto.py [--raiz .] [--docs docs] [--base HEAD] [--pr archivo.md] [--max 10]

Qué revisa:
  LIMITE      documentos que superan su extensión máxima (líneas con contenido,
              sin encabezado ni vacías). Por defecto: ESTADO 60, requisito 40,
              ficha 50, ADR 60, descripción de PR 30. Ajustables en
              docs/.texto.json, por ejemplo {"limites": {"requisito": 60}}.
  REPETIDO    párrafos iguales o casi iguales en documentos distintos: dejarlo
              en su lugar de referencia y enlazar desde el otro.
  VACIA       secciones con encabezado y sin contenido.
  PERDIDA     párrafos que estaban en la versión anterior (git, --base) de un
              documento y ya no aparecen en ningún documento: posible
              información perdida al mover o recortar. Si la baja fue
              intencional (dato obsoleto), ignorar el aviso.

REGLA DE DESBORDE: dividir o mover, nunca recortar. Destinos sugeridos:
  ESTADO   -> docs/historial/AAAA-MM.md, ADR, ficha
  requisito-> dividir en requisitos atómicos o anexo enlazado
  ficha    -> fichas menores bajo una ficha general; pendientes; ADR
  ADR      -> un ADR por decisión; anexo enlazado
  PR       -> enlazar a ficha, requisitos y ADR

Es una comparación de texto, no de significado: una reescritura con otras
palabras no se detecta. Código de salida: 0 sin avisos, 1 con avisos.
Solo biblioteca estándar.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LIMITES = {"estado": 60, "requisito": 40, "ficha": 50, "adr": 60, "pr": 30}
DESTINO = {
    "estado": "mover el historial a docs/historial/AAAA-MM.md, decisiones a un ADR y el detalle a su ficha",
    "requisito": "dividir en requisitos atómicos con ID propio o mover tablas largas a un anexo enlazado",
    "ficha": "dividir en fichas menores bajo una ficha general; ideas a pendientes; decisiones a un ADR",
    "adr": "una decisión por ADR; análisis y evidencia a un anexo enlazado",
    "pr": "enlazar a la ficha, los requisitos y los ADR en vez de repetirlos",
}
EXCLUIR_PARTES = {"historial", "archivo", "fuentes"}  # fuentes: documentos externos convertidos, no se editan
MIN_PALABRAS_REPETIDO = 14
MIN_PALABRAS_PERDIDA = 8


def leer(ruta):
    return ruta.read_text(encoding="utf-8-sig", errors="replace")


def sin_encabezado(texto):
    if texto.startswith("---"):
        fin = texto.find("\n---", 3)
        if fin != -1:
            return texto[fin + 4:]
    return texto


def normalizar(texto):
    texto = re.sub(r"\[\[([^\]|#]+)[^\]]*\]\]", r"\1", texto)
    texto = re.sub(r"[*_`>#|\-]", " ", texto.lower())
    return " ".join(re.findall(r"\w+", texto))


def parrafos(texto):
    """Bloques de prosa (sin encabezados, tablas ni código)."""
    cuerpo = re.sub(r"```.*?```", "", sin_encabezado(texto), flags=re.DOTALL)
    res = []
    for bloque in re.split(r"\n\s*\n", cuerpo):
        limpio = bloque.strip()
        if not limpio or limpio.startswith(("#", "|", "<!--")):
            continue
        res.append(limpio)
    return res


def tipo_de(ruta, raiz_docs):
    rel = ruta.relative_to(raiz_docs).as_posix().lower()
    if rel == "estado.md":
        return "estado"
    if rel.startswith("cambios/"):
        return "ficha"
    if rel.startswith("decisiones/"):
        return "adr"
    if rel.startswith("requisitos/"):
        return "requisito"
    return None


def lineas_con_contenido(texto):
    cuerpo = sin_encabezado(texto)
    return len([l for l in cuerpo.splitlines() if l.strip() and not l.strip().startswith("#")])


def cargar_limites(carpeta):
    limites = dict(LIMITES)
    ruta = carpeta / ".texto.json"
    if ruta.exists():
        try:
            limites.update(json.loads(leer(ruta)).get("limites", {}))
        except (OSError, ValueError):
            pass
    return limites


def documentos(raiz, carpeta):
    for ruta in sorted(carpeta.rglob("*.md")):
        partes = set(ruta.relative_to(carpeta).parts)
        if ruta.name == "INDEX.md" or partes & EXCLUIR_PARTES:
            continue
        yield ruta


def huella(texto, k=5):
    p = normalizar(texto).split()
    return {" ".join(p[i:i + k]) for i in range(max(1, len(p) - k + 1))}


def similitud(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def revisar_limites(raiz, carpeta, limites):
    res = []
    for ruta in documentos(raiz, carpeta):
        tipo = tipo_de(ruta, carpeta)
        if tipo and tipo in limites:
            n = lineas_con_contenido(leer(ruta))
            if n > limites[tipo]:
                res.append(("LIMITE", ruta.relative_to(raiz).as_posix(),
                            f"{n} líneas (máx. {limites[tipo]}). Dividir o mover: {DESTINO[tipo]}"))
    return res


def revisar_repetidos(raiz, carpeta):
    items = []
    for ruta in documentos(raiz, carpeta):
        for p in parrafos(leer(ruta)):
            if len(p.split()) >= MIN_PALABRAS_REPETIDO:
                items.append((ruta.relative_to(raiz).as_posix(), p, huella(p)))
    items = items[:1500]
    res, vistos = [], set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][0] == items[j][0]:
                continue
            if similitud(items[i][2], items[j][2]) >= 0.8 and (i, j) not in vistos:
                vistos.add((i, j))
                extracto = " ".join(items[i][1].split()[:9]) + "…"
                res.append(("REPETIDO", items[i][0],
                            f"«{extracto}» también está en {items[j][0]}. Dejarlo en su lugar de referencia y enlazar"))
    return res


def revisar_vacias(raiz, carpeta):
    res = []
    for ruta in documentos(raiz, carpeta):
        lineas = sin_encabezado(leer(ruta)).splitlines()
        for i, l in enumerate(lineas):
            m = re.match(r"^(#{2,6})\s+(.+)$", l)
            if not m:
                continue
            nivel = len(m.group(1))
            contenido = False
            for sig in lineas[i + 1:]:
                if not sig.strip():
                    continue
                es_encabezado = re.match(r"^(#{1,6})\s", sig)
                # un subencabezado inmediato cuenta como contenido; uno del mismo nivel o superior, no
                contenido = not es_encabezado or len(es_encabezado.group(1)) > nivel
                break
            if not contenido:
                res.append(("VACIA", ruta.relative_to(raiz).as_posix(), f"sección «{m.group(2)}» sin contenido"))
    return res


def git(raiz, *args):
    try:
        p = subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return p.stdout, p.returncode
    except (OSError, subprocess.TimeoutExpired):
        return "", -1


def revisar_perdidas(raiz, carpeta, base):
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        return []
    rel_docs = carpeta.relative_to(raiz).as_posix()
    modificados = git(raiz, "diff", "--name-only", base, "--", rel_docs)[0].split()
    corpus = [normalizar(p) for ruta in carpeta.rglob("*.md") for p in parrafos(leer(ruta))]
    texto_total = " ".join(corpus)
    huellas = [huella(p) for p in corpus]
    res = []
    for rel in modificados:
        if rel.endswith("INDEX.md") or not rel.endswith(".md"):
            continue
        # ESTADO.md y las fichas son documentos vivos que se reescriben a propósito
        # (su historial va a docs/historial/); avisar de cada reemplazo sería puro ruido.
        if tipo_de(raiz / rel, carpeta) in ("estado", "ficha"):
            continue
        anterior, codigo = git(raiz, "show", f"{base}:{rel}")
        if codigo != 0:
            continue
        for p in parrafos(anterior.lstrip("﻿")):
            if len(p.split()) < MIN_PALABRAS_PERDIDA:
                continue
            norm = normalizar(p)
            if norm in texto_total:
                continue
            h = huella(p)
            if any(similitud(h, otra) >= 0.6 for otra in huellas):
                continue
            extracto = " ".join(p.split()[:10]) + "…"
            res.append(("PERDIDA", rel, f"«{extracto}» ya no aparece en ningún documento (¿se movió sin dejarlo en su lugar?)"))
    return res


def revisar_pr(archivo, limites):
    ruta = Path(archivo)
    if not ruta.exists():
        return [("LIMITE", archivo, "no existe el archivo de descripción del PR")]
    n = len([l for l in leer(ruta).splitlines() if l.strip() and not l.strip().startswith("#")])
    if n > limites["pr"]:
        return [("LIMITE", archivo, f"{n} líneas (máx. {limites['pr']}). Dividir o mover: {DESTINO['pr']}")]
    return []


def analizar(raiz, carpeta, base="HEAD", pr=None):
    limites = cargar_limites(carpeta)
    hallazgos = revisar_limites(raiz, carpeta, limites) + revisar_repetidos(raiz, carpeta) + \
        revisar_vacias(raiz, carpeta) + revisar_perdidas(raiz, carpeta, base)
    if pr:
        hallazgos += revisar_pr(pr, limites)
    return hallazgos


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--pr", default=None, help="archivo con la descripción del PR a medir")
    ap.add_argument("--max", type=int, default=10)
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    carpeta = raiz / args.docs
    if not carpeta.is_dir():
        print(f"Texto: no existe la carpeta {args.docs} (se omite).")
        sys.exit(0)
    hallazgos = analizar(raiz, carpeta, args.base, args.pr)
    if not hallazgos:
        print("Texto: documentos dentro de límites, sin repetición ni información perdida.")
        sys.exit(0)
    print(f"Texto: {len(hallazgos)} avisos.")
    for id_t, rel, msg in hallazgos[:args.max]:
        print(f"  {id_t} {rel} — {msg}")
    if len(hallazgos) > args.max:
        print(f"  … y {len(hallazgos) - args.max} más (usar --max).")
    sys.exit(1)


if __name__ == "__main__":
    main()
