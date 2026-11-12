#!/usr/bin/env python3
"""Documentación inferida de un proyecto existente: diagramas, requisitos, decisiones y reglas por confirmar.

Todo lo que genera es PROVISORIO: sale del código (lo que el sistema hace hoy), no de una regla confirmada, y cada dato
cita su evidencia (archivo:línea). Nada se confirma solo: las reglas de negocio candidatas salen como una consulta por
lotes para que las responda el usuario. Sin --aplicar solo muestra qué crearía y no escribe nada.

Uso:
    python documentar.py plan        [--raiz .]               # qué hay, qué se generaría y cuánto cuesta cada etapa
    python documentar.py estructura  [--raiz .] [--aplicar]   # diagramas: módulos, clases por módulo, entidad-relación
    python documentar.py interfaces  [--raiz .] [--aplicar]   # RI: rutas HTTP y variables de entorno
    python documentar.py dominio     [--raiz .] [--aplicar]   # RD: una entidad por cada tabla o modelo
    python documentar.py adr         [--raiz .] [--aplicar]   # ADR: decisiones visibles del stack
    python documentar.py reglas      [--raiz .] [--aplicar]   # consulta por lotes con reglas de negocio candidatas
    python documentar.py todo        [--raiz .] [--aplicar]   # las cinco etapas anteriores (todas por script, sin tokens)
    python documentar.py secuencias  [--raiz .]               # flujos candidatos para dibujar a mano un diagrama de secuencia
    python documentar.py requisito   --tipo RF --titulo "…" --evidencia archivo:línea [--modulo m] [--descripcion "…"]
    python documentar.py secuencia   --titulo "…" --pregunta "…" --archivo diagrama.mmd --evidencia archivo:línea
    python documentar.py confirmar-diagrama docs/diagramas/x.md   # el usuario lo confirmó: deja de ser provisorio y de regenerarse
    python documentar.py progreso    [--raiz .]               # qué módulos ya tienen requisitos funcionales y secuencias
    python documentar.py evidencia   [--raiz .]               # comprueba que cada cita archivo:línea exista

Agregar --refrescar a una etapa vuelve a escribir los requisitos y decisiones que SIGUEN provisorios; los que el usuario
confirmó o editó a mano no se tocan. Los diagramas generados llevan una marca en su primera línea: sin esa marca se
consideran editados a mano y no se pisan. Lenguajes: PHP, JavaScript o TypeScript y Python. Solo biblioteca estándar.
"""
import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analisis as an  # noqa: E402 motivo: sys.path se ajusta justo antes de importarlo

MARCA = ("<!-- generado por documentar.py: provisorio, inferido del código. Se regenera con `documentar.py {etapa} --aplicar`; "
         "para editarlo a mano, borrar esta línea. -->")
MARCA_RE = re.compile(r"<!--\s*generado por documentar\.py")
TIPOS = {"RN": ("negocio", "negocio"), "RU": ("usuario", "usuario"), "RD": ("dominio", "dominio"), "RF": ("funcional", "funcional"),
         "RNF": ("no-funcional", "no-funcional"), "RT": ("transicion", "transicion"), "RI": ("interfaces", "interfaces")}
RE_EVIDENCIA = re.compile(r"([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?")
MAX_ENTIDADES_ER = 10
MAX_CLASES = 10
MAX_MIEMBROS = 8
MAX_NODOS_MODULOS = 15
MAX_RD = 25
MAX_PREGUNTAS = 15


def slug(texto):
    sin_acentos = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower()).strip("-") or "raiz"


def identificador(texto):
    return re.sub(r"\W", "_", texto) or "x"


class Resultado:
    def __init__(self, aplicar):
        self.aplicar = aplicar
        self.creados, self.actualizados, self.omitidos = [], [], []
        self.ultimo = {}  # último ID asignado por tipo en esta corrida, para numerar bien aunque no se escriba

    def escribir(self, raiz, rel, texto, refrescable=True):
        """Escribe un documento generado. No pisa lo que alguien editó o confirmó (sin la marca de generado)."""
        ruta = Path(raiz) / rel
        if not ruta.exists():
            self.creados.append(rel)
        else:
            actual = ruta.read_text(encoding="utf-8-sig", errors="replace")
            if not refrescable or not MARCA_RE.search(actual[:900]):
                self.omitidos.append(rel)
                return
            if actual.strip() == texto.strip():
                return
            self.actualizados.append(rel)
        if self.aplicar:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(texto, encoding="utf-8", newline="\n")

    def informe(self, etapa):
        lineas = []
        verbo = "Se crearon" if self.aplicar else "Se crearían"
        if self.creados:
            lineas.append(f"{verbo} {len(self.creados)}: " + ", ".join(self.creados[:8]) + (f" y {len(self.creados) - 8} más" if len(self.creados) > 8 else ""))
        if self.actualizados:
            lineas.append(f"{'Se actualizaron' if self.aplicar else 'Se actualizarían'} {len(self.actualizados)}: " + ", ".join(self.actualizados[:6]))
        if self.omitidos:
            lineas.append(f"Ya existían {len(self.omitidos)} y no se tocaron (confirmados o editados a mano; los que siguen provisorios "
                          "se actualizan con --refrescar): " + ", ".join(self.omitidos[:6]))
        if not (self.creados or self.actualizados or self.omitidos):
            lineas.append("Nada para generar en esta etapa.")
        if not self.aplicar and (self.creados or self.actualizados):
            lineas.append(f"No se escribió nada: agregar --aplicar para generar ({etapa}).")
        return lineas


