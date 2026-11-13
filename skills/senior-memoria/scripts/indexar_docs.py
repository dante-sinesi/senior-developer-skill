#!/usr/bin/env python3
"""Indexador y grafo de conceptos para la documentación viva de un proyecto.

Solo usa la biblioteca estándar de Python (3.10+). No depende de Obsidian ni de
ninguna herramienta externa.

Uso:
    python indexar_docs.py indexar  [--raiz .] [--docs docs]
    python indexar_docs.py vecinos   <id>      [--raiz .] [--docs docs]

Qué hace "indexar":
  1. Lee todos los .md de docs/ (encabezado opcional con id, tipo, titulo,
     resumen, tags).
  2. Construye el grafo: documentos enlazados entre sí ([[enlaces]] o enlaces
     markdown) y requisitos/ADRs (RN-001, RF-012, RNF-003...) mencionados en
     otros documentos, en el código o en los tests.
  3. Detecta clases, funciones y tablas del código con los perfiles de
     senior-lenguajes y las suma al mapa (solo en .grafo.json, no en INDEX.md).
  4. Escribe docs/INDEX.md (índice legible, con trazabilidad) y
     docs/.grafo.json (para consultar sin leer todo).
La salida es determinista (sin fechas), así no ensucia el historial de git.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# Prefijos de ID: RN negocio, RU usuario, RD dominio, RF funcional,
# RNF no funcional, RT transición, RI interfaz externa, ADR decisión.
PATRON_ID = re.compile(r"\b(?:RNF|RN|RU|RD|RF|RT|RI|ADR)-\d{1,4}\b")
PATRON_WIKI = re.compile(r"\[\[([^\]\|#]+)(?:[#\|][^\]]*)?\]\]")
PATRON_MD = re.compile(r"\[[^\]]*\]\(([^)\s#]+\.md)(?:#[^)]*)?\)")
EXT_CODIGO = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".kt", ".cs", ".go",
    ".rs", ".rb", ".c", ".cc", ".cpp", ".h", ".hpp", ".swift", ".lua", ".sql",
    ".sh", ".ps1", ".html", ".css", ".vue", ".svelte",
}
IGNORAR = {
    ".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv",
    "venv", ".idea", ".vscode", "coverage", ".next",
}
ORDEN_TIPOS = [
    "negocio", "usuario", "dominio", "funcional", "no-funcional",
    "transicion", "interfaz", "arquitectura", "decision", "diagrama", "otro",
]
TIPOS_REQUISITO = {"RN": "negocio", "RU": "usuario", "RD": "dominio",
                   "RF": "funcional", "RNF": "no-funcional",
                   "RT": "transicion", "RI": "interfaz"}


def leer(ruta):
    return ruta.read_text(encoding="utf-8-sig", errors="replace")


def separar_encabezado(texto):
    """Devuelve (dict_encabezado, cuerpo). Soporta un YAML mínimo clave: valor."""
    if not texto.startswith("---"):
        return {}, texto
    fin = texto.find("\n---", 3)
    if fin == -1:
        return {}, texto
    meta = {}
    for linea in texto[3:fin].splitlines():
        if ":" not in linea:
            continue
        clave, _, valor = linea.partition(":")
        valor = valor.strip().strip("\"'")
        if valor.startswith("[") and valor.endswith("]"):
            meta[clave.strip()] = [v.strip().strip("\"'") for v in valor[1:-1].split(",") if v.strip()]
        else:
            meta[clave.strip()] = valor
    return meta, texto[fin + 4:]


def primer_parrafo(cuerpo):
    for bloque in re.split(r"\n\s*\n", cuerpo):
        limpio = bloque.strip()
        if limpio and not limpio.startswith(("#", "```", "|", "---")):
            return " ".join(limpio.split())[:160]
    return ""


def titulo_de(cuerpo, defecto):
    m = re.search(r"^#\s+(.+)$", cuerpo, re.MULTILINE)
    return m.group(1).strip() if m else defecto


def tipo_por_id(id_doc):
    m = re.match(r"([A-Z]+)-\d+$", id_doc)
    if not m:
        return None
    if m.group(1) == "ADR":
        return "decision"
    return TIPOS_REQUISITO.get(m.group(1))


def cargar_documentos(raiz, carpeta_docs):
    docs = {}
    for ruta in sorted(carpeta_docs.rglob("*.md")):
        if ruta.name == "INDEX.md":
            continue
        rel = ruta.relative_to(raiz).as_posix()
        meta, cuerpo = separar_encabezado(leer(ruta))
        id_doc = meta.get("id") or ruta.stem
        tipo = meta.get("tipo") or tipo_por_id(id_doc) or "otro"
        m_estado = re.search(r"(?mi)^##\s+Estado\s*\n+\s*(\S[^\n]*)", cuerpo) or re.search(r"(?mi)^\*\*Estado:\*\*\s*(\S[^\n]*)", cuerpo)
        docs[id_doc] = {
            "estado": m_estado.group(1).strip().lower() if m_estado else "",
            "id": id_doc,
            "tipo": tipo,
            "titulo": meta.get("titulo") or titulo_de(cuerpo, ruta.stem),
            "resumen": meta.get("resumen") or primer_parrafo(cuerpo),
            "ruta": rel,
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "verificado_por": meta.get("verificado_por") if isinstance(meta.get("verificado_por"), str) else "",
            "_texto": cuerpo,
        }
    return docs


def resolver(destino, docs, por_ruta):
    destino = destino.strip()
    if destino in docs:
        return destino
    base = Path(destino).stem
    if base in docs:
        return base
    for id_doc, d in docs.items():
        if d["titulo"].lower() == destino.lower():
            return id_doc
    return por_ruta.get(Path(destino).name)


def escanear_codigo(raiz, carpeta_docs):
    """Devuelve {ruta: set(ids)} para archivos de código que mencionan IDs."""
    hallados = {}
    for ruta in raiz.rglob("*"):
        if not ruta.is_file() or ruta.suffix.lower() not in EXT_CODIGO:
            continue
        partes = set(ruta.relative_to(raiz).parts)
        if partes & IGNORAR:
            continue
        try:
            ruta.relative_to(carpeta_docs)
            continue
        except ValueError:
            pass
        ids = set(PATRON_ID.findall(leer(ruta)))
        if ids:
            hallados[ruta.relative_to(raiz).as_posix()] = ids
    return hallados


def es_test(rel):
    bajo = rel.lower()
    return any(s in bajo for s in ("test", "spec", "__tests__"))


def cargar_perfiles():
    """Perfiles de lenguaje (senior-lenguajes/perfiles/*.json) indexados por extensión."""
    env = os.environ.get("SENIOR_PERFILES")
    carpeta = Path(env) if env else Path(__file__).resolve().parents[2] / "senior-lenguajes" / "perfiles"
    por_ext = {}
    if not carpeta.is_dir():
        return por_ext
    for ruta in sorted(carpeta.glob("*.json")):
        if ruta.name.startswith("_"):
            continue
        try:
            perfil = json.loads(ruta.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        simbolos = []
        for s in perfil.get("simbolos", []):
            try:
                simbolos.append((s["tipo"], re.compile(s["patron"])))
            except (KeyError, re.error):
                continue
        for ext in perfil.get("extensiones", []):
            por_ext[ext.lower()] = simbolos
    return por_ext


def escanear_simbolos(raiz, carpeta_docs, max_bytes=300_000):
    """Devuelve {ruta_relativa: [(tipo, nombre, linea)]} usando los perfiles de lenguaje."""
    perfiles = cargar_perfiles()
    hallados = {}
    if not perfiles:
        return hallados
    for ruta in raiz.rglob("*"):
        if not ruta.is_file() or not perfiles.get(ruta.suffix.lower()):
            continue
        if set(ruta.relative_to(raiz).parts) & IGNORAR or ruta.stat().st_size > max_bytes:
            continue
        try:
            ruta.relative_to(carpeta_docs)
            continue
        except ValueError:
            pass
        encontrados = []
        for n, linea in enumerate(leer(ruta).splitlines(), 1):
            for tipo, rx in perfiles[ruta.suffix.lower()]:
                m = rx.search(linea)
                if m:
                    encontrados.append((tipo, m.group(1), n))
                    break
        if encontrados:
            hallados[ruta.relative_to(raiz).as_posix()] = encontrados
    return hallados


def construir_grafo(raiz, carpeta_docs):
    docs = cargar_documentos(raiz, carpeta_docs)
    por_ruta = {Path(d["ruta"]).name: i for i, d in docs.items()}
    aristas = set()

    for id_doc, d in docs.items():
        texto = d["_texto"]
        for destino in PATRON_WIKI.findall(texto) + PATRON_MD.findall(texto):
            hacia = resolver(destino, docs, por_ruta)
            if hacia and hacia != id_doc:
                aristas.add((id_doc, hacia, "enlaza"))
        for mencion in set(PATRON_ID.findall(texto)):
            if mencion in docs and mencion != id_doc and (id_doc, mencion, "enlaza") not in aristas:
                aristas.add((id_doc, mencion, "menciona"))

    nodos = [{k: v for k, v in d.items() if not k.startswith("_")} for d in docs.values()]
    for id_doc, d in docs.items():  # requisito que se verifica con un script en lugar de un test
        if d.get("verificado_por"):
            script = d["verificado_por"]
            if script not in {n["id"] for n in nodos}:
                nodos.append({"id": script, "tipo": "test", "titulo": script, "resumen": "", "ruta": script, "tags": []})
            aristas.add((id_doc, script, "verificado_en"))
    for rel, ids in escanear_codigo(raiz, carpeta_docs).items():
        tipo = "test" if es_test(rel) else "codigo"
        nodos.append({"id": rel, "tipo": tipo, "titulo": rel, "resumen": "", "ruta": rel, "tags": []})
        for id_req in ids:
            if id_req in docs:
                aristas.add((id_req, rel, "verificado_en" if tipo == "test" else "implementado_en"))
            else:
                aristas.add((id_req, rel, "sin_documento"))

    ids_nodos = {n["id"] for n in nodos}
    for rel, simbolos in escanear_simbolos(raiz, carpeta_docs).items():
        if rel not in ids_nodos:
            nodos.append({"id": rel, "tipo": "test" if es_test(rel) else "codigo", "titulo": rel,
                          "resumen": "", "ruta": rel, "tags": []})
            ids_nodos.add(rel)
        for tipo_s, nombre, linea in simbolos:
            id_s = f"{rel}::{nombre}"
            if id_s in ids_nodos:
                continue
            ids_nodos.add(id_s)
            nodos.append({"id": id_s, "tipo": "simbolo", "titulo": nombre,
                          "resumen": f"{tipo_s} en {rel}:{linea}", "ruta": rel, "tags": [tipo_s]})
            aristas.add((rel, id_s, "define"))

    nodos.sort(key=lambda n: (n["tipo"], n["id"]))
    lista = [{"desde": a, "hasta": b, "tipo": t} for a, b, t in sorted(aristas)]
    return {"nodos": nodos, "aristas": lista}


def generar_indice(grafo):
    nodos = {n["id"]: n for n in grafo["nodos"]}
    docs = [n for n in grafo["nodos"] if n["tipo"] not in ("test", "codigo", "simbolo")]
    lineas = [
        "# Índice de documentación",
        "",
        "Archivo generado por `indexar_docs.py`. No editar a mano: se regenera.",
        "",
    ]
    for tipo in ORDEN_TIPOS + sorted({d["tipo"] for d in docs} - set(ORDEN_TIPOS)):
        grupo = [d for d in docs if d["tipo"] == tipo]
        if not grupo:
            continue
        lineas.append(f"## {tipo.capitalize()}")
        lineas.append("")
        for d in grupo:
            resumen = f" — {d['resumen']}" if d["resumen"] else ""
            lineas.append(f"- [[{d['id']}]] [{d['titulo']}]({Path(d['ruta']).as_posix().split('/', 1)[-1]}){resumen}")
        lineas.append("")

    # Trazabilidad requisito -> tests / código
    reqs = [d for d in docs if PATRON_ID.fullmatch(d["id"]) and d["tipo"] != "decision"]
    if reqs:
        lineas += ["## Trazabilidad", "", "| Requisito | Tests | Código |", "|---|---|---|"]
        sin_test, provisorios_sin_test = [], 0
        for d in reqs:
            tests = [a["hasta"] for a in grafo["aristas"] if a["desde"] == d["id"] and a["tipo"] == "verificado_en"]
            codigo = [a["hasta"] for a in grafo["aristas"] if a["desde"] == d["id"] and a["tipo"] == "implementado_en"]
            if not tests and d.get("estado", "").startswith("provisorio"):
                provisorios_sin_test += 1  # una hipótesis sin confirmar todavía no necesita un test
            elif not tests:
                sin_test.append(d["id"])
            lineas.append(f"| {d['id']} | {', '.join(tests) or '—'} | {', '.join(codigo) or '—'} |")
        lineas.append("")
        if sin_test:
            lineas += ["**Requisitos sin test:** " + ", ".join(sin_test), ""]
        if provisorios_sin_test:
            lineas += [f"Requisitos provisorios sin test: {provisorios_sin_test} (esperan confirmación; no cuentan como pendientes).", ""]
    huerfanos = sorted({a["desde"] for a in grafo["aristas"] if a["tipo"] == "sin_documento"})
    if huerfanos:
        lineas += ["**IDs usados en el código pero sin documento:** " + ", ".join(huerfanos), ""]
    return "\n".join(lineas).rstrip() + "\n"


def cmd_indexar(raiz, carpeta_docs):
    if not carpeta_docs.is_dir():
        sys.exit(f"No existe la carpeta de documentación: {carpeta_docs}")
    grafo = construir_grafo(raiz, carpeta_docs)
    (carpeta_docs / "INDEX.md").write_text(generar_indice(grafo), encoding="utf-8", newline="\n")
    (carpeta_docs / ".grafo.json").write_text(
        json.dumps(grafo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"Índice generado: {len(grafo['nodos'])} nodos, {len(grafo['aristas'])} relaciones.")


def cargar_grafo(carpeta_docs):
    ruta = carpeta_docs / ".grafo.json"
    if not ruta.exists():
        sys.exit("Falta .grafo.json: ejecutá primero 'indexar'.")
    return json.loads(leer(ruta))


def vecinos_de(grafo, id_nodo):
    res = []
    for a in grafo["aristas"]:
        if a["desde"] == id_nodo:
            res.append((a["tipo"], a["hasta"], "->"))
        elif a["hasta"] == id_nodo:
            res.append((a["tipo"], a["desde"], "<-"))
    return res


def tokens_al_abrir(raiz, nodo):
    """Tokens aproximados (caracteres / 4) de abrir el archivo del nodo, o None si no se puede medir.

    Sirve para decidir qué abrir: un resultado chico se lee entero; uno grande se lee por partes. Un símbolo
    no se mide: abrirlo es leer unas líneas del archivo, no el archivo entero."""
    if raiz is None or nodo["tipo"] == "simbolo":
        return None
    ruta = Path(raiz) / nodo["ruta"]
    try:
        return max(1, len(ruta.read_text(encoding="utf-8", errors="replace")) // 4) if ruta.is_file() else None
    except OSError:
        return None


def mostrar(grafo, nodo, raiz=None):
    print(f"{nodo['id']} [{nodo['tipo']}] {nodo['titulo']}")
    tokens = tokens_al_abrir(raiz, nodo)
    # senior-ignore: SEC-LOG-SENSIBLE (es una cantidad de tokens de texto, no una credencial)
    print(f"  ruta: {nodo['ruta']}" + (f" (~{tokens} tokens al abrirlo)" if tokens else ""))
    if nodo["resumen"]:
        print(f"  resumen: {nodo['resumen']}")
    for tipo, otro, sentido in vecinos_de(grafo, nodo["id"]):
        print(f"  {sentido} {tipo}: {otro}")


def cmd_vecinos(carpeta_docs, id_nodo):
    grafo = cargar_grafo(carpeta_docs)
    nodo = next((n for n in grafo["nodos"] if n["id"] == id_nodo), None)
    if not nodo:
        sys.exit(f"No existe el nodo: {id_nodo}")
    mostrar(grafo, nodo, carpeta_docs.parent)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["indexar", "vecinos"])
    ap.add_argument("argumento", nargs="?", help="id (vecinos)")
    ap.add_argument("--raiz", default=".", help="raíz del proyecto (por defecto, la carpeta actual)")
    ap.add_argument("--docs", default="docs", help="carpeta de documentación dentro de la raíz")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    carpeta_docs = (raiz / args.docs).resolve()
    if args.accion == "indexar":
        cmd_indexar(raiz, carpeta_docs)
    else:
        if not args.argumento:
            ap.error(f"'{args.accion}' necesita un argumento")
        cmd_vecinos(carpeta_docs, args.argumento)


if __name__ == "__main__":
    main()
