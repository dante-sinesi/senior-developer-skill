#!/usr/bin/env python3
"""Paquete de inicio de requisitos de interfaz: las reglas de senior-diseno escritas como requisitos no funcionales.

Uso:
    python paquete_interfaz.py [--raiz .] [--excluir clave1,clave2] [--aplicar]

Sin --aplicar solo muestra qué se crearía (no escribe nada). Con --aplicar crea un requisito por regla en
docs/requisitos/no-funcional/RNF-NNN.md, con los números siguientes a los que ya existan, en estado «provisorio»:
son una PROPUESTA. El usuario decide, regla por regla, si la acepta (Estado: vigente), la cambia o la borra.
Cada requisito declara con «verificado_por» el chequeo de revisar_diseno.py que lo controla.

Sirve para un proyecto nuevo con interfaz y también para uno existente (lo propone /auditar-diseno). No pisa nada:
si una regla del paquete ya está en docs/requisitos/ (campo «clave»), se omite. Solo biblioteca estándar.
"""
import argparse
import re
import sys
from pathlib import Path

PLANTILLAS = Path(__file__).resolve().parents[1] / "plantillas" / "requisitos-interfaz"
RE_ID = re.compile(r"^RNF-(\d+)$")


def meta_de(texto):
    meta = {}
    lineas = texto.splitlines()
    if lineas and lineas[0].strip() == "---":
        for l in lineas[1:]:
            if l.strip() == "---":
                break
            m = re.match(r"^([\w-]+)\s*:\s*(.*)$", l)
            if m:
                meta[m.group(1).lower()] = m.group(2).strip()
    return meta


def existentes(carpeta):
    """(números RNF ya usados, claves del paquete ya presentes)."""
    usados, claves = set(), set()
    if carpeta.is_dir():
        for f in carpeta.rglob("*.md"):
            texto = f.read_text(encoding="utf-8-sig", errors="replace")
            meta = meta_de(texto)
            m = RE_ID.match(meta.get("id", "").upper()) or RE_ID.match(f.stem.upper())
            if m:
                usados.add(int(m.group(1)))
            if meta.get("paquete") == "interfaz" and meta.get("clave"):
                claves.add(meta["clave"])
    return usados, claves


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--excluir", default="", help="claves del paquete a omitir, separadas por comas")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    destino = raiz / "docs" / "requisitos" / "no-funcional"
    usados, claves = existentes(raiz / "docs" / "requisitos")
    excluidas = {c.strip() for c in args.excluir.split(",") if c.strip()}
    siguiente = max(usados, default=0) + 1
    plan = []
    for f in sorted(PLANTILLAS.glob("*.md")):
        texto = f.read_text(encoding="utf-8")
        meta = meta_de(texto)
        clave = meta.get("clave", f.stem)
        if clave in claves or clave in excluidas:
            continue
        plan.append((f"RNF-{siguiente:03d}", clave, meta.get("titulo", clave), texto))
        siguiente += 1
    if not plan:
        print("Paquete de interfaz: no hay nada para crear (las reglas ya están o se excluyeron).")
        return
    print(f"Paquete de interfaz: {len(plan)} {'requisito no funcional' if len(plan) == 1 else 'requisitos no funcionales'}, provisorios hasta que el usuario los confirme.")
    for rid, clave, titulo, texto in plan:
        print(f"  {rid}  {titulo}")
        if args.aplicar:
            destino.mkdir(parents=True, exist_ok=True)
            (destino / f"{rid}.md").write_text(texto.replace("{{id}}", rid), encoding="utf-8", newline="\n")
    if args.aplicar:
        print("Creados en docs/requisitos/no-funcional/. Siguiente paso: repasarlos con el usuario (aceptar = «Estado: vigente»,"
              " cambiar el valor o borrar el archivo) y correr verificar.py requisitos.")
    else:
        print("No se escribió nada. Para crearlos: agregar --aplicar (o --excluir con los nombres de las reglas que no se quieran).")


if __name__ == "__main__":
    main()