def encabezado(titulo, resumen, tipo, etiquetas=(), extra=None):
    meta = ["---", f"tipo: {tipo}", f"titulo: {titulo}", f"resumen: {resumen}", f"tags: [{', '.join(etiquetas)}]"]
    for k, v in (extra or {}).items():
        meta.append(f"{k}: {v}")
    return "\n".join(meta) + "\n---\n"


def bloque_diagrama(titulo, pregunta, mermaid):
    return f"### {titulo}\n\n{pregunta}\n\n```mermaid\n{mermaid.rstrip()}\n```\n"


def documento_diagramas(etapa, titulo, resumen, intro, bloques):
    return (encabezado(titulo, resumen, "diagrama", ["diagrama", "inferido"]) + MARCA.format(etapa=etapa) + "\n\n"
            + f"# {titulo}\n\n{intro}\n\n" + "\n".join(bloques))


def diagrama_modulos(proyecto):
    tamano, aristas = an.dependencias(proyecto)
    if len(tamano) < 2:
        return None
    visibles = [m for m, _ in tamano.most_common(MAX_NODOS_MODULOS - 1)] if len(tamano) > MAX_NODOS_MODULOS else list(tamano)
    visibles = sorted(visibles)
    ids = {m: f"m{i}" for i, m in enumerate(visibles)}
    otros = [m for m in tamano if m not in ids]
    if otros:
        ids["(otros)"] = "otros"
    lineas = ["flowchart LR"]
    for m in visibles:
        lineas.append(f'    {ids[m]}["{m} ({tamano[m]})"]')
    if otros:
        lineas.append(f'    otros["otros módulos ({len(otros)})"]')
    agrupadas = defaultdict(int)
    for (a, b), n in aristas.items():
        agrupadas[(ids.get(a, ids.get("(otros)")), ids.get(b, ids.get("(otros)")))] += n
    dibujadas = 0
    for (a, b), n in sorted(agrupadas.items()):
        if a and b and a != b:
            lineas.append(f"    {a} -->|{n}| {b}")
            dibujadas += 1
    nota = ("Cada flecha va del módulo que importa al módulo importado y el número es la cantidad de importaciones. "
            "Entre paréntesis, la cantidad de archivos de cada módulo.")
    if not dibujadas:
        nota = "No se detectaron dependencias entre módulos con este análisis (puede haber acoplamiento que no se ve en las importaciones)."
    return bloque_diagrama("Dependencias entre módulos", f"¿Qué módulo usa a qué otro módulo? {nota}", "\n".join(lineas))


def diagrama_clases(clases_modulo, parte, total_partes):
    nombres = {c["nombre"] for c in clases_modulo}
    lineas = ["classDiagram"]
    for c in clases_modulo:
        miembros = sorted(c["metodos"], key=lambda m: (m[0] != "+", m[1]))[:MAX_MIEMBROS]
        lineas.append(f"    class {identificador(c['nombre'])} {{")
        if c["clase"] in ("interface", "trait", "enum"):
            lineas.append(f"        <<{c['clase']}>>")
        for vis, nombre in miembros:
            lineas.append(f"        {vis}{identificador(nombre)}()")
        lineas.append("    }")
    for c in clases_modulo:
        for base in c["bases"]:
            if base in nombres:
                lineas.append(f"    {identificador(base)} <|-- {identificador(c['nombre'])}")
        for i in c["interfaces"]:
            if i in nombres:
                lineas.append(f"    {identificador(i)} <|.. {identificador(c['nombre'])}")
    sufijo = f" (parte {parte} de {total_partes})" if total_partes > 1 else ""
    return lineas, sufijo


def documentos_clases(proyecto):
    """{ruta relativa: texto} de un documento por módulo con al menos dos clases."""
    out = {}
    for modulo, lista in sorted(an.clases(proyecto).items()):
        unicas, vistos = [], set()
        for c in sorted(lista, key=lambda c: (-(len(c["bases"]) + len(c["interfaces"])), c["nombre"])):
            if c["nombre"] not in vistos:
                vistos.add(c["nombre"])
                unicas.append(c)
        if len(unicas) < 2:
            continue
        total = len(unicas)
        omitidas = max(0, total - 3 * MAX_CLASES)
        unicas = unicas[:3 * MAX_CLASES]
        partes = [unicas[i:i + MAX_CLASES] for i in range(0, len(unicas), MAX_CLASES)]
        bloques = []
        for n, grupo in enumerate(partes, 1):
            lineas, sufijo = diagrama_clases(grupo, n, len(partes))
            bloques.append(bloque_diagrama(f"Clases del módulo {modulo}{sufijo}",
                                           f"¿Qué clases tiene el módulo {modulo} y cómo se heredan? Se muestran hasta {MAX_MIEMBROS} métodos por clase.",
                                           "\n".join(lineas)))
        evidencia = ", ".join(f"`{c['rel']}:{c['linea']}`" for c in unicas[:5])
        intro = (f"Clases inferidas del código del módulo `{modulo}` ({total} en total). Evidencia: {evidencia}."
                 + (f" Quedan {omitidas} clases sin dibujar para respetar el límite de legibilidad." if omitidas else ""))
        out[f"docs/diagramas/clases-{slug(modulo)}.md"] = documento_diagramas(
            "estructura", f"Clases del módulo {modulo}", f"Diagramas de clases inferidos del módulo {modulo}.", intro, bloques)
    return out


