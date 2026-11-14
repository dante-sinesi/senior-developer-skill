#!/usr/bin/env python3
"""Prepara una ronda de diseño: tres esqueletos HTML (sin estilo) y los documentos de trabajo.

Uso (ronda nueva):
    python crear_bosquejos.py --nombre <proyecto> [--raiz .] [--tipo sitio|app] [--fecha AAAA-MM-DD] [--completo] [--modos desktop,mobile]
Uso (evolucionar o corregir la dirección elegida):
    python crear_bosquejos.py --evolucionar docs/diseno/rondas/<ronda>/direccion-b.html
        Copia la dirección a direccion-b-v2.html (luego -v3…) para trabajar sobre ella sin perder la anterior.

Por defecto la ronda es LIVIANA (trabajos chicos) y crea, solo dentro de <raiz>/docs/diseno/ y sin pisar nada:
  docs/diseno/rondas/AAAA-MM-DD-<proyecto>/   NOTAS.md (una hoja) y direccion-a.html, direccion-b.html, direccion-c.html
Con --completo (proyectos medianos o grandes) agrega además:
  docs/diseno/notas/preferencias.md, notas/decisiones.md, sistema/tokens.css,
  sistema/inventario-componentes.md, campos/, auditoria/, y en la ronda briefing.md, inventario-campos.md, comparar.html
Además deja ver.html: el visor para mirar todas las propuestas de la ronda juntas, en desktop, mobile o ambas (--modos mobile si la app
no tiene versión desktop, o al revés; `ver_propuestas.py crear <ronda>` lo regenera cuando se suman archivos).
Cada direccion-*.html es un esqueleto único, sin dependencias y SIN estilo: el aspecto lo decide el diseñador.
Trae solo la barra para ver el diseño en desktop, mobile o ambas. Solo biblioteca estándar.
"""
import argparse
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ver_propuestas  # noqa: E402 motivo: sys.path se ajusta justo antes de importarlo

PLANTILLAS = Path(__file__).resolve().parents[1] / "plantillas"


def leer(nombre):
    return (PLANTILLAS / nombre).read_text(encoding="utf-8")


def rellenar(texto, valores):
    for k, v in valores.items():
        texto = texto.replace("{{" + k + "}}", v)
    return texto


def con_visor(contenido, titulo):
    """Inserta la barra de vistas (visor.css y visor.js) en un bosquejo de plantilla."""
    estilo = "<style data-herramienta>" + chr(10) + leer("visor.css") + "</style>"
    script = "<script data-herramienta>" + chr(10) + rellenar(leer("visor.js"), {"titulo_visor": titulo}) + "</script>"
    return contenido.replace("{{visor_estilo}}", estilo).replace("{{visor_script}}", script)


def escribir_si_falta(ruta, contenido, creados):
    if ruta.exists():
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    creados.append(ruta)


def evolucionar(args):
    base = Path(args.evolucionar).resolve()
    if not base.is_file():
        sys.exit(f"No existe el archivo: {args.evolucionar}")
    m = re.match(r"(.+?)(?:-v(\d+))?$", base.stem)
    nombre, n = m.group(1), int(m.group(2) or 1)
    while (base.parent / f"{nombre}-v{n + 1}{base.suffix}").exists():
        n += 1
    destino = base.parent / f"{nombre}-v{n + 1}{base.suffix}"
    shutil.copyfile(base, destino)
    print(f"Creado: {destino.name} (copia de {base.name}). Trabajar sobre la nueva versión.")


def iniciar_diseno(diseno, valores, creados):
    escribir_si_falta(diseno / "notas" / "preferencias.md", leer("preferencias.md"), creados)
    escribir_si_falta(diseno / "notas" / "decisiones.md",
                      "# Decisiones de diseño\n\nUna línea por decisión, con su ID (D-001) y el motivo. "
                      "Los ADR de senior-docs las citan por ID.\n", creados)
    escribir_si_falta(diseno / "sistema" / "tokens.css", leer("tokens.css"), creados)
    escribir_si_falta(diseno / "sistema" / "inventario-componentes.md", leer("inventario-componentes.md"), creados)
    for carpeta in ("campos", "auditoria"):
        escribir_si_falta(diseno / carpeta / ".gitkeep", "", creados)


