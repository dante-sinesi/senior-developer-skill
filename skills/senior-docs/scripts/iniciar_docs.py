#!/usr/bin/env python3
"""Crea la estructura base de documentación (docs/) de un proyecto.

Uso:
    python iniciar_docs.py [--raiz .] [--docs docs]

Crea, sin pisar nada que ya exista:
  docs/README.md, docs/ESTADO.md, docs/pendientes.md, docs/deuda-tecnica.md
  docs/cambios/, docs/decisiones/, docs/diagramas/
  docs/requisitos/{negocio,usuario,dominio,funcional,no-funcional,transicion,interfaces}/
Usa las plantillas de senior-memoria/plantillas cuando están disponibles.
Al final regenera el índice. Solo biblioteca estándar.
"""
import argparse
import subprocess
import sys
from pathlib import Path

TIPOS = ["negocio", "usuario", "dominio", "funcional", "no-funcional", "transicion", "interfaces"]
PLANTILLAS = ["ESTADO.md", "pendientes.md", "deuda-tecnica.md"]
README = """# Documentación del proyecto

Documentación viva: se actualiza con cada cambio y se indexa automáticamente.

- Estado actual: [ESTADO](ESTADO.md)
- Índice y trazabilidad: [INDEX](INDEX.md)
- Pendientes: [pendientes](pendientes.md) · Deuda técnica: [deuda técnica](deuda-tecnica.md)

## Carpetas

- `requisitos/`: un archivo por requisito (negocio, usuario, dominio, funcional, no funcional, transición, interfaces).
- `decisiones/`: decisiones de arquitectura (ADR).
- `diagramas/`: diagramas Mermaid, uno por pregunta.
- `cambios/`: fichas de cambios medianos y grandes.
- `historial/`: lo que sale de ESTADO.md por antigüedad (un archivo por mes) y fichas cerradas.
- `fuentes/`: documentos externos convertidos a Markdown (por ejemplo con Token Diet); es lo que conviene leer de ellos.
- `consultas/`: cuestionarios de elicitación que el usuario responde en el propio archivo (opcional, se crea con `consultas.py`).
"""


def escribir_si_falta(ruta, contenido, creados):
    if ruta.exists():
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    creados.append(ruta)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--docs", default="docs")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    docs = raiz / args.docs
    plantillas = Path(__file__).resolve().parents[2] / "senior-memoria" / "plantillas"
    creados = []
    escribir_si_falta(docs / "README.md", README, creados)
    # el mapa de conceptos se regenera cuando hace falta: no se versiona
    escribir_si_falta(docs / ".gitignore", ".grafo.json\n", creados)
    for nombre in PLANTILLAS:
        origen = plantillas / nombre
        contenido = origen.read_text(encoding="utf-8") if origen.exists() else f"# {nombre[:-3]}\n"
        escribir_si_falta(docs / nombre, contenido, creados)
    for carpeta in ["cambios", "decisiones", "diagramas", "historial"] + [f"requisitos/{t}" for t in TIPOS]:
        marcador = docs / carpeta / ".gitkeep"
        escribir_si_falta(marcador, "", creados)
    print(f"Documentación base: {len(creados)} elementos creados en {args.docs}/ (lo existente no se tocó).")
    indexador = Path(__file__).resolve().parents[2] / "senior-memoria" / "scripts" / "indexar_docs.py"
    if indexador.exists():
        p = subprocess.run([sys.executable, "-I", str(indexador), "indexar", "--raiz", str(raiz), "--docs", args.docs],
                           capture_output=True, encoding="utf-8", errors="replace")
        print(p.stdout.strip() or p.stderr.strip())


if __name__ == "__main__":
    main()