def documento_er(proyecto):
    ts = an.tablas(proyecto)
    if not ts:
        return None
    vecinos = defaultdict(set)
    for nombre, t in ts.items():
        for _, destino in t["fks"]:
            vecinos[nombre].add(destino)
            vecinos[destino].add(nombre)
    visto, componentes = set(), []
    for nombre in sorted(ts, key=lambda n: (-len(vecinos[n]), n)):
        if nombre in visto:
            continue
        pila, comp = [nombre], []
        while pila:
            x = pila.pop(0)
            if x in visto:
                continue
            visto.add(x)
            comp.append(x)
            pila += sorted(vecinos[x] - visto)
        componentes.append(comp)
    conectados = [c for c in componentes if len(c) > 1]
    sueltas = sorted(x for c in componentes if len(c) == 1 for x in c)
    grupos = []
    for comp in conectados:
        grupos += [comp[i:i + MAX_ENTIDADES_ER] for i in range(0, len(comp), MAX_ENTIDADES_ER)]
    grupos += [sueltas[i:i + MAX_ENTIDADES_ER] for i in range(0, len(sueltas), MAX_ENTIDADES_ER)]
    bloques = []
    for n, grupo in enumerate(grupos, 1):
        lineas = ["erDiagram"]
        for nombre in grupo:
            t = ts[nombre]
            fks = {c for c, _ in t["fks"]}
            cols = sorted(t["columnas"], key=lambda c: (not c[2], c[0] not in fks, c[0]))[:MAX_MIEMBROS]
            lineas.append(f"    {identificador(nombre)} {{")
            for col, tipo, pk in cols:
                marca = " PK" if pk else (" FK" if col in fks else "")
                lineas.append(f"        {identificador(tipo or 'campo')} {identificador(col)}{marca}")
            lineas.append("    }")
        for nombre in grupo:
            for col, destino in ts[nombre]["fks"]:
                if destino in grupo:
                    lineas.append(f'    {identificador(destino)} ||--o{{ {identificador(nombre)} : "{col}"')
        titulo = "Tablas y relaciones" + (f" (parte {n} de {len(grupos)})" if len(grupos) > 1 else "")
        con_relacion = any(destino in grupo for nombre in grupo for _, destino in ts[nombre]["fks"])
        pregunta = "¿Qué datos guarda el sistema y cómo se vinculan?" if con_relacion else "¿Qué tablas hay que no se relacionan con otras?"
        bloques.append(bloque_diagrama(titulo, pregunta + f" Se muestran hasta {MAX_MIEMBROS} columnas por tabla.", "\n".join(lineas)))
    evidencia = ", ".join(f"`{t['rel']}:{t['linea']}`" for t in list(ts.values())[:5])
    intro = f"Tablas y relaciones inferidas del esquema ({len(ts)} tablas). Evidencia: {evidencia}."
    return documento_diagramas("estructura", "Tablas y relaciones", "Diagrama entidad-relación inferido del esquema.", intro, bloques)


def etapa_estructura(proyecto, raiz, res):
    bloque = diagrama_modulos(proyecto)
    if bloque:
        res.escribir(raiz, "docs/diagramas/modulos.md", documento_diagramas(
            "estructura", "Módulos y dependencias", "Mapa de módulos y de qué módulo usa a cuál, inferido de las importaciones.",
            "Mapa inferido de las importaciones del código; no incluye las dependencias que el análisis no puede ver.", [bloque]))
    for rel, texto in documentos_clases(proyecto).items():
        res.escribir(raiz, rel, texto)
    er = documento_er(proyecto)
    if er:
        res.escribir(raiz, "docs/diagramas/entidad-relacion.md", er)


def ids_existentes(raiz, prefijo):
    base = Path(raiz) / "docs"
    maximo = 0
    for f in base.rglob("*.md") if base.is_dir() else []:
        m = re.match(rf"{prefijo}-(\d+)", f.stem, re.I)
        if m:
            maximo = max(maximo, int(m.group(1)))
        else:
            try:
                for m2 in re.finditer(rf"(?m)^id:\s*{prefijo}-(\d+)", f.read_text(encoding="utf-8-sig", errors="replace")[:600]):
                    maximo = max(maximo, int(m2.group(1)))
            except OSError:
                pass
    return maximo


def buscar_generado(raiz, clave):
    """Ruta del documento ya generado con esa clave, o None."""
    base = Path(raiz) / "docs"
    for f in base.rglob("*.md") if base.is_dir() else []:
        try:
            if f"generado: {clave}\n" in f.read_text(encoding="utf-8-sig", errors="replace")[:900] + "\n":
                return f
        except OSError:
            pass
    return None


def es_provisorio(texto):
    m = re.search(r"(?mi)^##\s+Estado\s*\n+\s*(\S[^\n]*)", texto) or re.search(r"(?mi)^\*\*Estado:\*\*\s*(\S[^\n]*)", texto)
    return bool(m and m.group(1).strip().lower().startswith("provisorio"))


def cuerpo_requisito(ident, titulo, descripcion, evidencias, sin_ejemplos=True):
    ev = " ".join(f"`{e}`" for e in evidencias)
    partes = [f"# {ident}: {titulo}", "", "## Descripción", "", descripcion.strip(), ""]
    if sin_ejemplos:
        partes += ["## Ejemplos verificables", "", "Sin ejemplos: el requisito es provisorio y sale del código, no de una regla confirmada.", ""]
    partes += ["## Origen", "", "Inferido del código; no lo confirmó nadie.", f"Evidencia: {ev}", "", "## Estado", "", "provisorio", ""]
    return "\n".join(partes)


