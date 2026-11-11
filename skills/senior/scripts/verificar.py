#!/usr/bin/env python3
"""Verificador del paquete senior: controles automáticos con salida corta.

La idea es que el trabajo de control lo haga este script y el modelo solo lea
un resumen de pocas líneas (ahorra miles de tokens por revisión).

Uso:
    python verificar.py [chequeo] [--raiz .] [--ficha docs/cambios/x.md] [--base HEAD] [--auditar]

Chequeos (sin argumento corre "todo"):
  tamano      tamaño del cambio actual y nivel de ceremonia recomendado
  alcance     archivos tocados que no figuran en el "Alcance" de la ficha
  deuda       TODO/FIXME/HACK en el código y formato de docs/deuda-tecnica.md
  estado      ESTADO.md al día, cambios sin guardar, pasos abiertos en fichas
  docs        marca requisitos sin test e IDs sin documento (solo lectura: el
              índice se regenera aparte con senior-memoria/scripts/indexar_docs.py indexar)
  fuentes     documentos e imágenes de documentos-externos/ sin procesar (convertir a Markdown o reducir a 1024 px)
              (se leen solo los .md de docs/fuentes/; ver senior-relevar/scripts/convertir_fuentes.py)
  requisitos  calidad del texto de docs/requisitos/: encabezado, IDs, enlaces, ejemplos verificables,
              palabras ambiguas y estado (ver senior-docs/scripts/revisar_requisitos.py)
  readme      el README.md de GitHub existe, está completo, enlaza a docs/,
              menciona cada carpeta y se actualizó con el cambio (sin excepciones)
  texto       límites de extensión, párrafos repetidos, secciones vacías e
              información perdida en docs/ (ver texto.py)
  diagramas   legibilidad de los diagramas Mermaid (ver diagramas.py)
  comentarios calidad de los comentarios del código modificado (ver comentarios.py)
  diseno      si el proyecto tiene docs/diseno/, comprueba que el código use las variables de diseño
              (sin copiar sus valores) y las etiquetas del contrato de campos; si no, no dice nada
  autoria     REGLA INVIOLABLE: en los commits nuevos solo figura el usuario; sin
              Claude, coautores ni pies de atribución (ver senior-git/scripts/guardia_autoria.py)
  seguridad   alertas por lenguaje, secretos, logs sensibles (ver seguridad.py)
              con --auditar suma el chequeo de dependencias (usa la red)

Código de salida: 0 todo bien, 1 hay algo para revisar. Solo biblioteca estándar.
"""
import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comentarios  # noqa: E402
import diagramas  # noqa: E402
import seguridad  # noqa: E402
import texto  # noqa: E402

MARCAS_DEUDA = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
EXT_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".kt", ".cs", ".go", ".rs", ".rb",
              ".c", ".cc", ".cpp", ".h", ".hpp", ".swift", ".lua", ".sql", ".sh", ".html", ".css", ".vue"}


def git(raiz, *args):
    try:
        p = subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return p.stdout.strip(), p.returncode
    except (OSError, subprocess.TimeoutExpired):
        return "", -1


def es_repo(raiz):
    return git(raiz, "rev-parse", "--is-inside-work-tree")[0] == "true"


GENERADOS = {"docs/INDEX.md", "docs/.grafo.json"}  # los regenera el indexador; no cuentan como cambio


def archivos_cambiados(raiz, base):
    """Archivos modificados respecto de `base` más los nuevos sin seguimiento."""
    modificados, _ = git(raiz, "diff", "--name-only", base)
    nuevos, _ = git(raiz, "ls-files", "--others", "--exclude-standard")
    return sorted({a for a in (modificados.splitlines() + nuevos.splitlines()) if a and a not in GENERADOS})


