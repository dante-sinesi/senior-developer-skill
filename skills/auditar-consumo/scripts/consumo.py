#!/usr/bin/env python3
"""Auditoría de consumo de contexto: mide cuánto cargan las skills, los archivos de instrucciones y la memoria.

Lo que se carga SIEMPRE (el nombre y la descripción de cada skill, CLAUDE.md, el índice de la memoria y, en un
proyecto con la metodología, ESTADO.md) se paga en cada sesión, se use o no. Lo que se carga AL ACTIVARSE (el cuerpo
de un SKILL.md) se paga cuando la skill entra en juego. Los `references/` se leen solo si hacen falta. Este script
mide las tres cosas con una estimación de tokens (caracteres / 4, con un margen de error de alrededor de 30 %),
marca lo que conviene recortar y dice qué no puede medir. Solo lee: no modifica nada.

Uso:
    python consumo.py [--raiz .] [--top 5] [--json] [--salida ruta.md] [--home <carpeta>]

  --raiz     proyecto a auditar (por defecto, la carpeta actual)
  --salida   además escribe el informe completo en Markdown (debe quedar dentro del proyecto, p. ej. .temporal/)
  --home     carpeta que hace de «home» (por defecto la del usuario); sirve para probar
No puede medir: las definiciones de las herramientas de cada servidor MCP, las skills de plugins, el prompt de
sistema ni el historial de la conversación. Solo biblioteca estándar.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

CARACTERES_POR_TOKEN = 4
# Umbrales orientativos (heurísticas: avisan, no condenan)
MAX_DESCRIPCION = 800
MAX_CUERPO_TOKENS = 5000
MAX_CUERPO_LINEAS = 500
MAX_CLAUDE_MD_TOKENS = 2500  # suma de todos los CLAUDE.md
MAX_INDICE_MEMORIA_LINEAS = 200
MAX_ESTADO_TOKENS = 1500
MAX_DESCRIPCIONES_TOKENS = 6000
MAX_SERVIDORES_MCP = 3


def tokens(caracteres):
    return math.ceil(caracteres / CARACTERES_POR_TOKEN) if caracteres else 0


def leer(ruta):
    try:
        return Path(ruta).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def separar_frontmatter(texto):
    """(campos, cuerpo) de un SKILL.md; los valores que siguen en líneas con sangría se unen al campo anterior."""
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        return {}, texto
    campos, clave = {}, None
    for i in range(1, len(lineas)):
        l = lineas[i]
        if l.strip() == "---":
            return campos, "\n".join(lineas[i + 1:])
        m = re.match(r"^([\w-]+):\s*(.*)$", l)
        if m:
            clave = m.group(1).lower()
            campos[clave] = m.group(2).strip().strip('"\'')
        elif clave and l.startswith((" ", "\t")):
            campos[clave] += " " + l.strip()
    return campos, ""


def medir_skills(carpeta, origen):
    """Una fila por skill de la carpeta (cada subcarpeta con SKILL.md)."""
    filas = []
    if not carpeta.is_dir():
        return filas
    for d in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        texto = leer(d / "SKILL.md")
        if texto is None:
            continue
        campos, cuerpo = separar_frontmatter(texto)
        nombre = campos.get("name") or d.name
        descripcion = campos.get("description", "")
        refs = [f for f in (d / "references").rglob("*") if f.is_file()] if (d / "references").is_dir() else []
        filas.append({
            "nombre": nombre, "origen": origen,
            "descripcion_caracteres": len(descripcion),
            "fijo_tokens": tokens(len(nombre) + len(descripcion) + 4),
            "cuerpo_tokens": tokens(len(cuerpo)), "cuerpo_lineas": len(cuerpo.splitlines()),
            "references": len(refs),
            "references_tokens": sum(tokens(len(leer(f) or "")) for f in refs),
        })
    return filas


def carpeta_de_memoria(home, raiz):
    """Memoria de Claude Code del proyecto: ~/.claude/projects/<ruta con todo lo no alfanumérico en guiones>/memory."""
    base = home / ".claude" / "projects"
    actual = raiz.resolve()
    for carpeta in [actual, *actual.parents]:
        candidata = base / re.sub(r"[^A-Za-z0-9]", "-", str(carpeta)) / "memory"
        if candidata.is_dir():
            return candidata
    return None


def medir_memoria(home, raiz):
    carpeta = carpeta_de_memoria(home, raiz)
    if carpeta is None:
        return None
    indice = leer(carpeta / "MEMORY.md") or ""
    otros = [f for f in carpeta.glob("*.md") if f.name != "MEMORY.md"]
    return {"indice_lineas": len(indice.splitlines()), "indice_tokens": tokens(len(indice)),
            "archivos": len(otros), "archivos_tokens": sum(tokens(len(leer(f) or "")) for f in otros)}


def medir_instrucciones(home, raiz):
    candidatos = [home / ".claude" / "CLAUDE.md", raiz / "CLAUDE.md", raiz / ".claude" / "CLAUDE.md", raiz / "CLAUDE.local.md"]
    filas = []
    for f in candidatos:
        t = leer(f)
        if t is not None:
            filas.append({"archivo": f.as_posix(), "tokens": tokens(len(t)), "lineas": len(t.splitlines())})
    return filas


def leer_json(ruta):
    t = leer(ruta)
    if not t:
        return {}
    try:
        d = json.loads(t)
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def medir_ajustes(home, raiz):
    """Hooks, permisos y servidores MCP declarados (se cuentan; su costo en tokens depende de cada servidor)."""
    hooks, permisos, servidores = 0, 0, set()
    for f in (home / ".claude" / "settings.json", raiz / ".claude" / "settings.json", raiz / ".claude" / "settings.local.json"):
        d = leer_json(f)
        for grupos in (d.get("hooks") or {}).values():
            for g in grupos if isinstance(grupos, list) else []:
                hooks += len(g.get("hooks", [])) if isinstance(g, dict) else 0
        permisos += len((d.get("permissions") or {}).get("allow", []) or [])
        servidores.update((d.get("mcpServers") or {}).keys())
    servidores.update((leer_json(raiz / ".mcp.json").get("mcpServers") or {}).keys())
    global_ = leer_json(home / ".claude.json")
    servidores.update((global_.get("mcpServers") or {}).keys())
    proyectos = global_.get("projects") or {}
    for clave, valor in proyectos.items():
        if isinstance(valor, dict) and Path(clave).as_posix().rstrip("/").lower() == raiz.resolve().as_posix().rstrip("/").lower():
            servidores.update((valor.get("mcpServers") or {}).keys())
    return {"hooks": hooks, "permisos": permisos, "servidores_mcp": sorted(servidores)}


def medir_proyecto(raiz):
    out = {}
    for nombre in ("ESTADO.md", "INDEX.md"):
        t = leer(raiz / "docs" / nombre)
        if t is not None:
            out[nombre] = tokens(len(t))
    return out


def auditar(raiz, home):
    skills = medir_skills(home / ".claude" / "skills", "usuario") + medir_skills(raiz / ".claude" / "skills", "proyecto")
    instrucciones = medir_instrucciones(home, raiz)
    memoria = medir_memoria(home, raiz)
    ajustes = medir_ajustes(home, raiz)
    proyecto = medir_proyecto(raiz)
    fijo = {
        "descripciones": sum(s["fijo_tokens"] for s in skills),
        "instrucciones": sum(i["tokens"] for i in instrucciones),
        "indice_memoria": memoria["indice_tokens"] if memoria else 0,
        "estado": proyecto.get("ESTADO.md", 0),
    }
    fijo["total"] = sum(fijo.values())
    return {"skills": skills, "instrucciones": instrucciones, "memoria": memoria, "ajustes": ajustes,
            "proyecto": proyecto, "fijo": fijo, "hallazgos": hallazgos(skills, instrucciones, memoria, ajustes, proyecto, fijo)}


def hallazgos(skills, instrucciones, memoria, ajustes, proyecto, fijo):
    h = []
    for s in sorted(skills, key=lambda s: -s["descripcion_caracteres"]):
        if s["descripcion_caracteres"] > MAX_DESCRIPCION:
            h.append(f"La descripción de «{s['nombre']}» tiene {s['descripcion_caracteres']} caracteres (más de {MAX_DESCRIPCION}): "
                     "se carga en cada sesión; conviene dejar solo cuándo se usa y qué hace.")
    for s in sorted(skills, key=lambda s: -s["cuerpo_tokens"]):
        if s["cuerpo_tokens"] > MAX_CUERPO_TOKENS or s["cuerpo_lineas"] > MAX_CUERPO_LINEAS:
            h.append(f"El cuerpo de «{s['nombre']}» pesa ~{s['cuerpo_tokens']} tokens y {s['cuerpo_lineas']} líneas cuando se activa: "
                     "conviene mover el detalle a `references/`, que se lee solo si hace falta.")
    total_instrucciones = sum(i["tokens"] for i in instrucciones)
    if total_instrucciones > MAX_CLAUDE_MD_TOKENS:
        h.append(f"Los CLAUDE.md suman ~{total_instrucciones} tokens (más de {MAX_CLAUDE_MD_TOKENS}) y se cargan siempre: "
                 "dejar solo lo que se debe cumplir en cada sesión y mover el resto a una skill o a un documento.")
    if memoria and memoria["indice_lineas"] > MAX_INDICE_MEMORIA_LINEAS:
        h.append(f"El índice de la memoria tiene {memoria['indice_lineas']} líneas: lo que pasa de la línea {MAX_INDICE_MEMORIA_LINEAS} "
                 "no se carga. Fusionar o borrar memorias viejas.")
    if proyecto.get("ESTADO.md", 0) > MAX_ESTADO_TOKENS:
        h.append(f"ESTADO.md pesa ~{proyecto['ESTADO.md']} tokens y se lee al empezar cada sesión: pasar lo viejo a `docs/historial/`.")
    if fijo["descripciones"] > MAX_DESCRIPCIONES_TOKENS:
        h.append(f"Las descripciones de las {len(skills)} skills suman ~{fijo['descripciones']} tokens en cada sesión: "
                 "ver qué skills casi no se usan.")
    if len(ajustes["servidores_mcp"]) > MAX_SERVIDORES_MCP:
        h.append(f"Hay {len(ajustes['servidores_mcp'])} servidores MCP ({', '.join(ajustes['servidores_mcp'])}): "
                 "cada uno suma las definiciones de sus herramientas al contexto, y eso no se mide acá.")
    nombres = [s["nombre"] for s in skills]
    repetidas = sorted({n for n in nombres if nombres.count(n) > 1})
    if repetidas:
        h.append("Skills con el mismo nombre en el usuario y en el proyecto: " + ", ".join(repetidas) + ".")
    return h


def resumen(r, top=5):
    f = r["fijo"]
    l = [f"Consumo fijo (se paga en cada sesión): ~{f['total']} tokens = descripciones de {len(r['skills'])} skills ~{f['descripciones']}"
         f" + CLAUDE.md ~{f['instrucciones']} + índice de memoria ~{f['indice_memoria']} + ESTADO.md ~{f['estado']}."]
    por_fijo = sorted(r["skills"], key=lambda s: -s["fijo_tokens"])[:top]
    l.append("Skills que más pesan siempre: " + "; ".join(f"{s['nombre']} ~{s['fijo_tokens']}" for s in por_fijo) + ".")
    por_cuerpo = sorted(r["skills"], key=lambda s: -s["cuerpo_tokens"])[:top]
    l.append("Skills que más pesan al activarse: " + "; ".join(f"{s['nombre']} ~{s['cuerpo_tokens']}" for s in por_cuerpo) + ".")
    a = r["ajustes"]
    l.append(f"Ajustes: {a['hooks']} hooks, {a['permisos']} permisos, {len(a['servidores_mcp'])} servidores MCP.")
    if r["memoria"]:
        m = r["memoria"]
        l.append(f"Memoria: índice de {m['indice_lineas']} líneas (~{m['indice_tokens']} tokens) y {m['archivos']} archivos (~{m['archivos_tokens']}, se leen solo si hacen falta).")
    if r["hallazgos"]:
        l.append(f"Para revisar ({len(r['hallazgos'])}):")
        l += [f"  - {x}" for x in r["hallazgos"]]
    else:
        l.append("Sin hallazgos: nada supera los umbrales.")
    l.append("No se mide: herramientas de servidores MCP, skills de plugins, prompt de sistema ni historial. Tokens estimados (caracteres / 4, ±30 %).")
    return l


def informe_md(r, raiz):
    l = ["# Consumo de contexto", "", f"Proyecto: `{raiz.name}`. Tokens estimados (caracteres / 4, margen de ±30 %).", ""]
    l += ["## Resumen", ""] + [x if x.startswith("  ") else "- " + x for x in resumen(r, top=8)] + [""]
    l += ["## Skills", "", "| Skill | Origen | Siempre (tokens) | Al activarse (tokens) | Líneas | References (tokens) |", "|---|---|---|---|---|---|"]
    for s in sorted(r["skills"], key=lambda s: -(s["fijo_tokens"] + s["cuerpo_tokens"])):
        l.append(f"| {s['nombre']} | {s['origen']} | {s['fijo_tokens']} | {s['cuerpo_tokens']} | {s['cuerpo_lineas']} | {s['references_tokens']} ({s['references']}) |")
    l += ["", "## Archivos de instrucciones", ""] + [f"- `{i['archivo']}`: ~{i['tokens']} tokens, {i['lineas']} líneas" for i in r["instrucciones"]]
    return "\n".join(l) + "\n"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--home", default=None)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--salida", default=None)
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    home = Path(args.home).resolve() if args.home else Path.home()
    r = auditar(raiz, home)
    if args.salida:
        destino = (raiz / args.salida).resolve() if not Path(args.salida).is_absolute() else Path(args.salida).resolve()
        if raiz != destino and raiz not in destino.parents:
            sys.exit("--salida debe quedar dentro del proyecto (por ejemplo .temporal/consumo.md).")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(informe_md(r, raiz), encoding="utf-8", newline="\n")
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("\n".join(resumen(r, args.top)))
        if args.salida:
            print(f"Informe completo: {Path(args.salida).as_posix()}")
    sys.exit(1 if r["hallazgos"] else 0)


if __name__ == "__main__":
    main()