def escribir_requisito(raiz, res, tipo, titulo, resumen, descripcion, evidencias, clave, etiquetas=(), modulo=None, refrescar=False):
    """Crea un requisito provisorio con el siguiente ID del tipo. Devuelve el ID o None si ya existía."""
    previo = buscar_generado(raiz, clave) if clave else None
    if previo is not None:
        texto_previo = previo.read_text(encoding="utf-8-sig", errors="replace")
        if not (refrescar and es_provisorio(texto_previo)):
            res.omitidos.append(previo.relative_to(raiz).as_posix())
            return None
        ident = previo.stem.split("-", 2)[0] + "-" + previo.stem.split("-", 2)[1]
        rel = previo.relative_to(raiz).as_posix()
        accion = "actualizar"
    else:
        numero = max(ids_existentes(raiz, tipo), res.ultimo.get(tipo, 0)) + 1
        res.ultimo[tipo] = numero
        ident = f"{tipo}-{numero:03d}"
        rel = f"docs/requisitos/{TIPOS[tipo][1]}/{ident}.md"
        accion = "crear"
    extra = {"generado": clave} if clave else {}
    if modulo:
        extra["modulo"] = modulo
    texto = (encabezado(titulo, resumen, TIPOS[tipo][0], etiquetas, extra).replace("---\n", f"---\nid: {ident}\n", 1)
             + "\n" + cuerpo_requisito(ident, titulo, descripcion, evidencias, sin_ejemplos=tipo in ("RF", "RN", "RU", "RT")))
    (res.actualizados if accion == "actualizar" else res.creados).append(rel)
    if res.aplicar:
        ruta = Path(raiz) / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8", newline="\n")
    return ident


def etapa_interfaces(proyecto, raiz, res, refrescar=False):
    rutas = an.rutas_http(proyecto)
    por_archivo = defaultdict(list)
    for r in rutas:
        por_archivo[r["rel"]].append(r)
    for rel, lista in sorted(por_archivo.items()):
        filas = "\n".join(f"| {r['metodo']} | `{r['ruta']}` | {r['manejador']} | `{r['rel']}:{r['linea']}` |" for r in lista)
        descripcion = (f"El sistema expone estas rutas HTTP, definidas en `{rel}` (inferidas del código):\n\n"
                       "| Método | Ruta | Manejador | Evidencia |\n|---|---|---|---|\n" + filas)
        escribir_requisito(raiz, res, "RI", f"Rutas HTTP de {rel}", f"{len(lista)} rutas HTTP que expone {rel}.", descripcion,
                           [f"{lista[0]['rel']}:{lista[0]['linea']}"], f"documentar:ri:rutas:{rel}", ("interfaz", "http"), refrescar=refrescar)
    entorno = an.variables_entorno(proyecto)
    if entorno:
        filas = "\n".join(f"| `{n}` | `{rel}:{linea}` |" for n, (rel, linea) in entorno.items())
        descripcion = ("El sistema lee estas variables de entorno (inferidas del código y de los archivos de ejemplo):\n\n"
                       "| Variable | Evidencia |\n|---|---|\n" + filas)
        primero = next(iter(entorno.values()))
        escribir_requisito(raiz, res, "RI", "Variables de entorno", f"{len(entorno)} variables de entorno que lee el sistema.", descripcion,
                           [f"{primero[0]}:{primero[1]}"], "documentar:ri:entorno", ("interfaz", "configuracion"), refrescar=refrescar)


def etapa_dominio(proyecto, raiz, res, refrescar=False):
    ts = an.tablas(proyecto)
    relacionadas = defaultdict(set)
    for nombre, t in ts.items():
        for col, destino in t["fks"]:
            relacionadas[nombre].add(f"{destino} (por `{col}`)")
            relacionadas[destino].add(f"{nombre} (la referencia desde `{col}`)")
    elegidas = sorted(ts, key=lambda n: (-(len(ts[n]["columnas"]) + 3 * len(relacionadas[n])), n))[:MAX_RD]
    for nombre in sorted(elegidas):
        t = ts[nombre]
        columnas = ", ".join(f"`{c}` ({tipo})" if tipo else f"`{c}`" for c, tipo, _ in t["columnas"][:12])
        descripcion = (f"El código guarda una entidad `{nombre}`. Columnas: {columnas}."
                       + (f" Se relaciona con: {', '.join(sorted(relacionadas[nombre])[:6])}." if relacionadas[nombre] else "")
                       + " Qué significa para el negocio no está confirmado.")
        escribir_requisito(raiz, res, "RD", f"Entidad {nombre}", f"Entidad {nombre} inferida del esquema.", descripcion,
                           [f"{t['rel']}:{t['linea']}"], f"documentar:rd:{nombre}", ("entidad", "inferido"), refrescar=refrescar)
    if len(ts) > MAX_RD:
        res.omitidos.append(f"(se documentaron {MAX_RD} de {len(ts)} entidades; las demás están en el diagrama entidad-relación)")


