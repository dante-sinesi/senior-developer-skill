#!/usr/bin/env python3
"""Chequeos de seguridad automáticos (sin consumir tokens del modelo).

Uso:
    python seguridad.py [--raiz .] [--auditar] [--json] [--max 30]

Qué revisa:
  1. Alertas por lenguaje definidas en senior-lenguajes/perfiles/*.json
     (SQL concatenado, XSS, secretos serializados, falta de sesión/CSRF,
     despacho dinámico, etc.).
  2. Secretos escritos en el código (claves, tokens, contraseñas, claves privadas).
  3. Datos sensibles escritos en registros (logs).
  4. Con --auditar: dependencias con vulnerabilidades conocidas, usando las
     herramientas que ya existan (npm audit, composer audit, pip-audit).
     ATENCIÓN: --auditar consulta bases de vulnerabilidades por la red.

Son heurísticas: cada hallazgo es algo que REVISAR, no una condena. Para
descartar un falso positivo, escribir en la misma línea (o en la anterior)
el comentario:  senior-ignore: ID-DE-LA-ALERTA

Códigos de salida: 0 sin hallazgos, 1 con hallazgos. Solo biblioteca estándar.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv",
           "venv", ".idea", ".vscode", "coverage", ".next", ".grafo"}
SALTAR_NOMBRES = ("package-lock.json", "composer.lock", "yarn.lock", "pnpm-lock.yaml", ".min.js", ".min.css")
MAX_BYTES = 1_000_000

SECRETOS = [
    ("SEC-SECRETO-AWS", "Posible clave de acceso de AWS escrita en el código.", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SEC-SECRETO-CLAVE-PRIVADA", "Clave privada incluida en el repositorio.",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY")),
    ("SEC-SECRETO-TOKEN", "Token de servicio escrito en el código.",
     re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{32,})\b")),
    ("SEC-SECRETO-LITERAL", "Credencial asignada como texto literal; usar variables de entorno o un gestor de secretos.",
     re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|apikey|token|clave|contrasena)\w*\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']")),
]
VALOR_FALSO = re.compile(r"(?i)(example|ejemplo|changeme|cambiar|your|tu_|xxx|\*\*\*|<.*>|\$\{|%s|process\.env|getenv|placeholder|dummy|test)")
LOG_SENSIBLE = re.compile(
    r"(?i)(console\.(?:log|info|debug|error)|error_log|logger?\.\w+|logging\.\w+|print_r|var_dump|\bprint)\s*\(.*"
    r"(password|passwd|contrasena|contraseña|token|secret|clave|api[_-]?key)")


def localizar_perfiles():
    env = os.environ.get("SENIOR_PERFILES")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "senior-lenguajes" / "perfiles"


def cargar_perfiles():
    por_ext = {}
    carpeta = localizar_perfiles()
    if not carpeta.is_dir():
        return por_ext
    for ruta in sorted(carpeta.glob("*.json")):
        if ruta.name.startswith("_"):
            continue
        try:
            perfil = json.loads(ruta.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for ext in perfil.get("extensiones", []):
            por_ext[ext.lower()] = perfil
    return por_ext


def archivos_de_texto(raiz):
    for actual, carpetas, nombres in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR]
        for nombre in nombres:
            if nombre.endswith(SALTAR_NOMBRES):
                continue
            ruta = Path(actual) / nombre
            try:
                if ruta.stat().st_size > MAX_BYTES:
                    continue
                datos = ruta.read_bytes()
            except OSError:
                continue
            if b"\x00" in datos[:2048]:
                continue
            yield ruta, datos.decode("utf-8-sig", errors="replace")


def suprimida(lineas, indice, id_alerta):
    marca = f"senior-ignore: {id_alerta}"
    actual = lineas[indice]
    anterior = lineas[indice - 1] if indice > 0 else ""
    return marca in actual or marca in anterior


def hallazgo(id_alerta, ruta, linea, desc, iso, extracto=""):
    return {"id": id_alerta, "archivo": ruta, "linea": linea, "descripcion": desc, "iso": iso, "extracto": extracto}


def revisar_archivo(raiz, ruta, texto, perfiles):
    rel = ruta.relative_to(raiz).as_posix()
    lineas = texto.splitlines()
    res = []
    perfil = perfiles.get(ruta.suffix.lower())
    if perfil:
        for alerta in perfil.get("alertas_seguridad", []):
            req = alerta.get("archivo_requiere")
            if req and not re.search(req, texto):
                continue
            aus = alerta.get("archivo_ausente")
            if aus and not alerta.get("patron"):
                if not re.search(aus, texto) and not suprimida(lineas, 0, alerta["id"]):
                    res.append(hallazgo(alerta["id"], rel, 1, alerta["descripcion"], alerta.get("iso", "")))
                continue
            patron = re.compile(alerta["patron"])
            excepto = re.compile(alerta["excepto_linea"]) if alerta.get("excepto_linea") else None
            for i, linea in enumerate(lineas):
                if patron.search(linea) and not (excepto and excepto.search(linea)) \
                        and not suprimida(lineas, i, alerta["id"]):
                    res.append(hallazgo(alerta["id"], rel, i + 1, alerta["descripcion"],
                                        alerta.get("iso", ""), linea.strip()[:100]))
    for i, linea in enumerate(lineas):
        for id_s, desc, rx in SECRETOS:
            m = rx.search(linea)
            if not m:
                continue
            valor = m.group(1) if m.groups() else m.group(0)
            if id_s == "SEC-SECRETO-LITERAL" and VALOR_FALSO.search(valor + " " + linea):
                continue
            if not suprimida(lineas, i, id_s):
                res.append(hallazgo(id_s, rel, i + 1, desc, "5.17", linea.strip()[:60] + "…"))
        if LOG_SENSIBLE.search(linea) and not suprimida(lineas, i, "SEC-LOG-SENSIBLE"):
            res.append(hallazgo("SEC-LOG-SENSIBLE", rel, i + 1,
                                "Dato sensible escrito en un registro (log).", "8.15", linea.strip()[:100]))
    return res


def ejecutar(comando, cwd):
    try:
        p = subprocess.run(comando, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
        return p.stdout, p.returncode
    except (OSError, subprocess.TimeoutExpired):
        return "", -1


def auditar_dependencias(raiz):
    """Devuelve (lineas_resumen, hay_vulnerabilidades)."""
    resumen, hay = [], False
    if (raiz / "package.json").exists() and shutil.which("npm"):
        salida, _ = ejecutar(["npm", "audit", "--json"], raiz)
        try:
            v = json.loads(salida).get("metadata", {}).get("vulnerabilities", {})
            total = sum(v.get(k, 0) for k in ("low", "moderate", "high", "critical"))
            resumen.append(f"npm audit: {total} vulnerabilidades (altas: {v.get('high', 0)}, críticas: {v.get('critical', 0)})")
            hay = hay or total > 0
        except ValueError:
            resumen.append("npm audit: no se pudo interpretar la salida (¿falta package-lock.json o hay sin red?)")
    if (raiz / "composer.lock").exists() and shutil.which("composer"):
        salida, codigo = ejecutar(["composer", "audit", "--format=json"], raiz)
        try:
            avisos = json.loads(salida).get("advisories", {})
            total = sum(len(v) for v in avisos.values())
            resumen.append(f"composer audit: {total} avisos de seguridad")
            hay = hay or total > 0
        except ValueError:
            resumen.append(f"composer audit: sin resultado interpretable (código {codigo})")
    if (raiz / "requirements.txt").exists() and shutil.which("pip-audit"):
        salida, _ = ejecutar(["pip-audit", "-r", "requirements.txt", "-f", "json"], raiz)
        try:
            datos = json.loads(salida)
            deps = datos.get("dependencies", datos) if isinstance(datos, dict) else datos
            total = sum(len(d.get("vulns", [])) for d in deps)
            resumen.append(f"pip-audit: {total} vulnerabilidades")
            hay = hay or total > 0
        except ValueError:
            resumen.append("pip-audit: sin resultado interpretable")
    if not resumen:
        resumen.append("Auditoría de dependencias: no se encontró manifiesto con herramienta instalada "
                       "(npm, composer o pip-audit).")
    return resumen, hay


def analizar(raiz, auditar=False):
    perfiles = cargar_perfiles()
    hallazgos = []
    for ruta, texto in archivos_de_texto(raiz):
        hallazgos.extend(revisar_archivo(raiz, ruta, texto, perfiles))
    auditoria, vulnerable = ([], False)
    if auditar:
        auditoria, vulnerable = auditar_dependencias(raiz)
    return hallazgos, auditoria, vulnerable


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--auditar", action="store_true", help="auditar dependencias (usa la red)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max", type=int, default=30, help="máximo de hallazgos a mostrar")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    hallazgos, auditoria, vulnerable = analizar(raiz, args.auditar)
    if args.json:
        print(json.dumps({"hallazgos": hallazgos, "auditoria": auditoria}, ensure_ascii=False, indent=1))
    else:
        if not hallazgos:
            print("Seguridad: sin hallazgos de patrón.")
        else:
            print(f"Seguridad: {len(hallazgos)} hallazgos para revisar.")
            for h in hallazgos[:args.max]:
                iso = f" [ISO 27002:2022 {h['iso']}]" if h["iso"] else ""
                print(f"  {h['id']} {h['archivo']}:{h['linea']} — {h['descripcion']}{iso}")
            if len(hallazgos) > args.max:
                print(f"  … y {len(hallazgos) - args.max} más (usar --max o --json).")
        for linea in auditoria:
            print(f"  {linea}")
    sys.exit(1 if hallazgos or vulnerable else 0)


if __name__ == "__main__":
    main()
