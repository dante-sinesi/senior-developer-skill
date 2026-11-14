#!/usr/bin/env python3
"""Diagramas en el README: la arquitectura y los flujos principales se muestran dibujados, con un texto breve debajo.

GitHub dibuja Mermaid dentro del README. Para que el diagrama del README no se desfase del de `docs/diagramas/` (un dato,
un lugar), este script lo COPIA desde ahí entre dos marcas y comprueba que la copia siga igual a su fuente:

    <!-- diagrama: docs/diagramas/modulos.md#1 -->
    ### Dependencias entre módulos
    ```mermaid
    …
    ```
    <!-- /diagrama -->

    Texto breve de lo que se ve (lo escribe una persona; queda fuera de las marcas y no se toca).

Uso:
    python readme_diagramas.py listar  [--raiz .]
        Los diagramas de docs/diagramas/ con su tipo, tamaño, si están confirmados o son provisorios y si ya están en el README.
    python readme_diagramas.py proponer [--aplicar] [ref …] [--raiz .]
        Arma la lista de diagramas que conviene mostrar (hasta 3), cada uno con un texto sugerido; con --aplicar, y solo con el
        visto bueno del usuario, los agrega (todos o los que se pidan).
    python readme_diagramas.py agregar docs/diagramas/<archivo>.md[#n] --texto "Qué se ve" [--raiz .]
        Copia el diagrama al README, en la sección «Cómo funciona» (la crea si falta), con su texto debajo.
    python readme_diagramas.py quitar  docs/diagramas/<archivo>.md[#n] [--raiz .]
    python readme_diagramas.py sync    [--raiz .]     # vuelve a copiar cada diagrama desde su fuente
    python readme_diagramas.py estado  [--raiz .]     # copias desfasadas, sin texto, de más o demasiado grandes (código 1 si hay)

Reglas: hasta 4 diagramas en el README, más chicos que los de docs/ (se leen al ancho de la página), cada uno con su texto
(hasta 400 caracteres) y sin diagramas escritos a mano fuera de las marcas. Un diagrama provisorio (inferido del código con
`/documentar-proyecto`) entra con una nota visible hasta que se confirme; confirmarlo es `documentar.py confirmar-diagrama`.
Solo biblioteca estándar.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "senior" / "scripts"))
import diagramas as dg  # noqa: E402 motivo: sys.path se ajusta justo antes de importarlo

MAX_DIAGRAMAS = 4
MAX_TEXTO = 400
SECCION = "Cómo funciona"
LIMITES_README = {"secuencia_participantes": 6, "secuencia_mensajes": 12, "clases": 8, "clase_miembros": 6, "flujo_nodos": 12, "er_entidades": 8}
NOTA_PROVISORIA = "> Diagrama inferido del código y sin confirmar: describe lo que el código hace hoy, no necesariamente lo que debería hacer."
MARCA_GENERADO = re.compile(r"<!--\s*generado por documentar\.py")
INICIO = re.compile(r"^<!--\s*diagrama:\s*(\S+?)(?:#(\d+))?\s*-->\s*$")
FIN = re.compile(r"^<!--\s*/diagrama\s*-->\s*$")
ANTES_DE = ("## Cómo empezar", "## Pruebas", "## Estructura del proyecto", "## Documentación", "## Más información", "## Para quien colabora", "## Contribuir")


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8-sig", errors="replace")


def escribir(ruta, texto):
    Path(ruta).write_text(texto, encoding="utf-8", newline="\n")


def ruta_readme(raiz):
    return next((Path(raiz) / n for n in ("README.md", "readme.md", "Readme.md") if (Path(raiz) / n).exists()), None)


def referencia(texto):
    """(ruta relativa, número de bloque) de «docs/diagramas/x.md#2»."""
    m = re.fullmatch(r"(.+?)(?:#(\d+))?", texto.strip())
    return m.group(1).replace("\\", "/"), int(m.group(2) or 1)


def es_provisorio(texto):
    return bool(MARCA_GENERADO.search(texto[:900]))