def etapa_adr(proyecto, raiz, res, refrescar=False):
    for d in an.decisiones_stack(proyecto):
        categoria = d["categoria"]
        clave = f"documentar:adr:{slug(categoria)}"
        usados = ", ".join(c[0] for c in d["componentes"])
        evidencias = [f"{rel}:{n}" for _, rel, n in d["componentes"]]
        previo = buscar_generado(raiz, clave)
        if previo is not None:
            texto_previo = previo.read_text(encoding="utf-8-sig", errors="replace")
            if not (refrescar and re.search(r"(?mi)^\*\*Estado:\*\*\s*provisorio", texto_previo)):
                res.omitidos.append(previo.relative_to(raiz).as_posix())
                continue
            ident, rel, actualizar = previo.stem.split("-", 2)[0] + "-" + previo.stem.split("-", 2)[1], previo.relative_to(raiz).as_posix(), True
        else:
            numero = max(ids_existentes(raiz, "ADR"), res.ultimo.get("ADR", 0)) + 1
            res.ultimo["ADR"] = numero
            ident = f"ADR-{numero:03d}"
            rel, actualizar = f"docs/decisiones/{ident}-{slug(categoria)}.md", False
        titulo = f"Se usa {usados} como {categoria}"
        ev = " ".join(f"`{e}`" for e in evidencias)
        texto = (f"---\nid: {ident}\ntipo: decision\ntitulo: {titulo}\nresumen: Decisión de {categoria} inferida de los manifiestos de dependencias.\n"
                 f"tags: [arquitectura, inferido]\ngenerado: {clave}\n---\n\n# {ident}: {titulo}\n\n"
                 "**Fecha:** desconocida (inferida del código)\n**Estado:** provisorio (inferida del código; el motivo no está confirmado)\n\n"
                 f"## Contexto\n\nNo se conoce por qué se tomó esta decisión. Se infiere de los manifiestos de dependencias. Evidencia: {ev}\n\n"
                 f"## Decisión\n\nEl proyecto usa {usados} como {categoria}.\n\n## Alternativas consideradas\n\nNo documentadas.\n\n"
                 "## Consecuencias\n\nPor confirmar con quien tomó la decisión.\n")
        (res.actualizados if actualizar else res.creados).append(rel)
        if res.aplicar:
            ruta = Path(raiz) / rel
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(texto, encoding="utf-8", newline="\n")


def elegir_reglas(candidatas):
    """Hasta MAX_PREGUNTAS, con a lo sumo 3 por archivo y variedad de tipos."""
    orden = sorted(candidatas, key=lambda c: (-c["puntaje"], c["rel"], c["linea"]))
    por_archivo, elegidas = defaultdict(int), []
    for tipo in ("umbral", "constante", "validación", "permiso", "estados"):
        for c in [c for c in orden if c["tipo"] == tipo][:4]:
            if por_archivo[c["rel"]] < 3 and len(elegidas) < MAX_PREGUNTAS:
                por_archivo[c["rel"]] += 1
                elegidas.append(c)
    return sorted(elegidas, key=lambda c: (c["tipo"], c["rel"], c["linea"]))


PREGUNTAS = {
    "umbral": ("Umbral o condición con un valor fijo", "si el valor o la condición está mal, el cálculo o la decisión sale incorrecto en producción"),
    "constante": ("Constante con significado de negocio", "un valor de negocio escrito en el código se cambia sin avisar y nadie lo revisa"),
    "validación": ("Regla de validación de datos", "define qué datos acepta el sistema; una regla de más o de menos rechaza o deja pasar datos indebidos"),
    "permiso": ("Control de permisos o roles", "decide quién puede hacer qué; un error acá es un problema de seguridad"),
    "estados": ("Estados o tipos posibles", "fija los estados que puede tener algo y, con ellos, qué transiciones tienen sentido"),
}


def etapa_reglas(proyecto, raiz, res, refrescar=False):
    existente = buscar_generado(raiz, "documentar:reglas")
    if existente is not None:
        res.omitidos.append(existente.relative_to(raiz).as_posix())
        return
    elegidas = elegir_reglas(an.reglas_candidatas(proyecto))
    if not elegidas:
        return
    carpeta = Path(raiz) / "docs" / "consultas"
    ronda = max([int(f.name.split("-")[0]) for f in carpeta.glob("*.md") if re.match(r"^\d+-", f.name)] + [0]) + 1 if carpeta.is_dir() else 1
    preguntas = []
    for i, c in enumerate(elegidas, 1):
        titulo, porque = PREGUNTAS[c["tipo"]]
        preguntas.append(
            f"#### P{i}. {titulo} en `{c['rel']}`\n\n**Lo que hace el código:** `{c['rel']}:{c['linea']}` — `{c['texto']}`\n"
            f"**Por qué importa:** {porque}.\n**Opciones:** a) es la regla correcta; b) es incorrecta (indicar cuál es); c) ya no aplica.\n"
            "**Propuesta:** a. Queda como regla provisoria y sin test hasta que se confirme.\n**Respuesta:**\n")
    por_tipo = defaultdict(list)
    for c in elegidas:
        por_tipo[c["tipo"]].append(c)
    resumen = "\n".join(f"- {len(v)} de tipo «{k}»" for k, v in sorted(por_tipo.items()))
    texto = (f"---\ntipo: consulta\nronda: {ronda}\ntema: Reglas de negocio candidatas (inferidas del código)\nestado: abierta\n"
             "generado: documentar:reglas\n---\n\n"
             f"# Consulta {ronda}: Reglas de negocio candidatas (inferidas del código)\n\n"
             "> **Cómo responder.** Escribir debajo de cada pregunta, en **Respuesta:**. Si estás de acuerdo con la **Propuesta**, alcanza con `ok`. "
             "Lo que quede sin responder no bloquea nada: queda como regla provisoria.\n\n"
             "## Lo que entendí hasta ahora\n\nEl código parece aplicar reglas de negocio en estos lugares. **Lo que el código hace hoy no es necesariamente lo "
             f"que debería hacer:** esta consulta sirve para confirmarlo o corregirlo.\n\n{resumen}\n\n"
             "## Supuestos que usaré salvo que se diga lo contrario\n\n- Cada regla se toma tal como está en el código, como provisoria, hasta que la confirmes.\n\n"
             "## Preguntas\n\n### Reglas candidatas\n\n" + "\n".join(preguntas) +
             "\n## Espacio libre\n\n(Reglas que el código no muestra, o que están en otro lado.)\n\n**Respuesta:**\n")
    res.escribir(raiz, f"docs/consultas/{ronda:02d}-reglas-candidatas.md", texto, refrescable=False)


