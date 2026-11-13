#!/usr/bin/env python3
"""Impacto de un cambio sin gastar tokens: quién usa un símbolo, qué lo prueba y qué documento lo menciona.

Uso:
    python impacto.py <símbolo...> [--raiz .] [--max 8]   # llamadores, tests, documentos y configuración de cada símbolo
    python impacto.py <archivo>    [--raiz .] [--max 8]   # símbolos que define y quién los usa desde afuera
    python impacto.py --existe <palabras...>               # ¿ya hay algo parecido? antes de escribir uno nuevo
    python impacto.py --cambio [--base HEAD]               # símbolos que toca el cambio actual y quién los usa

Sirve para tres momentos: antes de modificar algo (¿a quién rompe?), antes de corregir un error (¿quiénes lo llaman?,
la causa se arregla una vez en el código compartido) y antes de escribir código nuevo (¿ya existe?).
Funciona con cualquier lenguaje: detecta definiciones con patrones generales (def, function, class, func, fn, struct,
create table…) y busca los usos por palabra completa. Es una ayuda: no entiende alcance ni herencia, así que los nombres
muy comunes dan ruido (se avisa). Solo lectura. Solo biblioteca estándar.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seguridad  # noqa: E402

EXT_CONFIG = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".xml", ".conf"}
EXT_DOC = {".md", ".rst", ".txt", ".adoc"}
DEFINICIONES = [
    re.compile(r"^\s*(?:async\s+)?def\s+(\w+)"),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:async\s+)?function\s*\*?\s*(\w+)"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\b"),
    re.compile(r"^\s*(?:export\s+)?(?:abstract\s+|final\s+|public\s+|static\s+)*(?:class|interface|trait|enum|struct|type)\s+(\w+)"),
    re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+)*function\s+&?(\w+)"),
    re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?(\w+)"),
    re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)"),
    re.compile(r"(?i)^\s*create\s+(?:or\s+replace\s+)?(?:table|view|function|procedure|index)\s+(?:if\s+not\s+exists\s+)?[\w.`\"\[\]]*?(\w+)[`\"\]]?\s*[(\s]"),
]
PALABRAS_COMUNES = {"main", "init", "run", "get", "set", "test", "name", "id", "data", "value", "result", "index", "self",
                    "args", "app", "main", "load", "save", "open", "close", "start", "stop", "list", "item", "key"}
RE_REQUISITO = re.compile(r"\b(?:RNF|RN|RU|RD|RF|RT|RI)-\d{1,4}\b")


def nombres_definidos(linea):
    res = []
    for rx in DEFINICIONES:
        m = rx.search(linea)
        if m and m.group(1) not in res:
            res.append(m.group(1))
    return res


def categoria(ruta_rel):
    partes = [p.lower() for p in Path(ruta_rel).parts]
    nombre = partes[-1]
    stem = Path(nombre).stem
    if {"test", "tests", "spec", "specs", "__tests__"} & set(partes) or stem.startswith("test_") or \
            stem.endswith(("_test", ".test", ".spec", "test", "tests")) and len(stem) > 4:
        return "tests"
    ext = Path(nombre).suffix
    if ext in EXT_DOC or partes[0] == "docs":
        return "documentos"
    if ext in EXT_CONFIG:
        return "configuración"
    return "código"


def archivos(raiz):
    """(ruta relativa, líneas) de los archivos de texto del proyecto, sin carpetas generadas ni la carpeta .git."""
    for ruta, texto in seguridad.archivos_de_texto(raiz):
        try:
            rel = ruta.relative_to(raiz).as_posix()
        except ValueError:
            continue
        if rel.startswith("docs/fuentes/") or rel.startswith("documentos-externos/"):
            continue
        yield rel, texto.splitlines()


def buscar_simbolo(raiz, simbolo):
    """Devuelve (definiciones, usos por categoría, requisitos mencionados en documentos)."""
    patron = re.compile(r"(?<![\w$])" + re.escape(simbolo) + r"(?![\w$])")
    definiciones, usos, requisitos = [], {"código": [], "tests": [], "documentos": [], "configuración": []}, set()
    for rel, lineas in archivos(raiz):
        cat = categoria(rel)
        for n, linea in enumerate(lineas, 1):
            if not patron.search(linea):
                continue
            if cat in ("código", "tests") and simbolo in nombres_definidos(linea):
                definiciones.append((rel, n, linea.strip()[:90]))
                continue
            usos[cat].append((rel, n, linea.strip()[:90]))
            if cat == "documentos":
                requisitos.update(RE_REQUISITO.findall(linea))
    return definiciones, usos, sorted(requisitos)


def informe_simbolo(raiz, simbolo, maximo):
    definiciones, usos, requisitos = buscar_simbolo(raiz, simbolo)
    total = sum(len(v) for v in usos.values())
    archivos_con_uso = len({u[0] for v in usos.values() for u in v})
    lineas = [f"Impacto de «{simbolo}»:"]
    if definiciones:
        lineas.append("  definición: " + "; ".join(f"{r}:{n}" for r, n, _ in definiciones[:4]) +
                      (f" (y {len(definiciones) - 4} más)" if len(definiciones) > 4 else ""))
    else:
        lineas.append("  definición: no se encontró en el código (¿es de una biblioteca, o el nombre está mal escrito?)")
    lineas.append(f"  usos fuera de la definición: {total} en {archivos_con_uso} archivos ("
                  + ", ".join(f"{k} {len(v)}" for k, v in usos.items()) + ")")
    for cat, items in usos.items():
        for rel, n, texto in items[:maximo]:
            lineas.append(f"    {cat}: {rel}:{n} — {texto}")
        if len(items) > maximo:
            lineas.append(f"    {cat}: … y {len(items) - maximo} más")
    if requisitos:
        lineas.append("  requisitos relacionados en la documentación: " + ", ".join(requisitos[:8]))
    if definiciones and not usos["tests"]:
        lineas.append("  AVISO: ningún test lo menciona; antes de cambiarlo, escribir el test desde la regla (senior-tdd)")
    if simbolo.lower() in PALABRAS_COMUNES or len(simbolo) < 4:
        lineas.append("  AVISO: nombre muy común: los usos pueden incluir otros símbolos con el mismo nombre")
    return lineas


def simbolos_de_archivo(raiz, ruta):
    ruta = Path(ruta)
    destino = ruta if ruta.is_absolute() else raiz / ruta
    nombres = []
    for linea in destino.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        for n in nombres_definidos(linea):
            if n not in nombres:
                nombres.append(n)
    return destino, nombres


def informe_archivo(raiz, ruta, maximo):
    destino, nombres = simbolos_de_archivo(raiz, ruta)
    try:
        rel = destino.resolve().relative_to(raiz).as_posix()
    except ValueError:
        rel = destino.name
    lineas = [f"Impacto del archivo {rel}: define {len(nombres)} símbolos"]
    for nombre in nombres[:25]:
        _, usos, _ = buscar_simbolo(raiz, nombre)
        externos = {c: [u for u in v if u[0] != rel] for c, v in usos.items()}
        total = sum(len(v) for v in externos.values())
        if total:
            lineas.append(f"  {nombre}: {total} usos externos (" + ", ".join(f"{k} {len(v)}" for k, v in externos.items() if v) + ")")
        else:
            lineas.append(f"  {nombre}: sin usos externos")
    patron = re.compile(r"(?<![\w$])" + re.escape(Path(rel).stem) + r"(?![\w$])")
    quienes = sorted({r for r, ls in archivos(raiz) if r != rel and any(patron.search(l) for l in ls)})
    if quienes:
        lineas.append(f"  mencionan «{Path(rel).stem}»: " + ", ".join(quienes[:maximo]) + (f" (y {len(quienes) - maximo} más)" if len(quienes) > maximo else ""))
    return lineas


def trocear(palabra):
    """Separa snake_case y camelCase en palabras en minúsculas."""
    partes = re.sub(r"([a-z0-9])([A-Z])", r" ", palabra).replace("_", " ").replace("-", " ").lower().split()
    return [p for p in partes if p]


def variantes(palabra):
    """La palabra y su forma sin plural (imagenes e imagen coinciden)."""
    res = {palabra}
    if len(palabra) > 3 and palabra.endswith("s"):
        res.add(palabra[:-1])
        if len(palabra) > 4 and palabra.endswith("es"):
            res.add(palabra[:-2])
    return res


def coincidencias(buscadas, nombre):
    del_nombre = [variantes(t) for t in trocear(nombre)]
    return sum(1 for q in buscadas if any(variantes(q) & v for v in del_nombre))


def buscar_existente(raiz, palabras, maximo=15):
    buscadas = {t for p in palabras for t in trocear(p)}
    candidatos = []
    for rel, lineas in archivos(raiz):
        if categoria(rel) not in ("código", "tests"):
            continue
        for n, linea in enumerate(lineas, 1):
            for nombre in nombres_definidos(linea):
                aciertos = coincidencias(buscadas, nombre)
                if aciertos:
                    candidatos.append((aciertos, nombre, rel, n))
    candidatos.sort(key=lambda c: (-c[0], c[2], c[3]))
    return candidatos[:maximo]


def informe_existente(raiz, palabras):
    candidatos = buscar_existente(raiz, palabras)
    if not candidatos:
        return [f"¿Ya existe algo para «{' '.join(palabras)}»? No hay definiciones parecidas: se puede escribir lo mínimo, "
                "después de mirar si la biblioteca estándar o una dependencia ya instalada lo resuelve."]
    lineas = [f"¿Ya existe algo para «{' '.join(palabras)}»? Definiciones parecidas (reusar antes de escribir):"]
    for c, nombre, rel, n in candidatos:
        lineas.append(f"  {nombre} — {rel}:{n} ({c} palabras en común)")
    return lineas


def diff_del_cambio(raiz, base):
    p = subprocess.run(["git", "diff", "-U0", base], cwd=raiz, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    return p.stdout if p.returncode == 0 else ""


def simbolos_del_diff(texto):
    """[(archivo, símbolo)] de lo que toca un diff: definiciones en las líneas nuevas o en el contexto de cada bloque."""
    res, archivo = [], None
    for linea in texto.splitlines():
        if linea.startswith("+++ b/"):
            archivo = linea[6:]
        elif linea.startswith("@@") and archivo:
            contexto = linea.split("@@")[-1]
            for n in nombres_definidos(contexto):
                res.append((archivo, n))
        elif linea.startswith("+") and not linea.startswith("+++") and archivo:
            for n in nombres_definidos(linea[1:]):
                res.append((archivo, n))
    vistos, unicos = set(), []
    for par in res:
        if par not in vistos:
            vistos.add(par)
            unicos.append(par)
    return unicos


def informe_cambio(raiz, base, maximo):
    pares = simbolos_del_diff(diff_del_cambio(raiz, base))
    if not pares:
        return ["Impacto del cambio: no se detectaron símbolos modificados (¿sin cambios, o solo documentos y datos?)."]
    lineas = [f"Impacto del cambio actual contra {base}: {len(pares)} símbolos tocados"]
    for archivo, nombre in pares[:20]:
        _, usos, _ = buscar_simbolo(raiz, nombre)
        externos = {c: [u for u in v if u[0] != archivo] for c, v in usos.items()}
        total = sum(len(v) for v in externos.values())
        detalle = ", ".join(f"{k} {len(v)}" for k, v in externos.items() if v) or "sin usos externos"
        aviso = "" if usos["tests"] else "  [sin tests que lo mencionen]"
        lineas.append(f"  {nombre} ({archivo}): {total} usos externos ({detalle}){aviso}")
    return lineas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("objetivo", nargs="*", help="símbolos o archivos; con --existe, palabras")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--max", type=int, default=8, help="usos mostrados por categoría")
    ap.add_argument("--existe", action="store_true", help="buscar definiciones parecidas a las palabras dadas")
    ap.add_argument("--cambio", action="store_true", help="símbolos que toca el cambio actual y quién los usa")
    ap.add_argument("--base", default="HEAD", help="con --cambio: contra qué se compara (HEAD por defecto)")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if args.cambio:
        print("\n".join(informe_cambio(raiz, args.base, args.max)))
        return 0
    if not args.objetivo:
        ap.error("indicar un símbolo, un archivo, --existe <palabras> o --cambio")
    if args.existe:
        print("\n".join(informe_existente(raiz, args.objetivo)))
        return 0
    for objetivo in args.objetivo:
        es_archivo = (raiz / objetivo).is_file() or Path(objetivo).is_file()
        print("\n".join(informe_archivo(raiz, objetivo, args.max) if es_archivo else informe_simbolo(raiz, objetivo, args.max)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