def bloque_de_fuente(raiz, ruta, n):
    """(título, código mermaid, provisorio, tipo) del bloque n de un archivo de diagramas, o un mensaje de error."""
    f = Path(raiz) / ruta
    if not f.is_file():
        return None, f"no existe {ruta}"
    texto = leer(f)
    bloques = dg.bloques_de_markdown(texto)
    if not 1 <= n <= len(bloques):
        return None, f"{ruta} tiene {len(bloques)} diagramas y se pidió el {n}"
    _, codigo, previas = bloques[n - 1]
    titulo = next((re.sub(r"^#+\s*", "", l).strip() for l in reversed(previas) if re.match(r"^\s*#{1,6}\s+\S", l)), None)
    if not titulo:
        m = re.search(r"^#\s+(.+)$", texto, re.M)
        titulo = m.group(1).strip() if m else f.stem
    return (titulo, codigo.strip("\n"), es_provisorio(texto), dg.tipo_diagrama(codigo)), None


def tamano_excedido(codigo):
    """Lo que hace que un diagrama no quepa en el README: demasiadas piezas o un ancho que lo achicaría hasta volverlo ilegible."""
    tipo = dg.tipo_diagrama(codigo)
    exceso = dg.excesos(tipo, dg.medir(tipo, codigo), LIMITES_README)
    ancho = dg.ancho_estimado(tipo, codigo)
    if ancho and dg.escala_en_readme(ancho) < dg.ESCALA_MINIMA:
        exceso.append(f"ancho estimado {ancho} px: se achicaría al {round(dg.escala_en_readme(ancho) * 100)} % al ancho del README "
                      f"(mínimo {round(dg.ESCALA_MINIMA * 100)} %); " + ("vertical (TB) y etiquetas más cortas" if tipo == "flujo" else "mensajes más cortos"))
    return exceso


def renderizar(ruta, n, titulo, codigo, provisorio):
    partes = [f"<!-- diagrama: {ruta}#{n} -->", f"### {titulo}", ""]
    if provisorio:
        partes += [NOTA_PROVISORIA, ""]
    partes += ["```mermaid", codigo, "```", "<!-- /diagrama -->"]
    return "\n".join(partes)


def analizar_readme(texto):
    """[{ruta, n, inicio, fin, cuerpo, texto_debajo}] con las líneas (base 0) de cada bloque gestionado."""
    lineas = texto.split("\n")
    out, i = [], 0
    while i < len(lineas):
        m = INICIO.match(lineas[i].strip())
        if m:
            j = i + 1
            while j < len(lineas) and not FIN.match(lineas[j].strip()):
                j += 1
            if j >= len(lineas):
                break
            k = j + 1
            while k < len(lineas) and not lineas[k].strip():
                k += 1
            debajo = []
            while k < len(lineas) and lineas[k].strip() and not lineas[k].startswith("#") and not INICIO.match(lineas[k].strip()):
                debajo.append(lineas[k].strip())
                k += 1
            out.append({"ruta": m.group(1), "n": int(m.group(2) or 1), "inicio": i, "fin": j, "cuerpo": "\n".join(lineas[i:j + 1]),
                        "texto_debajo": " ".join(debajo)})
            i = j + 1
        else:
            i += 1
    return out


def estado(raiz):
    """(problemas, cantidad de diagramas). Sin README no hay nada que revisar."""
    readme = ruta_readme(raiz)
    if readme is None:
        return [], 0
    texto = leer(readme)
    bloques = analizar_readme(texto)
    problemas = []
    if len(bloques) > MAX_DIAGRAMAS:
        problemas.append(f"{len(bloques)} diagramas (máximo {MAX_DIAGRAMAS}): el README orienta, el detalle va en docs/diagramas/")
    for b in bloques:
        ref = f"{b['ruta']}#{b['n']}"
        fuente, error = bloque_de_fuente(raiz, b["ruta"], b["n"])
        if error:
            problemas.append(f"{ref}: {error}")
            continue
        esperado = renderizar(b["ruta"], b["n"], *fuente[:3])
        if b["cuerpo"].strip() != esperado.strip():
            problemas.append(f"{ref}: la copia del README difiere de su fuente (ejecutar `readme_diagramas.py sync`)")
        if not b["texto_debajo"]:
            problemas.append(f"{ref}: sin el texto breve que explica qué se ve")
        elif len(b["texto_debajo"]) > MAX_TEXTO:
            problemas.append(f"{ref}: el texto debajo tiene {len(b['texto_debajo'])} caracteres (máximo {MAX_TEXTO})")
        for exceso in tamano_excedido(fuente[1]):
            problemas.append(f"{ref}: demasiado grande para el README: {exceso}")
    # un bloque mermaid fuera de las marcas es un diagrama escrito a mano: se desfasa sin avisar
    lineas = texto.split("\n")
    dentro = set()
    for b in bloques:
        dentro.update(range(b["inicio"], b["fin"] + 1))
    for i, l in enumerate(lineas):
        if l.strip().startswith("```mermaid") and i not in dentro:
            problemas.append(f"README.md:{i + 1}: diagrama escrito a mano en el README; moverlo a docs/diagramas/ y copiarlo con `readme_diagramas.py agregar`")
    return problemas, len(bloques)


