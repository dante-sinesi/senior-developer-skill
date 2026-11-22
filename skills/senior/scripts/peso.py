#!/usr/bin/env python3
"""Tope de peso de las skills de un paquete: el contexto cuesta en cada sesión y en cada vuelta, así que el paquete no crece sin límite.

Qué comprueba (solo en un proyecto que tenga una carpeta `skills/`; en cualquier otro se omite):
  - descripción de cada skill: hasta 800 caracteres (se paga en TODAS las sesiones);
  - suma de las descripciones: hasta 10.000 caracteres (~2.500 tokens fijos por sesión). No suman las de las skills con `disable-model-invocation: true`
    (comandos que solo invoca el usuario): su descripción no se carga en el contexto, aunque sigue valiendo el tope de 800 por cada una;
  - cuerpo de cada SKILL.md (se paga al activarse): hasta 3.500 tokens y 150 líneas;
  - cada archivo de references/ (se lee solo si hace falta): hasta 5.500 tokens;
  - ningún script sin caso de uso: cada `scripts/*.py` tiene que aparecer nombrado en alguna documentación (SKILL.md, references o README) o ser
    importado o ejecutado por otro script;
  - cada skill figura en la tabla de skills del README.
Los tokens se estiman como caracteres / 4, igual que la auditoría de consumo de Token Diet. Una excepción se justifica por escrito dentro del SKILL.md
con `<!-- excepcion-peso: motivo -->` (el motivo es obligatorio y se informa como JUSTIFICADA). Solo lectura, solo biblioteca estándar.

Uso: python peso.py [--raiz .] [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

MAX_DESCRIPCION = 800
MAX_DESCRIPCIONES = 10_000
MAX_CUERPO_TOKENS = 3_500
MAX_CUERPO_LINEAS = 150
MAX_REFERENCIA_TOKENS = 5_500
EXCEPCION = re.compile(r"<!--\s*excepcion-peso:\s*(\S.*?)\s*-->")


def tokens(texto):
    return len(texto) // 4


def partir(texto):
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", texto, re.S)
    if not m:
        return "", texto
    return m.group(1), m.group(2)


def descripcion_de(frontmatter):
    m = re.search(r"(?m)^description:\s*(.*)$", frontmatter)
    if not m:
        return ""
    return m.group(1).strip().strip("'\"")


def analizar(raiz):
    """Devuelve (hallazgos, resumen). Cada hallazgo es (severidad, skill, mensaje); severidad FALLA o JUSTIFICADA."""
    carpeta = Path(raiz) / "skills"
    if not carpeta.is_dir():
        return None, None
    hallazgos, filas = [], []
    skills = sorted(d for d in carpeta.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
    readme = (Path(raiz) / "README.md").read_text(encoding="utf-8", errors="replace") if (Path(raiz) / "README.md").exists() else ""
    documentacion = readme + "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in carpeta.rglob("*.md"))
    codigo = {p: p.read_text(encoding="utf-8", errors="replace") for p in carpeta.rglob("*.py")}
    total_desc = 0
    solo_usuario = 0
    for d in skills:
        texto = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        fm, cuerpo = partir(texto)
        desc = descripcion_de(fm)
        excepcion = EXCEPCION.search(cuerpo)
        if re.search(r"(?m)^disable-model-invocation:\s*true", fm):
            solo_usuario += len(desc)
        else:
            total_desc += len(desc)
        lineas, toks = len(cuerpo.splitlines()), tokens(cuerpo)
        filas.append((d.name, len(desc), lineas, toks))

        def marca(sev_ok_si_justificada, mensaje):
            if excepcion and sev_ok_si_justificada:
                hallazgos.append(("JUSTIFICADA", d.name, f"{mensaje} (excepción: {excepcion.group(1)})"))
            else:
                hallazgos.append(("FALLA", d.name, mensaje))

        if len(desc) > MAX_DESCRIPCION:
            marca(True, f"la descripción mide {len(desc)} caracteres y el tope es {MAX_DESCRIPCION} (se paga en todas las sesiones)")
        if toks > MAX_CUERPO_TOKENS:
            marca(True, f"el cuerpo pesa ~{toks} tokens y el tope es {MAX_CUERPO_TOKENS} (se paga al activarse): mover lo accesorio a references/")
        if lineas > MAX_CUERPO_LINEAS:
            marca(True, f"el cuerpo tiene {lineas} líneas y el tope es {MAX_CUERPO_LINEAS}")
        for ref in sorted((d / "references").glob("*.md")) if (d / "references").is_dir() else []:
            tr = tokens(ref.read_text(encoding="utf-8", errors="replace"))
            if tr > MAX_REFERENCIA_TOKENS:
                marca(True, f"references/{ref.name} pesa ~{tr} tokens y el tope por archivo es {MAX_REFERENCIA_TOKENS}: dividirlo")
        if readme and f"`{d.name}`" not in readme:
            hallazgos.append(("FALLA", d.name, "no figura en el README (una skill sin caso de uso anotado no se agrega)"))
        for script in sorted((d / "scripts").glob("*.py")) if (d / "scripts").is_dir() else []:
            n = script.name
            referido = n in documentacion
            usado = any(otro != script and (re.search(rf"(?m)^\s*(import|from)\s+{re.escape(script.stem)}\b", t) or re.search(rf"[\"']{re.escape(n)}[\"']", t))
                        for otro, t in codigo.items())
            if not referido and not usado:
                hallazgos.append(("FALLA", d.name, f"scripts/{n} no se menciona en ninguna documentación ni lo usa otro script: sin caso de uso anotado"))
    if total_desc > MAX_DESCRIPCIONES:
        hallazgos.append(("FALLA", "(paquete)", f"las descripciones suman {total_desc} caracteres y el tope es {MAX_DESCRIPCIONES} (~{MAX_DESCRIPCIONES // 4} tokens fijos por sesión)"))
    resumen = {"skills": len(skills), "descripciones_caracteres": total_desc, "descripciones_solo_usuario": solo_usuario, "filas": filas}
    return hallazgos, resumen


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    hallazgos, resumen = analizar(args.raiz)
    if hallazgos is None:
        print("Peso: no hay carpeta skills/ (se omite).")
        return 0
    if args.json:
        print(json.dumps({"hallazgos": hallazgos, "resumen": resumen}, ensure_ascii=False, indent=1))
    else:
        fallas = [h for h in hallazgos if h[0] == "FALLA"]
        print(f"Peso: {resumen['skills']} skills, descripciones {resumen['descripciones_caracteres']} de {MAX_DESCRIPCIONES} caracteres (más {resumen['descripciones_solo_usuario']} de comandos solo del usuario, que no entran al contexto); {len(fallas)} fallas, {len(hallazgos) - len(fallas)} justificadas.")
        for sev, skill, msg in hallazgos:
            print(f"  {sev:11} {skill}: {msg}")
    return 1 if any(h[0] == "FALLA" for h in hallazgos) else 0


if __name__ == "__main__":
    sys.exit(main())
