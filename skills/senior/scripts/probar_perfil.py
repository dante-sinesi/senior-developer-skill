#!/usr/bin/env python3
"""Valida un perfil de lenguaje y lo prueba contra un archivo de ejemplo.

Uso:
    python probar_perfil.py <perfil.json> [archivo_de_ejemplo]

Comprueba que el JSON tenga la estructura esperada, que todas las expresiones
regulares compilen y, si se da un archivo de ejemplo, muestra qué símbolos
detecta y qué alertas de seguridad dispara. Solo biblioteca estándar.
"""
import json
import re
import sys
from pathlib import Path

CLAVES_OBLIGATORIAS = ["lenguaje", "extensiones", "simbolos", "tests", "convenciones", "alertas_seguridad"]
CLAVES_TESTS = ["herramienta", "instalar", "comando", "patron_archivos"]


def compilar(texto, contexto, errores):
    try:
        return re.compile(texto)
    except re.error as e:
        errores.append(f"{contexto}: expresión regular inválida ({e})")
        return None


def validar(perfil):
    errores = []
    for clave in CLAVES_OBLIGATORIAS:
        if clave not in perfil:
            errores.append(f"Falta la clave '{clave}'")
    if errores:
        return errores, [], []
    if not all(e.startswith(".") for e in perfil["extensiones"]):
        errores.append("Cada extensión debe empezar con punto (ej. '.php')")
    for clave in CLAVES_TESTS:
        if clave not in perfil["tests"]:
            errores.append(f"tests: falta '{clave}'")
    simbolos = []
    for i, s in enumerate(perfil["simbolos"]):
        rx = compilar(s.get("patron", ""), f"simbolos[{i}]", errores)
        if rx and rx.groups < 1:
            errores.append(f"simbolos[{i}]: el patrón necesita un grupo de captura con el nombre")
        if rx:
            simbolos.append((s.get("tipo", "?"), rx))
    alertas = []
    for i, a in enumerate(perfil["alertas_seguridad"]):
        ctx = f"alertas_seguridad[{i}] ({a.get('id', 'sin id')})"
        for clave in ("id", "descripcion", "iso"):
            if clave not in a:
                errores.append(f"{ctx}: falta '{clave}'")
        if not any(k in a for k in ("patron", "archivo_ausente")):
            errores.append(f"{ctx}: necesita 'patron' o 'archivo_ausente'")
        rxs = {k: compilar(a[k], f"{ctx}.{k}", errores) for k in
               ("patron", "excepto_linea", "archivo_requiere", "archivo_ausente") if k in a}
        alertas.append((a.get("id", "?"), rxs))
    return errores, simbolos, alertas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    perfil = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    errores, simbolos, alertas = validar(perfil)
    if errores:
        print("PERFIL INVÁLIDO:")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)
    print(f"Perfil '{perfil['lenguaje']}' válido: {len(simbolos)} patrones de símbolos, {len(alertas)} alertas.")
    if len(sys.argv) < 3:
        return
    muestra = Path(sys.argv[2]).read_text(encoding="utf-8-sig", errors="replace")
    lineas = muestra.splitlines()
    print(f"\nSímbolos detectados en {sys.argv[2]}:")
    encontrados = 0
    for n, linea in enumerate(lineas, 1):
        for tipo, rx in simbolos:
            m = rx.search(linea)
            if m:
                encontrados += 1
                print(f"  línea {n}: {tipo} {m.group(1)}")
    if not encontrados:
        print("  (ninguno: revisar los patrones)")
    print("\nAlertas disparadas:")
    disparadas = 0
    for id_alerta, rxs in alertas:
        req = rxs.get("archivo_requiere")
        if req and not req.search(muestra):
            continue
        aus = rxs.get("archivo_ausente")
        if aus and "patron" not in rxs:
            if not aus.search(muestra):
                disparadas += 1
                print(f"  {id_alerta}: archivo completo")
            continue
        for n, linea in enumerate(lineas, 1):
            if rxs["patron"].search(linea) and not (rxs.get("excepto_linea") and rxs["excepto_linea"].search(linea)):
                disparadas += 1
                print(f"  {id_alerta} línea {n}: {linea.strip()[:90]}")
    if not disparadas:
        print("  (ninguna)")


if __name__ == "__main__":
    main()