def candidatos(raiz):
    """[{ref, titulo, tipo, medidas, provisorio, en_readme, excesos}] de docs/diagramas/."""
    carpeta = Path(raiz) / "docs" / "diagramas"
    readme = ruta_readme(raiz)
    usados = {(b["ruta"], b["n"]) for b in analizar_readme(leer(readme))} if readme else set()
    out = []
    for f in sorted(carpeta.rglob("*.md")) if carpeta.is_dir() else []:
        rel = f.relative_to(raiz).as_posix()
        for n in range(1, len(dg.bloques_de_markdown(leer(f))) + 1):
            fuente, _ = bloque_de_fuente(raiz, rel, n)
            if not fuente:
                continue
            titulo, codigo, provisorio, tipo = fuente
            out.append({"ref": f"{rel}#{n}", "titulo": titulo, "tipo": tipo, "medidas": dg.medir(tipo, codigo), "provisorio": provisorio,
                        "en_readme": (rel, n) in usados, "excesos": tamano_excedido(codigo)})
    return out


def cmd_listar(args):
    lista = candidatos(args.raiz)
    if not lista:
        print("No hay diagramas en docs/diagramas/. Se generan con `/documentar-proyecto` o se escriben con senior-docs.")
        return
    print("Diagramas de docs/diagramas/ (ref · tipo · tamaño · estado · README):")
    for c in lista:
        medidas = ", ".join(f"{v} {k}" for k, v in c["medidas"].items())
        apto = "cabe en el README" if not c["excesos"] else "no cabe: " + "; ".join(c["excesos"])
        sirve = c["tipo"] in ("secuencia", "er", "flujo")
        recomendado = " · recomendado" if sirve and not c["excesos"] and not c["en_readme"] else ""
        print(f"  {c['ref']} · {c['tipo']} · {medidas} · {'provisorio' if c['provisorio'] else 'confirmado'} · "
              f"{'ya está' if c['en_readme'] else 'no está'} · {apto}{recomendado}  [{c['titulo']}]")
    print("Para el README conviene la arquitectura, de uno a tres flujos y, si hay datos, el entidad-relación; las clases suelen ser ruido. "
          "`proponer` arma la lista con un texto sugerido.")


def insertar(texto, bloque, texto_debajo):
    """Agrega el bloque y su texto al final de la sección «Cómo funciona»; si no existe, la crea antes de Pruebas, Estructura, Documentación o Contribuir."""
    lineas = texto.split("\n")
    nuevo = bloque.split("\n") + ["", texto_debajo, ""]
    existente = next((i for i, l in enumerate(lineas) if re.match(rf"^##\s+{re.escape(SECCION)}\s*$", l.strip())), None)
    if existente is not None:
        pos = next((i for i in range(existente + 1, len(lineas)) if lineas[i].startswith("## ")), len(lineas))
        while pos > existente + 1 and not lineas[pos - 1].strip():
            pos -= 1
        return "\n".join(lineas[:pos] + [""] + nuevo + lineas[pos:])
    pos = next((i for i, l in enumerate(lineas) if l.strip() in ANTES_DE), len(lineas))
    antes = lineas[:pos]
    if antes and antes[-1].strip():
        antes.append("")
    return "\n".join(antes + [f"## {SECCION}", ""] + nuevo + lineas[pos:])