def chequeo_tamano(raiz, args):
    if not es_repo(raiz):
        return ["Tamaño: la carpeta no es un repositorio git; no se puede medir el cambio."], True
    salida, _ = git(raiz, "diff", "--numstat", args.base)
    lineas, archivos = 0, set()
    for fila in salida.splitlines():
        partes = fila.split("\t")
        if len(partes) == 3 and partes[2] not in GENERADOS:
            archivos.add(partes[2])
            lineas += (int(partes[0]) if partes[0].isdigit() else 0) + (int(partes[1]) if partes[1].isdigit() else 0)
    for nuevo in git(raiz, "ls-files", "--others", "--exclude-standard")[0].splitlines():
        if nuevo in GENERADOS:
            continue
        archivos.add(nuevo)
        try:
            lineas += len((raiz / nuevo).read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            pass
    n = len(archivos)
    if n == 0:
        return ["Tamaño: sin cambios."], True
    if n <= 1 and lineas <= 5:
        nivel, accion = "trivial", "una línea en ESTADO.md; sin ficha"
    elif n <= 3 and lineas <= 50:
        nivel, accion = "chico", "una línea en ESTADO.md; commit atómico"
    elif n <= 10 and lineas <= 300:
        nivel, accion = "mediano", "ficha propia; evaluar diagrama si cruza capas; PR con descripción completa"
    else:
        nivel, accion = "grande", "ficha propia; considerar dividir en cambios menores; diagrama de secuencia; revisar plan con el usuario"
    return [f"Tamaño: {nivel} ({n} archivos, {lineas} líneas) → {accion}."], True


def ultima_ficha(raiz):
    fichas = sorted((raiz / "docs" / "cambios").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True) \
        if (raiz / "docs" / "cambios").is_dir() else []
    return fichas[0] if fichas else None


def alcance_de_ficha(ficha):
    texto = ficha.read_text(encoding="utf-8-sig", errors="replace")
    m = re.search(r"^##\s+Alcance\s*$(.*?)(?=^##\s|\Z)", texto, re.MULTILINE | re.DOTALL)
    if not m:
        return None
    return [re.sub(r"^[-*]\s*", "", l).strip().strip("`") for l in m.group(1).splitlines()
            if l.strip().startswith(("-", "*")) and l.strip("-* \t")]


def chequeo_alcance(raiz, args):
    ficha = Path(args.ficha) if args.ficha else ultima_ficha(raiz)
    if not ficha or not ficha.exists():
        return ["Alcance: no hay ficha de cambio contra la cual comparar (se omite)."], True
    patrones = alcance_de_ficha(ficha)
    if patrones is None:
        return [f"Alcance: la ficha {ficha.name} no tiene sección '## Alcance' con una lista de archivos."], False
    if not es_repo(raiz):
        return ["Alcance: no es un repositorio git (se omite)."], True
    fuera = [a for a in archivos_cambiados(raiz, args.base)
             if not a.startswith("docs/") and not any(fnmatch.fnmatch(a, p) or a.startswith(p.rstrip("*/") + "/") for p in patrones)]
    if not fuera:
        return [f"Alcance: todo lo tocado está dentro de lo previsto en {ficha.name}."], True
    return [f"Alcance: {len(fuera)} archivos fuera de lo previsto en {ficha.name} (¿ampliar la ficha o revertir?):"] + \
           [f"  {a}" for a in fuera[:15]], False


def chequeo_deuda(raiz, args):
    marcas = []
    for ruta, texto in seguridad.archivos_de_texto(raiz):
        if ruta.suffix.lower() not in EXT_CODIGO:
            continue
        for i, l in enumerate(texto.splitlines(), 1):
            if MARCAS_DEUDA.search(l):
                marcas.append(f"{ruta.relative_to(raiz).as_posix()}:{i}")
    salida, ok = [], True
    if marcas:
        salida.append(f"Deuda: {len(marcas)} marcas TODO/FIXME/HACK en el código (ej.: {', '.join(marcas[:5])}).")
    archivo = raiz / "docs" / "deuda-tecnica.md"
    if archivo.exists():
        sin_motivo = [l.strip()[:70] for l in archivo.read_text(encoding="utf-8-sig").splitlines()
                      if re.match(r"^\s*-\s+\S", l) and "motivo:" not in l.lower() and not l.strip().startswith("- ejemplo")]
        if sin_motivo:
            ok = False
            salida.append(f"Deuda: {len(sin_motivo)} entradas de deuda-tecnica.md sin 'motivo:' (ej.: {sin_motivo[0]})")
    if not salida:
        salida.append("Deuda: sin marcas pendientes ni entradas sin motivo.")
    return salida, ok


def chequeo_estado(raiz, args):
    salida, ok = [], True
    estado = raiz / "docs" / "ESTADO.md"
    if not estado.exists():
        return ["Estado: falta docs/ESTADO.md (crearlo con senior-memoria)."], False
    if es_repo(raiz):
        ultimo, _ = git(raiz, "log", "-1", "--format=%ct")
        if ultimo.isdigit() and estado.stat().st_mtime + 60 < int(ultimo):
            ok = False
            salida.append("Estado: ESTADO.md es más viejo que el último commit; actualizarlo.")
        sin_guardar = [l for l in git(raiz, "status", "--porcelain")[0].splitlines() if l]
        if sin_guardar:
            salida.append(f"Estado: {len(sin_guardar)} archivos con cambios sin guardar en git.")
    abiertas = []
    carpeta = raiz / "docs" / "cambios"
    for ficha in sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []:
        texto = ficha.read_text(encoding="utf-8-sig", errors="replace")
        if re.search(r"(?im)^\s*\**estado\**\s*:\s*\**\s*en curso", texto):
            pasos = len(re.findall(r"^\s*-\s*\[ \]", texto, re.MULTILINE))
            abiertas.append(f"{ficha.name} ({pasos} pasos abiertos)")
    if abiertas:
        salida.append("Estado: fichas en curso: " + "; ".join(abiertas) + ".")
    if not salida:
        salida.append("Estado: ESTADO.md al día, sin cambios sueltos ni fichas abiertas.")
    return salida, ok


def chequeo_docs(raiz, args):
    carpeta = raiz / "docs"
    if not carpeta.is_dir():
        return ["Docs: no existe la carpeta docs/ (se omite)."], True
    indexador = Path(__file__).resolve().parents[2] / "senior-memoria" / "scripts" / "indexar_docs.py"
    if not indexador.exists():
        return ["Docs: no se encontró senior-memoria/scripts/indexar_docs.py."], False
    # Solo lectura: se calcula el índice en memoria; verificar nunca modifica el árbol de trabajo.
    import importlib.util
    espec = importlib.util.spec_from_file_location("indexar_docs", indexador)
    modulo = importlib.util.module_from_spec(espec)
    try:
        espec.loader.exec_module(modulo)
        grafo = modulo.construir_grafo(raiz, carpeta)
        avisos = [l.strip() for l in modulo.generar_indice(grafo).splitlines() if l.startswith("**")]
    except Exception as e:  # noqa: BLE001 - se informa cualquier fallo del indexador
        return [f"Docs: el indexador falló: {str(e)[:200]}"], False
    pista = "" if (carpeta / "INDEX.md").exists() else " (INDEX.md no existe: generarlo con indexar_docs.py indexar)"
    if not avisos:
        return [f"Docs: todos los requisitos tienen test y todos los IDs tienen documento{pista}."], True
    return ["Docs: pendientes de trazabilidad:"] + [f"  {a.replace('**', '')}" for a in avisos], False


def chequeo_diagramas(raiz, args):
    carpeta = raiz / "docs"
    if not carpeta.is_dir():
        return ["Diagramas: no existe docs/ (se omite)."], True
    total, problemas = diagramas.analizar(raiz, carpeta)
    if not problemas:
        return [f"Diagramas: {total} revisados, todos legibles."], True
    return [f"Diagramas: {len(problemas)} problemas en {total} diagramas:"] + [f"  {p}" for p in problemas[:10]], False


def chequeo_readme(raiz, args):
    """El README de GitHub se mantiene al día en cada cambio, sin excepciones."""
    readme = next((raiz / n for n in ("README.md", "readme.md", "Readme.md") if (raiz / n).exists()), None)
    if not readme:
        return ["README: no existe README.md en la raíz (crearlo con senior-docs/plantillas/readme.md)."], False
    contenido = readme.read_text(encoding="utf-8-sig", errors="replace")
    bajo = contenido.lower()
    problemas = []
    if "(completar)" in contenido:
        problemas.append("tiene secciones sin completar (marca '(completar)')")
    if (raiz / "docs").is_dir() and "docs/" not in bajo:
        problemas.append("no enlaza a la documentación (docs/INDEX.md)")
    carpetas = sorted(d.name for d in raiz.iterdir()
                      if d.is_dir() and not d.name.startswith(".") and d.name not in seguridad.IGNORAR | {"docs"})
    sin_mencion = [c for c in carpetas if c.lower() not in bajo]
    if sin_mencion:
        problemas.append("no menciona las carpetas: " + ", ".join(sin_mencion))
    hay_tests = any(n in {"test", "tests", "spec", "__tests__"} for n in (c.lower() for c in carpetas))
    if hay_tests and not re.search(r"test|prueba", bajo):
        problemas.append("hay tests pero no explica cómo ejecutarlos")
    if es_repo(raiz):
        cambiados = archivos_cambiados(raiz, args.base)
        codigo = [a for a in cambiados if not a.startswith("docs/") and a.lower() != readme.name.lower()]
        if codigo and readme.name not in cambiados:
            problemas.append(f"hay {len(codigo)} archivos modificados y el README no se actualizó en este cambio "
                             "(revisar y actualizar la parte afectada; no agregar registros de cambios)")
    if not problemas:
        return ["README: al día."], True
    return ["README: " + "; ".join(problemas) + "."], False


EXT_FUENTE = {".html", ".htm", ".php", ".vue", ".svelte", ".jsx", ".tsx", ".js", ".ts", ".twig", ".ejs", ".css"}


def chequeo_requisitos(raiz, args):
    """Calidad del texto de docs/requisitos/ (estructura, ambigüedad, ejemplos); la trazabilidad la ve `docs`."""
    if not (raiz / "docs" / "requisitos").is_dir():
        return [], True
    revisor = Path(__file__).resolve().parents[2] / "senior-docs" / "scripts" / "revisar_requisitos.py"
    if not revisor.exists():
        return ["Requisitos: no se encontró senior-docs/scripts/revisar_requisitos.py."], False
    import importlib.util
    espec = importlib.util.spec_from_file_location("revisar_requisitos", revisor)
    modulo = importlib.util.module_from_spec(espec)
    try:
        espec.loader.exec_module(modulo)
        total, provisorios, hallazgos = modulo.revisar(raiz)
    except Exception as e:  # noqa: BLE001 - se informa cualquier fallo del revisor
        return [f"Requisitos: el revisor falló: {str(e)[:200]}"], False
    fallas = [h for h in hallazgos if h["sev"] == "FALLA"]
    avisos = len(hallazgos) - len(fallas)
    extra = f"; {provisorios} provisorios esperan confirmación" if provisorios else ""
    lineas = [f"Requisitos: {total} revisados, {len(fallas)} fallas, {avisos} avisos{extra}."]
    lineas += [f"  {h['archivo']}:{h['linea']} — {h['msg']}" for h in fallas[:3]]
    if hallazgos:
        lineas.append("  Detalle: python senior-docs/scripts/revisar_requisitos.py")
    return lineas, not fallas


def tabla_columna(texto, columna):
    """Valores de una columna de las tablas Markdown cuyo encabezado la contiene."""
    valores, indice = [], None
    for linea in texto.splitlines():
        if not linea.strip().startswith("|"):
            indice = None
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if indice is None:
            nombres = [c.lower() for c in celdas]
            indice = nombres.index(columna.lower()) if columna.lower() in nombres else -1
        elif indice >= 0 and indice < len(celdas) and not set(celdas[indice]) <= set("-: "):
            valores.append(celdas[indice])
    return valores


def chequeo_diseno(raiz, args):
    """Fidelidad de la implementación al diseño de docs/diseno/: variables de diseño y etiquetas del contrato de campos."""
    diseno = raiz / "docs" / "diseno"
    if not diseno.is_dir():
        return [], True
    lineas, ok = [], True
    fuentes = [f for f in raiz.rglob("*") if f.is_file() and f.suffix.lower() in EXT_FUENTE
               and not (set(f.relative_to(raiz).parts) & {"docs", "node_modules", "vendor", "dist", "build", ".git", ".claude"})]
    textos = {f: f.read_text(encoding="utf-8", errors="replace") for f in fuentes}
    tokens = diseno / "sistema" / "tokens.css"
    if tokens.exists() and fuentes:
        valores = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{3,8}\b", tokens.read_text(encoding="utf-8", errors="replace"))}
        copiados = {}
        for f, t in textos.items():
            if f.suffix.lower() in (".css", ".html", ".htm", ".vue", ".svelte"):
                for c in {x.lower() for x in re.findall(r"#[0-9a-fA-F]{3,8}\b", t)} & valores:
                    copiados.setdefault(c, f.name)
        if copiados:
            ejemplos = ", ".join(f"{c} en {n}" for c, n in list(copiados.items())[:3])
            lineas.append(f"Diseño: {len(copiados)} colores de las variables de diseño están copiados como literales ({ejemplos}): "
                          "usar var(--…) para no duplicar los valores.")
            ok = False
    contratos = sorted((diseno / "campos").glob("*.md")) if (diseno / "campos").is_dir() else []
    if contratos and fuentes:
        codigo = "\n".join(textos.values()).lower()
        faltan = []
        for f in contratos:
            etiquetas = [e for e in tabla_columna(f.read_text(encoding="utf-8-sig", errors="replace"), "Etiqueta final")
                         if e and not e.startswith("(")]
            faltan += [(f.stem, e) for e in etiquetas if e.lower() not in codigo]
        if faltan:
            lineas.append("Diseño: etiquetas del contrato de campos que no aparecen en el código: "
                          + "; ".join(f"«{e}» ({n})" for n, e in faltan[:4]) + ". Implementarlas exactamente como figuran.")
            ok = False
        else:
            lineas.append(f"Diseño: las etiquetas de {len(contratos)} contratos de campos aparecen en el código.")
    return lineas, ok


def chequeo_autoria(raiz, args):
    """Regla inviolable: en lo que se sube a GitHub figura únicamente el usuario."""
    guardia = Path(__file__).resolve().parents[2] / "senior-git" / "scripts" / "guardia_autoria.py"
    if not guardia.exists():
        return ["Autoría: no se encontró senior-git/scripts/guardia_autoria.py."], False
    if not es_repo(raiz):
        return ["Autoría: no es un repositorio git (se omite)."], True
    import importlib.util
    espec = importlib.util.spec_from_file_location("guardia_autoria", guardia)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    lista = modulo.commits(raiz, modulo.rango_por_defecto(raiz, None))
    problemas, avisos = modulo.revisar(raiz, lista)
    if problemas:
        return [f"Autoría: {len(problemas)} problemas (solo debe figurar el usuario):"] + \
               [f"  {p}" for p in problemas[:10]], False
    faltan = [l for l in modulo.asegurar_git(raiz, True)[0] + modulo.asegurar_claude(True)[0] if l.startswith(("FALTA", "NO"))]
    if faltan:
        return ([f"Autoría: {len(lista)} commits revisados, sin rastro de Claude ni coautores, pero la guardia no está completa:"]
                + [f"  {l}" for l in faltan]
                + ["  Activarla: python senior-git/scripts/guardia_autoria.py asegurar"]), False
    return [f"Autoría: {len(lista)} commits revisados, sin rastro de Claude ni coautores; guardia activa."], True


def chequeo_fuentes(raiz, args):
    """Documentos externos: ninguno se lee sin convertirlo antes (carpeta documentos-externos/)."""
    conversor = Path(__file__).resolve().parents[2] / "senior-relevar" / "scripts" / "convertir_fuentes.py"
    if not conversor.exists():
        return [], True
    import importlib.util
    espec = importlib.util.spec_from_file_location("convertir_fuentes", conversor)
    modulo = importlib.util.module_from_spec(espec)
    try:
        espec.loader.exec_module(modulo)
        pendientes, total = modulo.estado_de_fuentes(raiz)
    except Exception as e:  # noqa: BLE001 - se informa cualquier fallo del conversor
        return [f"Fuentes: no se pudo revisar: {str(e)[:150]}"], False
    if not total:
        return [], True
    if pendientes:
        nombres = ", ".join(o.name for o, _ in pendientes[:4])
        return [f"Fuentes: {len(pendientes)} de {total} documentos externos sin convertir o cambiados ({nombres}). "
                "No leerlos directo: correr senior-relevar/scripts/convertir_fuentes.py y leer docs/fuentes/."], False
    return [f"Fuentes: {total} documentos externos convertidos y al día."], True


def chequeo_comentarios(raiz, args):
    hallazgos, revisados, modo = comentarios.analizar(raiz, args.base)
    if modo == "sin-git":
        return ["Comentarios: no es un repositorio git (usar comentarios.py --todo)."], True
    if not hallazgos:
        return [f"Comentarios: {revisados} archivos modificados revisados, sin marcas."], True
    salida = [f"Comentarios: {len(hallazgos)} marcas en el código modificado:"]
    salida += [f"  {i} {r}:{l} — {m}" for i, r, l, m in hallazgos[:10]]
    if len(hallazgos) > 10:
        salida.append(f"  … y {len(hallazgos) - 10} más (ejecutar comentarios.py).")
    return salida, False


def chequeo_texto(raiz, args):
    carpeta = raiz / "docs"
    if not carpeta.is_dir():
        return ["Texto: no existe docs/ (se omite)."], True
    hallazgos = texto.analizar(raiz, carpeta, args.base)
    if not hallazgos:
        return ["Texto: documentos dentro de límites, sin repetición ni información perdida."], True
    salida = [f"Texto: {len(hallazgos)} avisos:"]
    salida += [f"  {i} {r} — {m}" for i, r, m in hallazgos[:10]]
    if len(hallazgos) > 10:
        salida.append(f"  … y {len(hallazgos) - 10} más (ejecutar texto.py).")
    return salida, False


def chequeo_seguridad(raiz, args):
    hallazgos, auditoria, vulnerable = seguridad.analizar(raiz, args.auditar)
    salida = []
    if hallazgos:
        salida.append(f"Seguridad: {len(hallazgos)} hallazgos para revisar:")
        for h in hallazgos[:10]:
            iso = f" [ISO {h['iso']}]" if h["iso"] else ""
            salida.append(f"  {h['id']} {h['archivo']}:{h['linea']}{iso}")
        if len(hallazgos) > 10:
            salida.append(f"  … y {len(hallazgos) - 10} más (ejecutar seguridad.py para el detalle).")
    else:
        salida.append("Seguridad: sin hallazgos de patrón.")
    salida.extend(f"  {a}" for a in auditoria)
    return salida, not hallazgos and not vulnerable


CHEQUEOS = {
    "tamano": chequeo_tamano, "alcance": chequeo_alcance, "deuda": chequeo_deuda, "estado": chequeo_estado,
    "docs": chequeo_docs, "fuentes": chequeo_fuentes, "requisitos": chequeo_requisitos, "readme": chequeo_readme, "texto": chequeo_texto, "diagramas": chequeo_diagramas,
    "comentarios": chequeo_comentarios, "autoria": chequeo_autoria,
    "diseno": chequeo_diseno, "seguridad": chequeo_seguridad,
}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chequeo", nargs="?", default="todo", choices=["todo", *CHEQUEOS])
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--ficha", default=None)
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--auditar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    elegidos = list(CHEQUEOS) if args.chequeo == "todo" else [args.chequeo]
    todo_bien = True
    for nombre in elegidos:
        lineas, ok = CHEQUEOS[nombre](raiz, args)
        todo_bien = todo_bien and ok
        if lineas:  # los chequeos de diseño no dicen nada si el proyecto no tiene diseno/
            print("\n".join(lineas))
    if args.chequeo == "todo":
        print("Resultado: " + ("todo en orden." if todo_bien else "hay puntos para revisar."))
    sys.exit(0 if todo_bien else 1)


if __name__ == "__main__":
    main()
