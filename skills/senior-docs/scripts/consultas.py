#!/usr/bin/env python3
"""Consultas de elicitación por lotes: cuestionarios en Markdown que el usuario responde en el mismo archivo.

Uso:
    python consultas.py nueva "<tema>" [--raiz .] [--docs docs]
        Crea docs/consultas/NN-<tema>.md con la plantilla (ronda = cantidad de consultas + 1). No pisa nada.
    python consultas.py estado [--raiz .] [--docs docs] [--json]
        Resume cada consulta: preguntas, respondidas y sin responder, sin abrir los archivos completos.
    python consultas.py intencion "<tema>" [--raiz .] [--docs docs]
        Crea docs/consultas/NN-intencion-<tema>.md para guardar la intención confirmada en una entrevista corta
        (resultado, quién, por qué ahora, éxito, restricción, fuera de alcance). Nace «sin confirmar».
    python consultas.py confirmar "<respuesta del usuario>"
        Dice si esa respuesta cuenta como un sí explícito a la intención reformulada (código 0) o no (código 1).
        «Dale, lo que te parezca», un «no sé», el silencio o un «sí, pero…» no cuentan: se vuelve a preguntar con
        opciones concretas. Es una ayuda: ante la duda devuelve que no.

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
PLANTILLA_INTENCION = Path(__file__).resolve().parents[1] / "plantillas" / "intencion.md"
RE_PREGUNTA = re.compile(r"^#{3,4}\s+(P\d+)\.\s*(.*)$")
RE_RESPUESTA = re.compile(r"^\*\*Respuesta:\*\*\s*(.*)$")


def slug(texto):
    sin = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", sin.lower()).strip("-") or "consulta"


def carpeta_consultas(args):
    return Path(args.raiz).resolve() / args.docs / "consultas"


def nueva(args, plantilla=PLANTILLA, prefijo="", aviso=None):
    carpeta = carpeta_consultas(args)
    carpeta.mkdir(parents=True, exist_ok=True)
    existentes = [f for f in carpeta.glob("*.md") if re.match(r"^\d+-", f.name)]
    ronda = max([int(f.name.split("-")[0]) for f in existentes], default=0) + 1
    destino = carpeta / f"{ronda:02d}-{prefijo}{slug(args.tema)}.md"
    if destino.exists():
        sys.exit(f"Ya existe {destino.name}; no se pisa.")
    texto = plantilla.read_text(encoding="utf-8").replace("{{ronda}}", str(ronda)).replace("{{tema}}", args.tema)
    destino.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Creada {destino.relative_to(Path(args.raiz).resolve()).as_posix()}. " + (aviso or
          "Completar «Lo que entendí», los supuestos y las preguntas (cada una con propuesta); luego avisar al usuario."))


# Respuestas que NO son una confirmación: delegan la decisión, dudan o corrigen a medias.
NO_CONFIRMA = [
    r"lo que (te|le|vos|tu|tú|usted)?\s*(parezca|decidas|quieras|veas|creas|convenga|sea)", r"\bdecid[ií]\b", r"\bdecide\b",
    r"como (quieras|prefieras|te parezca)", r"me da (igual|lo mismo)", r"\bda (igual|lo mismo)\b", r"no s[eé]\b",
    r"lo que sea", r"\bcualquiera\b", r"\b(puede|podr[ií]a) ser\b", r"\b(tal vez|quiz[aá]s?|capaz|supongo|creo que)\b",
    r"m[aá]s o menos", r"\b(pero|salvo|aunque|excepto|solo que|solamente que)\b", r"\bmm+\b", r"\?",
]
SI_EXPLICITO = {"si", "sí", "ok", "okay", "okey", "dale", "correcto", "exacto", "confirmo", "confirmado", "perfecto",
                "afirmativo", "exactamente", "claro", "listo", "de acuerdo", "asi es", "así es", "eso es", "esta bien", "está bien"}


def es_confirmacion(respuesta):
    """(confirma, motivo). Solo un sí claro y corto a lo reformulado cuenta; lo demás se vuelve a preguntar."""
    bajo = " ".join(respuesta.lower().replace("¡", "").replace("!", "").replace(".", "").split())
    if not bajo:
        return False, "no hay respuesta: el silencio no es un sí"
    for patron in NO_CONFIRMA:
        if re.search(patron, bajo):
            return False, "delega, duda o corrige a medias: se vuelve a preguntar con opciones concretas"
    if len(bajo.split()) > 12:
        return False, "es larga y trae información nueva: se reformula con lo que agregó"
    palabras = [w.strip(",;:") for w in bajo.split()]
    pares = [" ".join(palabras[i:i + 2]) for i in range(len(palabras))]
    if any(w in SI_EXPLICITO for w in palabras + pares):
        return True, "sí explícito"
    return False, "no hay un sí explícito"


def confirmar(args):
    ok, motivo = es_confirmacion(args.respuesta)
    print(("Confirma: " if ok else "No confirma: ") + motivo + ".")
    sys.exit(0 if ok else 1)


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
        if meta.get("tipo") == "intencion":
            resumen.append({"archivo": f.name, "ronda": meta.get("ronda", "?"), "estado": meta.get("estado", "?"),
                            "preguntas": 0, "respondidas": 0, "sin_responder": [], "intencion": True})
            continue
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
        if r.get("intencion"):
            print(f"{r['archivo']} (intención, {r['estado']}).")
            continue
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
    i = sub.add_parser("intencion")
    i.add_argument("tema")
    c = sub.add_parser("confirmar")
    c.add_argument("respuesta")
    for p in (n, e, i):
        p.add_argument("--raiz", default=".")
        p.add_argument("--docs", default="docs")
    args = ap.parse_args()
    if args.orden == "nueva":
        nueva(args)
    elif args.orden == "intencion":
        nueva(args, PLANTILLA_INTENCION, "intencion-",
              "Completarla solo con lo que el usuario confirme; hasta entonces queda «sin confirmar».")
    elif args.orden == "confirmar":
        confirmar(args)
    else:
        estado(args)


if __name__ == "__main__":
    main()
