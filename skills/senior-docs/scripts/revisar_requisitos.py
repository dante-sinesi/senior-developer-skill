#!/usr/bin/env python3
"""Revisa la calidad del texto de los requisitos de docs/requisitos/ sin gastar tokens.

Uso:
    python revisar_requisitos.py [--raiz .] [--max 30] [--json]

Qué revisa (solo la forma; no juzga si el requisito es correcto o completo para el negocio):
  FALLA   frontmatter incompleto (id, tipo, titulo, resumen); id con formato inválido, repetido o distinto del
          nombre del archivo; prefijo que no corresponde al tipo; enlaces [[ID]] a requisitos que no existen;
          requisitos de negocio, usuario, funcional y transición sin ejemplos verificables.
  AVISO   palabras ambiguas («rápido», «fácil», «adecuado», «etc.»…), «debería» en lugar de «debe», varias
          obligaciones en un mismo requisito, requisitos no funcionales sin cifras, estado ausente o desconocido,
          origen vacío en requisitos vigentes, carpeta que no coincide con el tipo y plantilla sin completar.
No revisa la trazabilidad requisito-test (eso lo hace `verificar.py docs`) ni detecta contradicciones entre
requisitos: eso se decide con el usuario. Código de salida: 0 sin FALLA, 1 con FALLA. Solo lectura.
Solo biblioteca estándar.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

TIPOS = {  # tipo normalizado -> (prefijo, carpeta)
    "negocio": ("RN", "negocio"), "usuario": ("RU", "usuario"), "dominio": ("RD", "dominio"),
    "funcional": ("RF", "funcional"), "no-funcional": ("RNF", "no-funcional"),
    "transicion": ("RT", "transicion"), "interfaces": ("RI", "interfaces"),
}
ALIAS_TIPO = {"nofuncional": "no-funcional", "no funcional": "no-funcional", "no_funcional": "no-funcional",
              "interfaz": "interfaces", "interfaces-externas": "interfaces", "interfaces externas": "interfaces",
              "interfaz-externa": "interfaces"}
REQUIEREN_EJEMPLOS = {"negocio", "usuario", "funcional", "transicion"}
RE_ID = re.compile(r"^(RN|RU|RD|RF|RNF|RT|RI)-(\d{3,})$")
RE_ENLACE = re.compile(r"\[\[((?:RN|RU|RD|RF|RNF|RT|RI)-\d+)(?:\|[^\]]*)?\]\]", re.IGNORECASE)
AMBIGUAS = [
    r"r[aá]pid[oa]s?", r"r[aá]pidamente", r"f[aá]cil(?:es|mente)?", r"sencill[oa]s?", r"intuitiv[oa]s?",
    r"amigable[s]?", r"adecuad[oa]s?", r"apropiad[oa]s?", r"flexible[s]?", r"robust[oa]s?", r"eficiente[s]?",
    r"[oó]ptim[oa]s?", r"suficiente[s]?", r"razonable[s]?", r"normalmente", r"generalmente", r"habitualmente",
    r"a veces", r"etc\.?", r"etc[eé]tera", r"y/o", r"seg[uú]n corresponda", r"si es posible", r"cuando sea necesario",
    r"en lo posible", r"lo antes posible", r"moderno[s]?", r"potente[s]?", r"cualquier momento",
]
RE_AMBIGUA = re.compile(r"(?<![\w])(" + "|".join(AMBIGUAS) + r")(?![\w])", re.IGNORECASE)
RE_DEBERIA = re.compile(r"(?<![\w])(deber[ií]a(?:n)?|podr[ií]a(?:n)?|quiz[aá]s?|tal vez|idealmente)(?![\w])", re.IGNORECASE)
RE_DEBE = re.compile(r"(?<![\w])debe(?:n)?(?![\w])", re.IGNORECASE)
PLANTILLAS = ["Título corto del requisito", "(Una regla, una idea", "(Quién lo definió", "(caso normal)", "(caso límite)",
              "(caso inválido)", "(resultado)"]
ESTADOS_VALIDOS = re.compile(r"^(vigente|provisorio|reemplazado por\s+(?:RN|RU|RD|RF|RNF|RT|RI)-\d+)\b", re.IGNORECASE)


def sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_tipo(valor):
    v = sin_acentos(valor.strip().lower())
    return ALIAS_TIPO.get(v, v)


class Req:
    def __init__(self, ruta, raiz):
        self.ruta = ruta
        self.rel = ruta.relative_to(raiz).as_posix()
        texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
        self.lineas = texto.splitlines()
        self.linea_campo = {}
        self.meta, self.inicio_cuerpo = self._frontmatter()
        self.secciones = self._secciones()

    def _frontmatter(self):
        if not self.lineas or self.lineas[0].strip() != "---":
            return None, 0
        meta = {}
        for i, linea in enumerate(self.lineas[1:], start=1):
            if linea.strip() == "---":
                return meta, i + 1
            m = re.match(r"^([\w-]+)\s*:\s*(.*)$", linea)
            if m:
                meta[m.group(1).lower()] = m.group(2).strip()
                self.linea_campo[m.group(1).lower()] = i + 1
        return None, 0

    def _secciones(self):
        secciones, actual, buffer, en_codigo = {}, "_inicio", [], False
        inicios = {"_inicio": self.inicio_cuerpo + 1}
        for n, linea in enumerate(self.lineas[self.inicio_cuerpo:], start=self.inicio_cuerpo + 1):
            if linea.strip().startswith("```"):
                en_codigo = not en_codigo
                continue
            if en_codigo:
                continue
            m = re.match(r"^##\s+(.*)$", linea)
            if m:
                secciones[actual] = (inicios[actual], buffer)
                actual = sin_acentos(m.group(1).strip().lower())
                inicios[actual] = n
                buffer = []
            else:
                buffer.append((n, linea))
        secciones[actual] = (inicios[actual], buffer)
        return secciones

    def seccion(self, *nombres):
        for nombre, (inicio, lineas) in self.secciones.items():
            if any(nombre.startswith(n) for n in nombres):
                return inicio, lineas
        return None, []

    def texto_prosa(self):
        """Título, resumen y secciones de redacción (sin código, sin tablas de ejemplos)."""
        res = []
        for campo in ("titulo", "resumen"):
            if self.meta and self.meta.get(campo):
                res.append((self.linea_campo.get(campo, 1), self.meta[campo]))
        for nombre in ("descripcion", "_inicio"):
            _, lineas = self.seccion(nombre)
            res.extend((n, l) for n, l in lineas if not l.strip().startswith("|") and not l.strip().startswith("#"))
        return res


def hallazgo(sev, req, linea, msg):
    return {"sev": sev, "archivo": req.rel, "linea": linea, "msg": msg}


def filas_de_datos(lineas):
    """Filas de tablas Markdown que no son encabezado ni separador ni marcador de plantilla."""
    filas, encabezado = [], True
    for _, l in lineas:
        s = l.strip()
        if not s.startswith("|"):
            encabezado = True
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in celdas):
            continue
        if encabezado:
            encabezado = False
            continue
        if any(c and not (c.startswith("(") and c.endswith(")")) for c in celdas):
            filas.append(celdas)
    return filas


def tiene_ejemplos(req):
    inicio, lineas = req.seccion("ejemplos")
    if inicio is None:
        return False, None
    if filas_de_datos(lineas):
        return True, inicio
    cuerpo = " ".join(l for _, l in lineas).lower()
    if "dado" in cuerpo and "cuando" in cuerpo and "entonces" in cuerpo:
        return True, inicio
    return False, inicio


def revisar(raiz):
    carpeta = raiz / "docs" / "requisitos"
    archivos = sorted(f for f in carpeta.rglob("*.md")
                      if f.name.lower() not in {"readme.md", "indice.md"} and not f.name.startswith("_")) if carpeta.is_dir() else []
    reqs, hallazgos, vistos = [], [], {}
    for f in archivos:
        r = Req(f, raiz)
        if r.meta is not None and r.meta.get("id", "").upper().endswith("-000"):
            continue  # es la plantilla, no un requisito
        reqs.append(r)
    ids = {r.meta["id"].upper() for r in reqs if r.meta and r.meta.get("id")}
    provisorios = 0
    for r in reqs:
        if r.meta is None:
            hallazgos.append(hallazgo("FALLA", r, 1, "sin encabezado (frontmatter) con id, tipo, titulo y resumen"))
            continue
        faltan = [c for c in ("id", "tipo", "titulo", "resumen") if not r.meta.get(c)]
        if faltan:
            hallazgos.append(hallazgo("FALLA", r, 1, "faltan campos del encabezado: " + ", ".join(faltan)))
        rid = r.meta.get("id", "").upper()
        tipo = normalizar_tipo(r.meta.get("tipo", ""))
        if rid:
            if not RE_ID.match(rid):
                hallazgos.append(hallazgo("FALLA", r, 2, f"id «{rid}» inválido: usar RN-001, RF-010, RNF-004…"))
            else:
                if r.ruta.stem.upper() != rid:
                    hallazgos.append(hallazgo("FALLA", r, 2, f"el id {rid} no coincide con el nombre del archivo ({r.ruta.name})"))
                if tipo in TIPOS and TIPOS[tipo][0] != RE_ID.match(rid).group(1):
                    hallazgos.append(hallazgo("FALLA", r, 2, f"el prefijo de {rid} no corresponde al tipo «{tipo}» (debería ser {TIPOS[tipo][0]})"))
            if rid in vistos:
                hallazgos.append(hallazgo("FALLA", r, 2, f"id {rid} repetido (también en {vistos[rid]})"))
            vistos.setdefault(rid, r.rel)
        if r.meta.get("tipo") and tipo not in TIPOS:
            hallazgos.append(hallazgo("FALLA", r, 3, f"tipo «{r.meta['tipo']}» desconocido: negocio, usuario, dominio, funcional, no-funcional, transicion o interfaces"))
        elif tipo in TIPOS and r.ruta.parent.name in {c for _, c in TIPOS.values()} and r.ruta.parent.name != TIPOS[tipo][1]:
            hallazgos.append(hallazgo("AVISO", r, 3, f"está en la carpeta «{r.ruta.parent.name}» pero su tipo es «{tipo}»"))
        for n, linea in enumerate(r.lineas, start=1):
            for m in RE_ENLACE.finditer(linea):
                destino = m.group(1).upper()
                if not destino.endswith("-000") and destino not in ids:
                    hallazgos.append(hallazgo("FALLA", r, n, f"enlace [[{destino}]] a un requisito que no existe"))
        _, lineas_estado = r.seccion("estado")
        es_hipotesis = next((l.strip() for _, l in lineas_estado if l.strip()), "").lower().startswith("provisorio")
        if tipo in REQUIEREN_EJEMPLOS and not es_hipotesis:  # una hipótesis todavía no tiene ejemplos verificables
            ok, inicio = tiene_ejemplos(r)
            if not ok:
                hallazgos.append(hallazgo("FALLA", r, inicio or 1, "sin ejemplos verificables: agregar una tabla entrada → resultado con valores concretos"))
        prosa = r.texto_prosa()
        for n, linea in prosa:
            amb = sorted({m.group(1).lower() for m in RE_AMBIGUA.finditer(linea)})
            if amb:
                hallazgos.append(hallazgo("AVISO", r, n, "palabras ambiguas (" + ", ".join(amb[:3]) + "): reemplazar por un valor, un caso o quitarlas"))
            dev = sorted({m.group(1).lower() for m in RE_DEBERIA.finditer(linea)})
            if dev:
                hallazgos.append(hallazgo("AVISO", r, n, "«" + dev[0] + "»: un requisito se escribe con «debe»; si no es seguro, es una hipótesis (estado provisorio)"))
        inicio_desc, lineas_desc = r.seccion("descripcion")
        cuerpo_desc = " ".join(l for _, l in lineas_desc)
        if len(RE_DEBE.findall(cuerpo_desc)) >= 3:
            hallazgos.append(hallazgo("AVISO", r, inicio_desc or 1, "varias obligaciones en un mismo requisito («debe» 3 veces o más): separarlo en uno por idea"))
        if tipo == "no-funcional":
            _, lineas_ej = r.seccion("ejemplos")
            fuente = cuerpo_desc + " " + " ".join(l for _, l in lineas_ej) + " " + r.meta.get("resumen", "")
            if not re.search(r"\d", fuente):
                hallazgos.append(hallazgo("AVISO", r, inicio_desc or 1, "requisito no funcional sin ninguna cifra: no es medible (agregar un valor y una unidad)"))
        if len(r.meta.get("titulo", "")) > 90:
            hallazgos.append(hallazgo("AVISO", r, 1, "título de más de 90 caracteres: acortarlo"))
        inicio_est, lineas_est = r.seccion("estado")
        estado = next((l.strip() for _, l in lineas_est if l.strip()), "")
        if inicio_est is None or not estado:
            hallazgos.append(hallazgo("AVISO", r, 1, "sin sección Estado (vigente, provisorio o reemplazado por ID)"))
        elif not ESTADOS_VALIDOS.match(estado):
            hallazgos.append(hallazgo("AVISO", r, inicio_est, f"estado «{estado[:30]}» desconocido: vigente, provisorio o reemplazado por ID"))
        elif estado.lower().startswith("reemplazado"):
            destino = re.search(r"((?:RN|RU|RD|RF|RNF|RT|RI)-\d+)", estado, re.IGNORECASE)
            if destino and destino.group(1).upper() not in ids:
                hallazgos.append(hallazgo("FALLA", r, inicio_est, f"reemplazado por {destino.group(1).upper()}, que no existe"))
        elif estado.lower().startswith("provisorio"):
            provisorios += 1
        elif estado.lower().startswith("vigente"):
            _, lineas_or = r.seccion("origen")
            origen = " ".join(l.strip() for _, l in lineas_or if l.strip())
            if not origen or origen.startswith("(Quién"):
                hallazgos.append(hallazgo("AVISO", r, 1, "vigente pero sin Origen: anotar quién lo definió o dónde está definido"))
        if any(p.lower() in "\n".join(r.lineas).lower() for p in PLANTILLAS):
            hallazgos.append(hallazgo("AVISO", r, 1, "quedan partes de la plantilla sin completar"))
    return len(reqs), provisorios, hallazgos


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    total, provisorios, hallazgos = revisar(raiz)
    if args.json:
        print(json.dumps({"revisados": total, "provisorios": provisorios, "hallazgos": hallazgos}, ensure_ascii=False, indent=1))
    elif not (raiz / "docs" / "requisitos").is_dir():
        print("Requisitos: no existe docs/requisitos/ (se omite).")
    else:
        fallas = sum(h["sev"] == "FALLA" for h in hallazgos)
        avisos = len(hallazgos) - fallas
        extra = f", {provisorios} provisorios esperan confirmación" if provisorios else ""
        print(f"Requisitos: {total} revisados, {fallas} fallas, {avisos} avisos{extra}.")
        orden = {"FALLA": 0, "AVISO": 1}
        for h in sorted(hallazgos, key=lambda x: (orden[x["sev"]], x["archivo"], x["linea"]))[:args.max]:
            print(f"  {h['sev']:5} {h['archivo']}:{h['linea']} — {h['msg']}")
        if len(hallazgos) > args.max:
            print(f"  … y {len(hallazgos) - args.max} más (usar --max o --json).")
    sys.exit(1 if any(h["sev"] == "FALLA" for h in hallazgos) else 0)


if __name__ == "__main__":
    main()
