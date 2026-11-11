#!/usr/bin/env python3
"""Auditoría de diseño de un proyecto que no usó la skill desde el principio.

Uso:
    python auditar_proyecto.py [--raiz .] [--tipo sitio|app] [--max 8] [--sin-informe]

Busca los archivos de interfaz del proyecto (HTML, CSS y, de forma aproximada, plantillas PHP, Vue,
Svelte, JSX y TSX), aplica los chequeos de revisar_diseno.py y escribe un informe en
docs/diseno/auditoria/AAAA-MM-DD.md con los hallazgos y propuestas ordenadas por impacto y esfuerzo.
NO modifica nada del proyecto: solo escribe en docs/diseno/auditoria/. Se ignoran docs/diseno/, docs/,
node_modules, vendor, dist y build.
Solo biblioteca estándar.
"""
import argparse
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revisar_diseno  # noqa: E402

IGNORAR = {"diseno", "docs", "node_modules", "vendor", "dist", "build", ".git"}
PROPUESTAS = [
    ("etiquetas", "Etiquetas de formulario", "alto", "bajo",
     "Dar a cada campo una etiqueta visible, única y específica; quitar placeholders como etiqueta; agrupar opciones con título."),
    ("contraste", "Contraste de color", "alto", "bajo",
     "Ajustar los pares de color que no llegan a 4,5:1 (texto) o 3:1 (texto grande y componentes)."),
    ("saturacion", "Saturación del usuario", "alto", "medio",
     "Reducir campos visibles (pasos cortos y opciones avanzadas), dejar una sola acción principal y recortar navegación y texto."),
    ("interaccion", "Reactividad y foco", "medio", "bajo",
     "Agregar estados hover, foco visible y presionado con transiciones breves; respetar prefers-reduced-motion."),
    ("tipografia", "Tipografía (una familia ideal, dos como máximo)", "medio", "bajo",
     "Reducir a una o dos familias tipográficas para toda la web (más solo si el arte lo requiere, con excepción escrita)."),
    ("base", "Base técnica y contenido", "medio", "bajo",
     "Agregar viewport y reglas responsivas, completar marcadores y reemplazar frases genéricas por contenido concreto."),
    ("sistema", "Sistema de diseño", "alto a largo plazo", "alto",
     "Centralizar colores, tipografías y espacios en variables y unificar los componentes duplicados."),
]


def archivos_interfaz(raiz):
    res = []
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or set(f.relative_to(raiz).parts) & IGNORAR:
            continue
        if f.suffix.lower() in revisar_diseno.EXT_DOC or f.suffix.lower() in revisar_diseno.EXT_CSS:
            res.append(f)
    return res


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--tipo", choices=["sitio", "app"], default="sitio")
    ap.add_argument("--max", type=int, default=8, help="hallazgos listados por chequeo")
    ap.add_argument("--sin-informe", action="store_true", help="solo mostrar el resumen, sin escribir el informe")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    archivos = archivos_interfaz(raiz)
    if not archivos:
        print("Auditoría: no se encontraron archivos de interfaz (HTML, CSS, PHP, Vue, JSX…).")
        return
    hallazgos = revisar_diseno.analizar([str(f) for f in archivos], None, args.tipo, incluir_css=True)
    por_chequeo = defaultdict(list)
    for h in hallazgos:
        por_chequeo[h["chequeo"]].append(h)
    lineas = [f"# Auditoría de diseño: {raiz.name}", "",
              f"**Fecha:** {date.today().isoformat()} · **Archivos revisados:** {len(archivos)} · **Tipo:** {args.tipo}", "",
              "Informe generado por `auditar_proyecto.py`. Heurístico: marca qué mirar, no dicta el diseño. "
              "No se modificó nada del proyecto.", "", "## Resumen", "",
              "| Chequeo | Fallas | Avisos |", "|---|---|---|"]
    for clave, _, _, _, _ in PROPUESTAS:
        h = por_chequeo.get(clave, [])
        lineas.append(f"| {clave} | {sum(x['sev'] == 'FALLA' for x in h)} | {sum(x['sev'] == 'AVISO' for x in h)} |")
    lineas += ["", "## Hallazgos principales", ""]
    for clave, titulo, _, _, _ in PROPUESTAS:
        h = sorted(por_chequeo.get(clave, []), key=lambda x: x["sev"] != "FALLA")
        if not h:
            continue
        lineas.append(f"### {titulo}")
        for x in h[:args.max]:
            rel = Path(x["archivo"]).resolve().relative_to(raiz).as_posix()
            lineas.append(f"- {x['sev']} `{rel}:{x['linea']}` — {x['msg']}")
        if len(h) > args.max:
            lineas.append(f"- … y {len(h) - args.max} más.")
        lineas.append("")
    lineas += ["## Propuestas, ordenadas por impacto y esfuerzo", ""]
    n = 0
    for clave, titulo, impacto, esfuerzo, texto in PROPUESTAS:
        if por_chequeo.get(clave):
            n += 1
            lineas.append(f"{n}. **{titulo}** (impacto {impacto}, esfuerzo {esfuerzo}): {texto}")
    if n == 0:
        lineas.append("Sin propuestas: los chequeos automáticos no encontraron nada.")
    lineas += ["", "## Para que no se repita", "",
               "Las reglas de diseño pueden quedar escritas como requisitos no funcionales provisorios del proyecto: "
               "`python <senior-diseno>/scripts/paquete_interfaz.py` muestra qué crearía y, con `--aplicar`, los escribe; "
               "el usuario decide cuáles acepta."]
    lineas += ["", "## Límites", "",
               "- Las plantillas PHP, Vue y JSX se leen de forma aproximada; si el proyecto corre, conviene revisar también la página renderizada.",
               "- Lo subjetivo (identidad, tono, jerarquía) no lo mide un script: se conversa con el usuario antes de convertir propuestas en bosquejos."]
    resumen = ", ".join(f"{k}: {len(v)}" for k, v in por_chequeo.items()) or "sin hallazgos"
    if args.sin_informe:
        print(f"Auditoría ({len(archivos)} archivos): {resumen}.")
        return
    destino = raiz / "docs" / "diseno" / "auditoria" / f"{date.today().isoformat()}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    print(f"Auditoría ({len(archivos)} archivos): {resumen}.")
    print(f"Informe escrito en {destino.relative_to(raiz).as_posix()} (el proyecto no se modificó).")


if __name__ == "__main__":
    main()