def evidencias_validas(raiz, lista):
    problemas = []
    for e in lista:
        m = RE_EVIDENCIA.fullmatch(e.strip().strip("`"))
        if not m:
            problemas.append(f"«{e}» no tiene la forma archivo:línea")
            continue
        ruta = Path(raiz) / m.group(1)
        if not ruta.is_file():
            problemas.append(f"{m.group(1)} no existe")
            continue
        total = len(ruta.read_text(encoding="utf-8-sig", errors="replace").splitlines())
        if int(m.group(2)) > total or int(m.group(2)) < 1:
            problemas.append(f"{m.group(1)} tiene {total} líneas y se cita la {m.group(2)}")
    return problemas


def cmd_requisito(args):
    raiz = Path(args.raiz).resolve()
    tipo = args.tipo.upper()
    if tipo not in TIPOS or tipo == "RN":
        sys.exit("Tipo no admitido: las reglas de negocio (RN) no se infieren, se confirman por consulta. Usar RF, RD, RI, RNF o RT.")
    if not args.evidencia:
        sys.exit("Falta --evidencia archivo:línea: un requisito inferido sin evidencia es una invención.")
    problemas = evidencias_validas(raiz, args.evidencia)
    if problemas:
        sys.exit("Evidencia inválida: " + "; ".join(problemas))
    descripcion = Path(args.descripcion_archivo).read_text(encoding="utf-8") if args.descripcion_archivo else (args.descripcion or "")
    if not descripcion.strip():
        sys.exit("Falta --descripcion (o --descripcion-archivo): qué hace el sistema, en una o dos oraciones.")
    res = Resultado(True)
    ident = escribir_requisito(raiz, res, tipo, args.titulo, args.resumen or args.titulo, descripcion, args.evidencia, None,
                               ("inferido", args.modulo) if args.modulo else ("inferido",), modulo=args.modulo)
    print(f"Creado {ident} (provisorio): {(res.creados or ['?'])[0]}")


def cmd_secuencia(args):
    raiz = Path(args.raiz).resolve()
    problemas = evidencias_validas(raiz, args.evidencia or [])
    if not args.evidencia or problemas:
        sys.exit("Evidencia inválida o ausente: " + ("; ".join(problemas) or "falta --evidencia archivo:línea"))
    mermaid = Path(args.archivo).read_text(encoding="utf-8")
    if not mermaid.strip().startswith("sequenceDiagram"):
        sys.exit("El diagrama debe empezar con `sequenceDiagram`.")
    ev = ", ".join(f"`{e}`" for e in args.evidencia)
    texto = documento_diagramas("secuencias", args.titulo, f"Diagrama de secuencia inferido: {args.titulo}.",
                                f"Flujo inferido leyendo el código; no está confirmado. Evidencia: {ev}.", [bloque_diagrama(args.titulo, args.pregunta, mermaid)])
    ruta = raiz / "docs" / "diagramas" / f"secuencia-{slug(args.titulo)}.md"
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "senior" / "scripts"))
    try:
        import diagramas as dg
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8", newline="\n")
        _, avisos = dg.analizar(raiz, raiz / "docs")
        propios = [a for a in avisos if ruta.name in a]
        if propios:
            ruta.unlink()
            sys.exit("El diagrama no es legible y no se guardó: " + "; ".join(propios) + ". Dividirlo en dos.")
    except ImportError:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Guardado {ruta.relative_to(raiz).as_posix()} (provisorio).")


def cmd_secuencias(args):
    proyecto = an.Proyecto(args.raiz)
    modulo_de = an.modulos(proyecto)
    candidatos = []
    for r in an.rutas_http(proyecto):
        tamano = len(proyecto.texto(r["rel"]))
        candidatos.append((tamano, f"{r['metodo']} {r['ruta']} → {r['manejador']}", f"{r['rel']}:{r['linea']}", modulo_de.get(r["rel"], "(raíz)")))
    for rel, leng in proyecto.codigo:
        texto = proyecto.texto(rel)
        m = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', texto)
        if m or re.search(r"\bartisan\b|class\s+\w+\s+extends\s+Command\b", texto):
            candidatos.append((len(texto), f"Programa de línea de comandos en {rel}", f"{rel}:{an.linea_de(texto, m.start()) if m else 1}", modulo_de.get(rel, "(raíz)")))
    if not candidatos:
        print("No se detectaron puntos de entrada (rutas HTTP ni programas de consola). Elegir los flujos leyendo el código desde su archivo principal.")
        return
    vistos, unicos = set(), []
    for c in sorted(candidatos, reverse=True):
        if c[1] not in vistos:
            vistos.add(c[1])
            unicos.append(c)
    print("Flujos candidatos para dibujar un diagrama de secuencia (los de código más grande primero):")
    for _, flujo, evidencia, modulo in unicos[:10]:
        print(f"  - {flujo}  [{evidencia}]  (módulo {modulo})")
    print("Elegir los 4 o 5 principales, leer la cadena de llamadas de cada uno y guardar cada diagrama con `documentar.py secuencia`. "
          "Máximo 8 participantes y 20 mensajes por diagrama.")