def agregar_diagrama(raiz, diagrama, texto):
    """Copia un diagrama al README. Devuelve (mensaje, aviso); si no se puede, lanza SystemExit con el motivo."""
    readme = ruta_readme(raiz)
    if readme is None:
        sys.exit("No hay README.md en la raíz del proyecto.")
    ruta, n = referencia(diagrama)
    fuente, error = bloque_de_fuente(raiz, ruta, n)
    if error:
        sys.exit("No se puede agregar: " + error)
    texto_debajo = " ".join((texto or "").split())
    if not texto_debajo:
        sys.exit("Falta --texto: una o dos oraciones que expliquen qué se ve en el diagrama.")
    if len(texto_debajo) > MAX_TEXTO:
        sys.exit(f"El texto tiene {len(texto_debajo)} caracteres (máximo {MAX_TEXTO}): el diagrama explica, el texto solo orienta.")
    titulo, codigo, provisorio, tipo = fuente
    exceso = tamano_excedido(codigo)
    if exceso:
        sys.exit("No cabe en el README: " + "; ".join(exceso) + ". Elegir otro diagrama o dividir este en uno general y otros de detalle.")
    contenido = leer(readme)
    actuales = analizar_readme(contenido)
    if any((b["ruta"], b["n"]) == (ruta, n) for b in actuales):
        sys.exit(f"{ruta}#{n} ya está en el README (`quitar` y volver a agregar para cambiarlo, o editar el texto debajo).")
    if len(actuales) >= MAX_DIAGRAMAS:
        sys.exit(f"El README ya tiene {len(actuales)} diagramas (máximo {MAX_DIAGRAMAS}): quitar uno antes de agregar otro.")
    escribir(readme, insertar(contenido, renderizar(ruta, n, titulo, codigo, provisorio), texto_debajo))
    aviso = "un diagrama de clases en el README suele ser ruido; conviene la arquitectura y los flujos principales." if tipo == "clases" else ""
    return f"Agregado {ruta}#{n} al README" + (" con la nota de «sin confirmar»." if provisorio else "."), aviso


def cmd_agregar(args):
    mensaje, aviso = agregar_diagrama(Path(args.raiz).resolve(), args.diagrama, args.texto)
    print(mensaje)
    if aviso:
        print("AVISO: " + aviso)


def pregunta_de(raiz, ruta, n):
    """La pregunta que responde el diagrama: el párrafo que está justo arriba del bloque."""
    bloques = dg.bloques_de_markdown(leer(Path(raiz) / ruta))
    previas = bloques[n - 1][2] if 1 <= n <= len(bloques) else []
    for l in reversed(previas):
        s = l.strip()
        if s and not s.startswith("#"):
            return s
    return ""


def texto_sugerido(c, pregunta):
    """Un texto breve para empezar; la persona lo ajusta si quiere (`quitar` y `agregar --texto`, o editar el texto debajo del diagrama)."""
    m = c["medidas"]
    if c["tipo"] == "secuencia":
        base = pregunta or c["titulo"]
        return f"{base} Se lee de arriba hacia abajo: cada flecha es un mensaje entre participantes."
    if c["tipo"] == "er":
        return f"Las {m.get('entidades', '')} tablas del sistema y cómo se relacionan: la tabla del lado uno apunta a las que dependen de ella."
    if "modulos" in c["ref"]:
        return f"Los {m.get('nodos', '')} módulos del proyecto y qué módulo usa a cuál: cada flecha va de quien importa a lo importado."
    return f"{pregunta or c['titulo']} Cada flecha lleva al paso siguiente."


def propuestas(raiz):
    """[(candidato, texto sugerido)] de los diagramas recomendados que todavía no están en el README y caben."""
    readme = ruta_readme(raiz)
    lugares = max(0, MAX_DIAGRAMAS - len(analizar_readme(leer(readme)))) if readme else 0
    elegidos = [c for c in candidatos(raiz) if c["tipo"] in ("secuencia", "er", "flujo") and not c["excesos"] and not c["en_readme"]]
    orden = {"flujo": 0, "secuencia": 1, "er": 2}
    elegidos.sort(key=lambda c: (orden[c["tipo"]], c["ref"]))
    out = []
    for c in elegidos[:min(lugares, 3)]:
        ruta, n = referencia(c["ref"])
        out.append((c, texto_sugerido(c, pregunta_de(raiz, ruta, n))))
    return out


