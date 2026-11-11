#!/usr/bin/env python3
"""Consultas de elicitación por lotes: cuestionarios en Markdown que el usuario responde en el mismo archivo.

Uso:
    python consultas.py nueva "<tema>" [--raiz .] [--docs docs]
        Crea docs/consultas/NN-<tema>.md con la plantilla (ronda = cantidad de consultas + 1). No pisa nada.
    python consultas.py estado [--raiz .] [--docs docs] [--json]
        Resume cada consulta: preguntas, respondidas y sin responder, sin abrir los archivos completos.

Una pregunta es un encabezado «#### P<n>. …» seguido de una línea «**Respuesta:**». Cuenta como respondida si hay
texto después de «**Respuesta:**» (aunque sea «ok» o «no sé»). Las que quedan vacías no bloquean: se avanza con la
propuesta del modelo y el requisito resultante queda provisorio. Solo biblioteca estándar.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

PLANTILLA = Path(__file__).resolve().parents[1] / "plantillas" / "consulta.md"
RE_PREGUNTA = re.compile(r"^#{3,4}\s+(P\d+)\.\s*(.*)$")
RE_RESPUESTA = re.compile(r"^\*\*Respuesta:\*\*\s*(.*)$")


def slug(texto):
    sin = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin.lower()).strip("-") or "consulta"


def carpeta_consultas(args):
    return Path(args.raiz).resolve() / args.docs / "consultas"


def nueva(args):
    carpeta = carpeta_consultas(args)
    carpeta.mkdir(parents=True, exist_ok=True)
    existentes = [f for f in carpeta.glob("*.md") if re.match(r"^\d+-", f.name)]
    ronda = max([int(f.name.split("-")[0]) for f in existentes], default=0) + 1
    destino = carpeta / f"{ronda:02d}-{slug(args.tema)}.md"
    if destino.exists():
        sys.exit(f"Ya existe {destino.name}; no se pisa.")
    texto = PLANTILLA.read_text(encoding="utf-8").replace("{{ronda}}", str(ronda)).replace("{{tema}}", args.tema)
    destino.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Creada {destino.relative_to(Path(args.raiz).resolve()).as_posix()}. "
          "Completar «Lo que entendí», los supuestos y las preguntas (cada una con propuesta); luego avisar al usuario.")


def analizar(ruta):
    """Devuelve (frontmatter, preguntas) donde cada pregunta es (id, texto, respondida)."""
    lineas = ruta.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    meta = {}
    if lineas and lineas[0].strip() == "---":
        for l in lineas[1:]:
            if l.strip() == "---":
                break
            m = re.match(r"^([\w-]+)\s*:\s*(.*)$", l)
            if m:
                meta[m.group(1).lower()] = m.group(2).strip()
    preguntas, actual, respuesta, en_respuesta = [], None, [], False
    for l in lineas + ["#### P0. fin"]:
        m = RE_PREGUNTA.match(l)
        if m or l.startswith("## "):
            if actual:
                preguntas.append((actual[0], actual[1], bool("".join(respuesta).strip())))
            actual = (m.group(1), m.group(2).strip()) if m else None
            respuesta, en_respuesta = [], False
            continue
        if actual is None:
            continue
        r = RE_RESPUESTA.match(l)
        if r:
            en_respuesta = True
            respuesta.append(r.group(1))
        elif en_respuesta and not l.startswith("**") and not l.startswith("#"):
            respuesta.append(l)
    return meta, [p for p in preguntas if p[0] != "P0"]


def estado(args):
    carpeta = carpeta_consultas(args)
    archivos = sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []
    resumen = []
    for f in archivos:
        meta, preguntas = analizar(f)
        sin = [(i, t) for i, t, ok in preguntas if not ok]
        resumen.append({"archivo": f.name, "ronda": meta.get("ronda", "?"), "estado": meta.get("estado", "?"),
                        "preguntas": len(preguntas), "respondidas": len(preguntas) - len(sin),
                        "sin_responder": [f"{i}. {t}" for i, t in sin]})
    if args.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=1))
        return
    if not resumen:
        print("Consultas: no hay ninguna en docs/consultas/.")
        return
    for r in resumen:
        print(f"{r['archivo']} (ronda {r['ronda']}, {r['estado']}): {r['preguntas']} preguntas, "
              f"{r['respondidas']} respondidas, {len(r['sin_responder'])} sin responder.")
        for s in r["sin_responder"][:6]:
            print(f"  sin responder → {s[:90]}")
        if len(r["sin_responder"]) > 6:
            print(f"  … y {len(r['sin_responder']) - 6} más.")
    print("Las preguntas sin responder se toman con su propuesta como provisorias; no bloquean.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    n = sub.add_parser("nueva")
    n.add_argument("tema")
    e = sub.add_parser("estado")
    e.add_argument("--json", action="store_true")
    for p in (n, e):
        p.add_argument("--raiz", default=".")
        p.add_argument("--docs", default="docs")
    args = ap.parse_args()
    nueva(args) if args.orden == "nueva" else estado(args)


if __name__ == "__main__":
    main()