def slug(texto):
    sin_acentos = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower()).strip("-")
    return s or "proyecto"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre", default="")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--tipo", choices=["sitio", "app"], default="sitio")
    ap.add_argument("--fecha", default=date.today().isoformat())
    ap.add_argument("--modos", default="desktop,mobile", help="modos que tiene la app: desktop,mobile (por defecto), desktop o mobile")
    ap.add_argument("--completo", action="store_true", help="crea también los documentos de un proyecto mediano o grande")
    ap.add_argument("--evolucionar", help="copia la dirección elegida a una versión nueva (-v2, -v3…)")
    args = ap.parse_args()
    if args.evolucionar:
        return evolucionar(args)
    if not args.nombre:
        sys.exit("Falta --nombre <proyecto> (o --evolucionar <archivo>).")
    raiz = Path(args.raiz).resolve()
    diseno = raiz / "docs" / "diseno"
    ronda = diseno / "rondas" / f"{args.fecha}-{slug(args.nombre)}"
    valores = {"proyecto": args.nombre, "fecha": args.fecha, "tipo": args.tipo, "formulario": "(nombre del formulario)"}
    creados = []
    if args.completo:
        iniciar_diseno(diseno, valores, creados)
        escribir_si_falta(ronda / "briefing.md", rellenar(leer("briefing.md"), valores), creados)
        escribir_si_falta(ronda / "inventario-campos.md", rellenar(leer("inventario-campos.md"), valores), creados)
    else:
        escribir_si_falta(ronda / "NOTAS.md", rellenar(leer("notas-ronda.md"), valores), creados)
    con_estilo = (diseno / "estilo" / "tarjeta.html").exists() or (diseno / "estilo" / "tarjeta.md").exists()
    for letra in "abc":
        contenido = con_visor(rellenar(leer("bosquejo.html"), {**valores, "letra": letra.upper()}),
                              f"Dirección {letra.upper()}")
        if con_estilo:  # el estilo ya está decidido: las tres alternativas difieren solo en estructura
            contenido = contenido.replace("</head>", '<link rel="stylesheet" href="../../sistema/tokens.css">\n'
                                          '<!-- El estilo del proyecto ya está definido (docs/diseno/estilo/): usar las variables de '
                                          'sistema/tokens.css y las piezas de la tarjeta. Esta dirección solo cambia la estructura. -->\n</head>', 1)
        escribir_si_falta(ronda / f"direccion-{letra}.html", contenido, creados)
    if not (ronda / "ver.html").exists():
        try:
            ver_propuestas.crear(ronda, f"{args.nombre}: direcciones", ver_propuestas.leer_modos(args.modos))
            creados.append(ronda / "ver.html")
        except ver_propuestas.VisorError as e:
            sys.exit(f"Error: {e}")
    if args.completo:
        escribir_si_falta(ronda / "comparar.html", rellenar(leer("comparar.html"), valores), creados)
    print(f"Ronda lista en {ronda.relative_to(raiz).as_posix()}/ ({len(creados)} archivos creados; lo existente no se tocó).")
    if con_estilo:
        print("Hay una tarjeta de estilo: las tres direcciones usan sus variables y difieren solo en estructura.")
    print("Para mirar todas las propuestas juntas (desktop, mobile o ambas): python <senior>/scripts/abrir_en_navegador.py "
          f"{(ronda / 'ver.html').relative_to(raiz).as_posix()}")
    print("Siguiente paso: completar las notas/briefing con el usuario y diseñar tres direcciones que difieran en estructura. "
          "El aspecto (estilo, arte) lo decide el diseñador; las reglas objetivas las controla revisar_diseno.py.")


if __name__ == "__main__":
    main()