def cmd_confirmar_diagrama(args):
    ruta = (Path(args.raiz).resolve() / args.diagrama).resolve()
    if not ruta.is_file():
        sys.exit(f"No existe {args.diagrama}.")
    texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
    if not MARCA_RE.search(texto[:900]):
        sys.exit("Ese diagrama no es provisorio (no tiene la marca de generado): no hay nada que confirmar.")
    nuevo = re.sub(r"(?m)^<!--\s*generado por documentar\.py[^\n]*-->\s*$",
                   "<!-- confirmado por el usuario: este diagrama ya no se regenera; se edita a mano -->", texto, count=1)
    nuevo = re.sub(r"(?m)^tags:\s*\[(.*?)\]", lambda m: "tags: [" + ", ".join(x for x in re.split(r",\s*", m.group(1)) if x and x != "inferido") + "]", nuevo, count=1)
    ruta.write_text(nuevo, encoding="utf-8", newline="\n")
    print(f"Confirmado {args.diagrama}: deja de ser provisorio y las copias en el README pierden la nota de «sin confirmar» con `readme_diagramas.py sync`.")


def cmd_progreso(args):
    raiz = Path(args.raiz).resolve()
    proyecto = an.Proyecto(raiz)
    tamano, _ = an.dependencias(proyecto)
    hechos = defaultdict(int)
    base = raiz / "docs" / "requisitos" / "funcional"
    for f in base.glob("*.md") if base.is_dir() else []:
        m = re.search(r"(?m)^modulo:\s*(\S.*)$", f.read_text(encoding="utf-8-sig", errors="replace")[:600])
        if m:
            hechos[m.group(1).strip()] += 1
    secuencias = len(list((raiz / "docs" / "diagramas").glob("secuencia-*.md"))) if (raiz / "docs" / "diagramas").is_dir() else 0
    print("Módulo | archivos | requisitos funcionales (RF) con módulo")
    for m, n in sorted(tamano.items(), key=lambda x: -x[1]):
        print(f"  {m} | {n} | {hechos.get(m, 0)}" + ("  ← sin documentar" if not hechos.get(m, 0) else ""))
    print(f"Diagramas de secuencia: {secuencias}.")


def documentos_inferidos(raiz):
    """[(ruta, texto)] de los documentos de docs/ que salen del código (generados o con origen «Inferido del código»)."""
    out = []
    base = Path(raiz) / "docs"
    for f in sorted(base.rglob("*.md")) if base.is_dir() else []:
        texto = f.read_text(encoding="utf-8-sig", errors="replace")
        if "documentar.py" in texto or "Inferido del código" in texto or "generado:" in texto[:600]:
            out.append((f, texto))
    return out


def revisar_evidencia(raiz):
    """[(documento, problema)] de las citas «Evidencia: archivo:línea» de los documentos inferidos."""
    problemas = []
    for f, texto in documentos_inferidos(raiz):
        for n, linea in enumerate(texto.splitlines(), 1):
            if not re.search(r"(?i)\bevidencia\b", linea):
                continue
            for m in RE_EVIDENCIA.finditer(linea):
                for p in evidencias_validas(raiz, [m.group(0)]):
                    problemas.append((f"{f.relative_to(raiz).as_posix()}:{n}", p))
    return problemas


def cmd_evidencia(args):
    problemas = revisar_evidencia(Path(args.raiz).resolve())
    if not problemas:
        print("Evidencia: todas las citas de los documentos inferidos existen.")
        return
    print(f"Evidencia: {len(problemas)} citas que no se pueden comprobar:")
    for doc, p in problemas[:15]:
        print(f"  {doc} — {p}")
    sys.exit(1)


ETAPAS = {"estructura": etapa_estructura, "interfaces": etapa_interfaces, "dominio": etapa_dominio, "adr": etapa_adr, "reglas": etapa_reglas}


def correr_etapa(nombre, args):
    proyecto = an.Proyecto(args.raiz)
    res = Resultado(args.aplicar)
    raiz = Path(args.raiz).resolve()
    if nombre in ("estructura",):
        ETAPAS[nombre](proyecto, raiz, res)
    else:
        ETAPAS[nombre](proyecto, raiz, res, getattr(args, "refrescar", False))
    return res


def cmd_etapa(args):
    nombres = list(ETAPAS) if args.orden == "todo" else [args.orden]
    if not Path(args.raiz).resolve().joinpath("docs").is_dir() and args.aplicar:
        print("Aviso: no existe docs/; se crea la carpeta de lo generado. Conviene adoptar el proyecto antes (/adoptar-proyecto).")
    for n in nombres:
        res = correr_etapa(n, args)
        print(f"[{n}]")
        for l in res.informe(n):
            print("  " + l)
    if args.aplicar:
        print("Todo lo generado es provisorio y cita su evidencia. Siguiente: `documentar.py evidencia` y, para el detalle de los requisitos funcionales "
              "y las secuencias, `documentar.py plan`.")


