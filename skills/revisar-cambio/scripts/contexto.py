#!/usr/bin/env python3
"""Expediente de un cambio para revisarlo sin gastar tokens: qué toca, a quién afecta y qué mirar primero.

Uso:
    python contexto.py [sin-guardar | preparado | rama | pr <número> | <archivos...>] [--raiz .] [--base main]

  sin-guardar  los cambios sin commit (por defecto; si no hay, el último commit)
  preparado    lo que está en el área de preparación (git add)
  rama         la rama actual contra --base (main por defecto)
  pr <n>       un Pull Request de GitHub (necesita `gh` con sesión iniciada)
  <archivos>   esos archivos tal como están

Imprime un expediente corto: archivos y su tipo, símbolos tocados con quién los usa fuera del cambio, tests y
documentación, señales de riesgo en las líneas nuevas y pistas de la carga esperada. NO es la revisión: es el material
para hacerla (senior/scripts/impacto.py hace la búsqueda de usos). Solo lectura. Solo biblioteca estándar.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "senior" / "scripts"))
import impacto  # noqa: E402

SENALES = [
    (re.compile(r"\beval\s*\(|\bexec\s*\(|\bos\.system\s*\(|shell\s*=\s*True"), "ejecución dinámica o por shell: ¿entra algo del usuario?"),
    (re.compile(r"(?i)(select|insert|update|delete)\b[^\n]*(\+\s*\w|\$\{|\bf[\"'])"), "consulta SQL armada con texto: ¿inyección?"),
    (re.compile(r"(?i)innerHTML\s*=|document\.write\s*\(|dangerouslySetInnerHTML"), "HTML armado a mano: ¿XSS?"),
    (re.compile(r"(?i)\bexcept\b[^\n]*:\s*(pass)?\s*$|catch\s*\([^)]*\)\s*\{\s*\}"), "error tragado: ¿se pierde un fallo o un dato?"),
    (re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[\"'][^\"']{6,}"), "posible secreto escrito en el código"),
    (re.compile(r"(?i)\bfloat\s*\(|parseFloat\s*\(|\bdouble\b"), "decimales binarios: si es dinero, ¿redondeo?"),
    (re.compile(r"(?i)\brm\s+-rf\b|\bDROP\s+TABLE\b|\bTRUNCATE\b|\bunlink\s*\(|\brmtree\s*\("), "borrado: ¿se puede deshacer, está acotado?"),
    (re.compile(r"(?i)for\s[^\n]*:\s*$|\bforeach\b|\.forEach\("), "bucle nuevo: ¿hay una consulta o llamada por cada elemento?"),
]
PISTAS_CARGA = re.compile(r"(?i)\b(usuarios?|concurren\w*|workers?|procesos?|cron|lotes?|batch|colas?|rps|peticiones|requests?\s+por|"
                          r"tr[aá]fico|miles de|millones|escala\w*|producci[oó]n)\b")


def correr(args, raiz):
    p = subprocess.run(args, cwd=raiz, capture_output=True, encoding="utf-8", errors="replace", timeout=90)
    return p.stdout if p.returncode == 0 else ""


def rama_base(raiz, pedida):
    if pedida:
        return pedida
    for candidata in ("main", "master"):
        if subprocess.run(["git", "rev-parse", "--verify", "--quiet", candidata], cwd=raiz, capture_output=True).returncode == 0:
            return candidata
    return "HEAD~1"


def obtener_diff(raiz, objetivo, base):
    """(descripción, texto del diff, archivos nuevos sin seguimiento)."""
    nuevos = []
    if objetivo and objetivo[0] == "pr" and len(objetivo) > 1:
        return f"Pull Request {objetivo[1]}", correr(["gh", "pr", "diff", objetivo[1]], raiz), nuevos
    if objetivo and objetivo[0] == "preparado":
        return "cambios preparados (git add)", correr(["git", "diff", "--cached", "-U0"], raiz), nuevos
    if objetivo and objetivo[0] == "rama":
        b = rama_base(raiz, base)
        return f"rama actual contra {b}", correr(["git", "diff", "-U0", f"{b}...HEAD"], raiz), nuevos
    if objetivo and objetivo[0] not in ("sin-guardar",):
        texto = correr(["git", "diff", "-U0", "HEAD", "--", *objetivo], raiz)
        return "archivos indicados", texto, nuevos
    texto = correr(["git", "diff", "-U0", "HEAD"], raiz)
    nuevos = [l for l in correr(["git", "ls-files", "--others", "--exclude-standard"], raiz).splitlines() if l]
    if texto.strip() or nuevos:
        return "cambios sin commit", texto, nuevos
    return "último commit", correr(["git", "diff", "-U0", "HEAD~1", "HEAD"], raiz), nuevos


def archivos_del_diff(texto):
    """{archivo: [añadidas, eliminadas]} y las líneas añadidas por archivo."""
    cuenta, nuevas, actual = {}, {}, None
    for linea in texto.splitlines():
        if linea.startswith("+++ "):
            actual = linea[6:] if linea.startswith("+++ b/") else None
            if actual:
                cuenta.setdefault(actual, [0, 0])
                nuevas.setdefault(actual, [])
        elif linea.startswith("--- "):
            continue
        elif actual and linea.startswith("+"):
            cuenta[actual][0] += 1
            nuevas[actual].append(linea[1:])
        elif actual and linea.startswith("-"):
            cuenta[actual][1] += 1
    return cuenta, nuevas


def pistas_de_carga(raiz, limite=5):
    res = []
    for rel, lineas in impacto.archivos(raiz):
        base = Path(rel).name.lower()
        if not (base.startswith("readme") or base in ("docker-compose.yml", "docker-compose.yaml", "dockerfile", "procfile")
                or rel.startswith("docs/") and Path(rel).suffix == ".md"):
            continue
        for n, l in enumerate(lineas, 1):
            if PISTAS_CARGA.search(l):
                res.append(f"{rel}:{n} — {l.strip()[:90]}")
                if len(res) >= limite:
                    return res
    return res


def expediente(raiz, objetivo, base):
    descripcion, texto, nuevos = obtener_diff(raiz, objetivo, base)
    cuenta, nuevas = archivos_del_diff(texto)
    for n in nuevos:
        cuenta.setdefault(n, [0, 0])
    if not cuenta:
        return ["Expediente: no hay cambios para revisar (¿sin cambios, o el objetivo no existe?)."]
    por_cat = {}
    for archivo in cuenta:
        por_cat.setdefault(impacto.categoria(archivo), []).append(archivo)
    sumas = sum(v[0] for v in cuenta.values()), sum(v[1] for v in cuenta.values())
    lineas = [f"Expediente del cambio ({descripcion}): {len(cuenta)} archivos, +{sumas[0]} -{sumas[1]} líneas"]
    for cat in ("código", "tests", "documentos", "configuración"):
        if cat in por_cat:
            lineas.append(f"  {cat}: " + ", ".join(f"{a} (+{cuenta[a][0]} -{cuenta[a][1]})" for a in por_cat[cat][:8])
                          + (f" … y {len(por_cat[cat]) - 8} más" if len(por_cat[cat]) > 8 else ""))
    pares = impacto.simbolos_del_diff(texto)
    if pares:
        lineas.append("Símbolos tocados y quién los usa fuera de su archivo:")
        for archivo, nombre in pares[:12]:
            _, usos, _ = impacto.buscar_simbolo(raiz, nombre)
            externos = {c: [u for u in v if u[0] != archivo] for c, v in usos.items()}
            total = sum(len(v) for v in externos.values())
            nota = "" if usos["tests"] else "  [ningún test lo menciona]"
            ejemplo = next((f"{u[0]}:{u[1]}" for c in ("código", "tests") for u in externos[c]), "")
            lineas.append(f"  {nombre} ({archivo}): {total} usos externos" + (f", p. ej. {ejemplo}" if ejemplo else "") + nota)
        if len(pares) > 12:
            lineas.append(f"  … y {len(pares) - 12} símbolos más (impacto.py --cambio los lista)")
    if "código" in por_cat and "tests" not in por_cat:
        lineas.append("AVISO tests: hay cambios de código y ningún test nuevo o modificado.")
    if "código" in por_cat and not any(Path(a).name.lower().startswith("readme") for a in cuenta):
        lineas.append("AVISO documentación: cambia código y el README no se tocó (senior exige revisarlo en cada cambio).")
    senales = []
    for archivo, ls in nuevas.items():
        if impacto.categoria(archivo) not in ("código", "tests"):
            continue
        for l in ls:
            for rx, mensaje in SENALES:
                if rx.search(l) and (archivo, mensaje) not in [(s[0], s[1]) for s in senales]:
                    senales.append((archivo, mensaje, l.strip()[:70]))
    if senales:
        lineas.append("Señales en las líneas nuevas (confirmar cada una con un caso concreto antes de reportarla):")
        for archivo, mensaje, ejemplo in senales[:12]:
            lineas.append(f"  {archivo}: {mensaje} — «{ejemplo}»")
    pistas = pistas_de_carga(raiz)
    lineas.append("Carga esperada (pistas en README, docs y despliegue):" if pistas else
                  "Carga esperada: no hay pistas en README, docs ni despliegue; decir qué carga se asumió.")
    lineas += [f"  {p}" for p in pistas]
    return lineas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("objetivo", nargs="*")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--base", default=None)
    args = ap.parse_args()
    print("\n".join(expediente(Path(args.raiz).resolve(), args.objetivo, args.base)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