def cmd_proponer(args):
    raiz = Path(args.raiz).resolve()
    lista = propuestas(raiz)
    if not lista:
        print("No hay diagramas para proponer: o no hay en docs/diagramas/, o ya están en el README, o el README ya tiene el máximo "
              f"({MAX_DIAGRAMAS}), o ninguno cabe al ancho del README.")
        if args.aplicar and args.refs:
            sys.exit("Ninguna de las referencias pedidas está entre las propuestas.")
        return
    elegidos = lista if not args.refs else [(c, t) for c, t in lista if c["ref"] in args.refs or c["ref"].split("#")[0] in args.refs]
    if args.aplicar:
        if not elegidos:
            sys.exit("Ninguna de las referencias pedidas está entre las propuestas.")
        for c, texto in elegidos:
            mensaje, _ = agregar_diagrama(raiz, c["ref"], texto)
            print(mensaje)
        print("Los textos son sugeridos: se pueden editar a mano en el README (quedan debajo del diagrama, fuera de las marcas).")
        return
    print("Diagramas que conviene mostrar en el README (con un texto sugerido):")
    for c, texto in lista:
        estado_dg = "provisorio: entra con la nota «sin confirmar»" if c["provisorio"] else "confirmado"
        print(f"  - {c['ref']} · {c['tipo']} · {c['titulo']} ({estado_dg})\n      Texto: {texto}")
    print("Con el visto bueno del usuario: `readme_diagramas.py proponer --aplicar` (todos) o `proponer --aplicar <ref> …` (algunos).")


def cmd_quitar(args):
    raiz = Path(args.raiz).resolve()
    readme = ruta_readme(raiz)
    ruta, n = referencia(args.diagrama)
    texto = leer(readme) if readme else ""
    bloque = next((b for b in analizar_readme(texto) if (b["ruta"], b["n"]) == (ruta, n)), None)
    if not bloque:
        sys.exit(f"{ruta}#{n} no está en el README.")
    lineas = texto.split("\n")
    fin = bloque["fin"] + 1
    while fin < len(lineas) and not lineas[fin].strip():
        fin += 1
    while fin < len(lineas) and lineas[fin].strip() and not lineas[fin].startswith("#") and not INICIO.match(lineas[fin].strip()):
        fin += 1
    resto = lineas[:bloque["inicio"]] + lineas[fin:]
    escribir(readme, re.sub(r"\n{3,}", "\n\n", "\n".join(resto)))
    print(f"Quitado {ruta}#{n} del README (el diagrama sigue en docs/diagramas/).")


def cmd_sync(args):
    raiz = Path(args.raiz).resolve()
    readme = ruta_readme(raiz)
    if readme is None:
        sys.exit("No hay README.md en la raíz del proyecto.")
    texto = leer(readme)
    lineas = texto.split("\n")
    cambios, errores = [], []
    for b in reversed(analizar_readme(texto)):
        fuente, error = bloque_de_fuente(raiz, b["ruta"], b["n"])
        if error:
            errores.append(f"{b['ruta']}#{b['n']}: {error}")
            continue
        nuevo = renderizar(b["ruta"], b["n"], *fuente[:3])
        if b["cuerpo"].strip() != nuevo.strip():
            lineas[b["inicio"]:b["fin"] + 1] = nuevo.split("\n")
            cambios.append(f"{b['ruta']}#{b['n']}")
    if cambios:
        escribir(readme, "\n".join(lineas))
    print(f"Actualizados {len(cambios)}: " + ", ".join(reversed(cambios)) if cambios else "Todos los diagramas del README ya coinciden con su fuente.")
    for e in errores:
        print("ERROR: " + e)
    sys.exit(1 if errores else 0)


def cmd_estado(args):
    problemas, n = estado(Path(args.raiz).resolve())
    if not problemas:
        print(f"Diagramas del README: {n}, todos coinciden con su fuente y tienen su texto." if n else "Diagramas del README: ninguno.")
        return
    print(f"Diagramas del README: {len(problemas)} problemas:")
    for p in problemas:
        print("  " + p)
    sys.exit(1)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    for nombre in ("listar", "sync", "estado"):
        sub.add_parser(nombre).add_argument("--raiz", default=".")
    pr = sub.add_parser("proponer")
    pr.add_argument("refs", nargs="*")
    pr.add_argument("--aplicar", action="store_true")
    pr.add_argument("--raiz", default=".")
    a = sub.add_parser("agregar")
    a.add_argument("diagrama")
    a.add_argument("--texto", default="")
    a.add_argument("--raiz", default=".")
    q = sub.add_parser("quitar")
    q.add_argument("diagrama")
    q.add_argument("--raiz", default=".")
    args = ap.parse_args()
    {"listar": cmd_listar, "proponer": cmd_proponer, "agregar": cmd_agregar, "quitar": cmd_quitar, "sync": cmd_sync, "estado": cmd_estado}[args.orden](args)


if __name__ == "__main__":
    main()
