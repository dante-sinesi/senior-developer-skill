#!/usr/bin/env python3
"""Ancla del método en un proyecto: un bloque marcado dentro de su CLAUDE.md con la secuencia de todo cambio de código.

Por qué: en conversaciones largas las skills dejan de estar a la vista; el CLAUDE.md del proyecto se vuelve a leer después de
compactar y también lo reciben los subagentes. Solo se toca lo que está entre las marcas; lo demás del archivo queda igual.

Uso:
    python ancla.py [--raiz .]             # muestra el bloque y qué haría; no escribe nada
    python ancla.py [--raiz .] --aplicar   # crea o actualiza el bloque (con la aprobación del usuario)

Sale con 1 sin tocar nada si las marcas están rotas o el archivo no es UTF-8. Solo biblioteca estándar.
"""
import argparse
import re
import sys
from pathlib import Path

INICIO = "<!-- senior:ancla"
FIN = "<!-- /senior:ancla -->"
BLOQUE = f"""{INICIO} (bloque generado por la skill senior; lo propio del proyecto va fuera de las marcas) -->
## Método de trabajo (en todo cambio de código, por chico que sea)

1. Antes de editar: leer `docs/ESTADO.md` y los requisitos, casos de uso o decisiones que el cambio afecta (se ubican con `docs/INDEX.md`).
2. Si cambia el comportamiento: primero un test que falla, derivado de la regla de negocio.
3. Programar solo lo pedido.
4. Verificar: correr los tests o comprobar el resultado.
5. En el mismo cambio, actualizar lo que quedó distinto: requisitos, casos de uso, diagramas, decisiones y `docs/ESTADO.md`.

Un paso que no corresponde no se saltea en silencio: se dice al cerrar (por ejemplo, «test: no aplica, solo texto»).

**Orden de las fuentes:** mandan los requisitos y las decisiones del usuario; el código es evidencia, no fuente. Un caso de uso o diagrama sin un requisito o decisión que lo respalde se marca «inferido del código, por confirmar».

**Al delegar** (subagente o sesión nueva), el encargo dice qué documentos leer, cuáles actualizar y que siga estos cinco pasos.

En cambios medianos o grandes, además: la skill `senior` y su método completo.
{FIN}"""

RE_BLOQUE = re.compile(re.escape(INICIO) + r".*?" + re.escape(FIN), re.S)


def nuevo_texto(texto):
    """Devuelve (texto con el bloque al día, qué se hace) o (None, motivo) si las marcas no permiten tocar el archivo sin riesgo."""
    inicios, fines = texto.count(INICIO), texto.count(FIN)
    salto = "\r\n" if "\r\n" in texto else "\n"
    bloque = BLOQUE.replace("\n", salto)
    if not inicios and not fines:
        if not texto.strip():
            return bloque + salto, "crear el bloque"
        return texto.rstrip("\r\n") + salto * 2 + bloque + salto, "agregar el bloque al final"
    encontrado = RE_BLOQUE.search(texto)
    if inicios != 1 or fines != 1 or not encontrado:
        return None, f"hay una marca de más, de menos o en otro orden ({inicios} de apertura, {fines} de cierre): se corrige a mano"
    return texto[:encontrado.start()] + bloque + texto[encontrado.end():], "actualizar el bloque"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    archivo = Path(a.raiz).resolve() / "CLAUDE.md"
    crudo = archivo.read_bytes() if archivo.exists() else b""
    bom = crudo.startswith(b"\xef\xbb\xbf")
    try:
        texto = crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        print(f"{archivo} no está en UTF-8: no se toca. Guardalo en UTF-8 y volvé a correr.")
        return 1
    resultado, que = nuevo_texto(texto)
    if resultado is None:
        print(f"{archivo}: {que}. No se tocó.")
        return 1
    if resultado == texto:
        print("El ancla ya está al día en CLAUDE.md.")
        return 0
    if not a.aplicar:
        print(f"Sin --aplicar no se escribe nada. Haría falta {que} en {archivo}:\n\n{BLOQUE}")
        return 0
    archivo.write_bytes((b"\xef\xbb\xbf" if bom else b"") + resultado.encode("utf-8"))
    print(f"Hecho ({que}) en {archivo}. Commitearlo (con aprobación) para que lo reciban las demás copias de trabajo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