def cmd_plan(args):
    proyecto = an.Proyecto(args.raiz)
    raiz = Path(args.raiz).resolve()
    leng = proyecto.lenguajes()
    print("Proyecto: " + (", ".join(f"{k} {v} archivos" for k, v in leng.most_common()) or "sin código de PHP, JavaScript, TypeScript ni Python"))
    if not leng:
        print("No hay nada que analizar con este paquete de lenguajes: el resto de la documentación se hace a mano (senior-relevar).")
        return
    tamano, aristas = an.dependencias(proyecto)
    ts, rutas, entorno, stack, reglas = an.tablas(proyecto), an.rutas_http(proyecto), an.variables_entorno(proyecto), an.decisiones_stack(proyecto), an.reglas_candidatas(proyecto)
    clases = sum(len(v) for v in an.clases(proyecto).values())
    print(f"Se detectó: {len(tamano)} módulos, {clases} clases, {len(ts)} tablas, {len(rutas)} rutas HTTP, {len(entorno)} variables de entorno, "
          f"{len(stack)} decisiones de stack y {len(reglas)} reglas candidatas.")
    print("\nEtapas por script (sin tokens; con --aplicar escriben, sin --aplicar solo muestran):")  # senior-ignore: SEC-LOG-SENSIBLE (cantidad de tokens de texto, no una credencial)
    print(f"  estructura  diagramas de módulos, de clases por módulo y entidad-relación ({len(tamano)} módulos, {len(ts)} tablas)")
    print(f"  interfaces  requisitos de interfaz (RI): {len(set(r['rel'] for r in rutas))} archivos de rutas" + (" y variables de entorno" if entorno else ""))
    print(f"  dominio     requisitos de dominio (RD): hasta {min(len(ts), MAX_RD)} entidades")
    print(f"  adr         decisiones de arquitectura (ADR): {len(stack)}")
    print(f"  reglas      una consulta con hasta {min(len(reglas), MAX_PREGUNTAS)} reglas de negocio candidatas para que confirmes")
    caracteres = sum(len(proyecto.texto(r)) for r, _ in proyecto.codigo)
    por_modulo = defaultdict(int)
    modulo_de = an.modulos(proyecto)
    for r, _ in proyecto.codigo:
        por_modulo[modulo_de.get(r, "(raíz)")] += len(proyecto.texto(r))
    print("\nEtapas con lectura del modelo (cuestan tokens; se hacen por módulo, con tu aprobación antes de cada una):")  # senior-ignore: SEC-LOG-SENSIBLE (cantidad de tokens de texto, no una credencial)
    print(f"  requisitos  requisitos funcionales (RF) por módulo, con evidencia: ~{caracteres // 4 + 1500 * len(tamano)} tokens en total (±50 %)")  # senior-ignore: SEC-LOG-SENSIBLE (cantidad de tokens de texto, no una credencial)
    for m, c in sorted(por_modulo.items(), key=lambda x: -x[1])[:8]:
        print(f"    {m}: ~{c // 4 + 1500} tokens")  # senior-ignore: SEC-LOG-SENSIBLE (cantidad de tokens de texto, no una credencial)
    print("  secuencias  diagramas de secuencia de los 4 o 5 flujos principales: ~8.000 tokens cada uno (`documentar.py secuencias` los lista)")  # senior-ignore: SEC-LOG-SENSIBLE (cantidad de tokens de texto, no una credencial)
    existentes = sum(1 for _ in (raiz / "docs" / "requisitos").rglob("*.md")) if (raiz / "docs" / "requisitos").is_dir() else 0
    print(f"\nYa hay {existentes} requisitos en docs/requisitos/. Lo generado nunca pisa lo que está confirmado o editado a mano.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)

    def con_raiz(p):
        p.add_argument("--raiz", default=".")
        return p
    for nombre in ("estructura", "interfaces", "dominio", "adr", "reglas", "todo"):
        p = con_raiz(sub.add_parser(nombre))
        p.add_argument("--aplicar", action="store_true")
        p.add_argument("--refrescar", action="store_true")
    for nombre in ("plan", "secuencias", "progreso", "evidencia"):
        con_raiz(sub.add_parser(nombre))
    cd = con_raiz(sub.add_parser("confirmar-diagrama"))
    cd.add_argument("diagrama")
    r = con_raiz(sub.add_parser("requisito"))
    r.add_argument("--tipo", required=True)
    r.add_argument("--titulo", required=True)
    r.add_argument("--resumen", default="")
    r.add_argument("--modulo", default="")
    r.add_argument("--evidencia", action="append")
    r.add_argument("--descripcion", default="")
    r.add_argument("--descripcion-archivo", default="")
    s = con_raiz(sub.add_parser("secuencia"))
    s.add_argument("--titulo", required=True)
    s.add_argument("--pregunta", required=True)
    s.add_argument("--archivo", required=True)
    s.add_argument("--evidencia", action="append")
    args = ap.parse_args()
    if args.orden in ETAPAS or args.orden == "todo":
        cmd_etapa(args)
    else:
        {"plan": cmd_plan, "secuencias": cmd_secuencias, "progreso": cmd_progreso, "evidencia": cmd_evidencia, "confirmar-diagrama": cmd_confirmar_diagrama,
         "requisito": cmd_requisito, "secuencia": cmd_secuencia}[args.orden](args)


if __name__ == "__main__":
    main()
