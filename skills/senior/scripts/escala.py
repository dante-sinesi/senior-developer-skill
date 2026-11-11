#!/usr/bin/env python3
"""Escala del proyecto: cuánto rigor lleva el proyecto entero, decidido una vez con el usuario.

No es lo mismo que el tamaño de cada cambio (`verificar.py tamano`): la escala dice si el proyecto es una
herramienta personal, una aplicación con usuarios o un sistema grande de largo plazo, y con eso se fija el piso
de método desde el primer día (arquitectura antes de código, requisitos, seguridad, tests).

Uso:
    python escala.py niveles [--nivel pequeño|mediano|grande]   # qué incluye cada nivel (para mostrárselo al usuario)
    python escala.py estado [--raiz .]                          # nivel, lo que falta; si el proyecto creció, lo sube solo
    python escala.py evolucionar [--raiz .]                     # sube la escala si el tamaño ya corresponde a un nivel mayor
    python escala.py fijar <nivel> [--raiz .]                   # escribe «Escala del proyecto» en docs/ESTADO.md

La skill pregunta la escala UNA SOLA VEZ, al empezar en un proyecto sin nivel declarado (ver `senior` y
`adoptar-proyecto`): muestra los niveles, el usuario elige y se registra con `fijar`. Después no vuelve a preguntar:
si el proyecto crece, la escala sube sola (`evolucionar`, que también corre `estado`) y se informa en una línea.
Nunca baja por su cuenta y lo que falta del nivel nuevo es una guía, no un bloqueo. El usuario puede fijar otro
nivel cuando quiera. Solo biblioteca estándar.
"""
import argparse
import datetime
import os
import re
import sys
from pathlib import Path

NIVELES = ["pequeño", "mediano", "grande"]
IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".idea", ".vscode",
           "coverage", ".next", ".temporal", "docs", "documentos-externos"}
EXT_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".kt", ".cs", ".go", ".rs", ".rb", ".c", ".cc", ".cpp",
              ".h", ".hpp", ".swift", ".lua", ".sql", ".sh", ".vue"}
RE_ESCALA = re.compile(r"^\*\*Escala del proyecto:\*\*[ \t]*(.*)$", re.M)

DESCRIPCION = {
    "pequeño": ("Pequeño", "una herramienta personal, un script, un prototipo o algo de vida corta, con una sola persona."),
    "mediano": ("Mediano", "una aplicación con usuarios reales, un equipo chico o una vida de meses."),
    "grande": ("Grande", "un sistema de largo plazo, con varias personas o módulos, dinero, datos sensibles o integraciones críticas."),
}

# Lo que suma cada nivel, por área. Cada nivel incluye todo lo del anterior.
INCLUYE = {
    "pequeño": [
        ("Tests", "tests primero para las reglas importantes; lo trivial sin test nuevo"),
        ("Documentación", "README al día y `docs/ESTADO.md` corto; sin fichas salvo cambios grandes"),
        ("Arquitectura", "se respeta la estructura que ya haya; sin ADR ni diagramas obligatorios"),
        ("Seguridad", "modo liviano: la lista de revisión y los chequeos automáticos"),
        ("Git", "una rama por cambio, commits atómicos y PR breve"),
    ],
    "mediano": [
        ("Requisitos", "reglas de negocio con ejemplos con valores concretos (RN), de donde salen los tests; el resto a medida"),
        ("Arquitectura", "un ADR por decisión que importa (stack, base de datos, autenticación); diagrama cuando un cambio cruza capas"),
        ("Documentación", "`docs/` completa: estado, fichas de cambio desde el nivel mediano, pendientes y deuda técnica"),
        ("Revisión", "`/revisar-cambio` antes de cada PR; la guardia de listones vigila que no se aflojen controles"),
        ("Tests", "suite que corre sola, contra una base de prueba separada"),
        ("Estilo", "si hay interfaz, tarjeta de estilo viva antes de las pantallas (tres alternativas A, B y C), recomendada"),
    ],
    "grande": [
        ("Arquitectura primero", "antes del primer código, un ADR de capas, límites entre módulos y estructura, con diagramas de clases y de entidad-relación"),
        ("Requisitos", "los siete tipos (negocio, usuario, dominio, funcional, no funcional, transición, interfaces) y trazabilidad requisito → test → código"),
        ("Seguridad", "modo formal: registro de riesgos (`docs/seguridad/riesgos.md`) y requisitos de seguridad escritos antes de construir"),
        ("Calidad", "cobertura mínima de tests fijada desde el comienzo y vigilada; `verificar.py` completo en cada PR"),
        ("Decisiones", "duda con contexto fresco en las decisiones de arquitectura y en todo lo difícil de revertir (base de datos, interfaces públicas)"),
        ("Estilo", "la tarjeta de estilo es obligatoria si hay interfaz y se mantiene al día con cada componente nuevo"),
        ("Planificación", "plan acordado con el usuario antes de cada cambio grande; deuda técnica revisada en cada hito"),
        ("Costo", "es más lento a propósito: se avisa antes de elegirlo"),
    ],
}


def texto_niveles(solo=None):
    lineas = []
    for n in NIVELES:
        nombre, para = DESCRIPCION[n]
        if solo and n != solo:
            continue
        lineas.append(f"{nombre}: {para}")
        if n != "pequeño":
            lineas.append("  Incluye todo lo del nivel anterior y además:")
        for area, detalle in INCLUYE[n]:
            lineas.append(f"  - {area}: {detalle}.")
        lineas.append("")
    return "\n".join(lineas).rstrip()


def declarada(raiz):
    """Nivel escrito en docs/ESTADO.md, o None."""
    estado = Path(raiz) / "docs" / "ESTADO.md"
    if not estado.exists():
        return None
    m = RE_ESCALA.search(estado.read_text(encoding="utf-8-sig", errors="replace"))
    if not m:
        return None
    valor = m.group(1).strip().lower().replace("pequeno", "pequeño")
    for n in NIVELES:
        if valor.startswith(n):
            return n
    return None


def subio_sola(raiz):
    """True si el nivel escrito en ESTADO.md lo subió la skill por el tamaño y no lo eligió el usuario."""
    estado = Path(raiz) / "docs" / "ESTADO.md"
    if not estado.exists():
        return False
    m = RE_ESCALA.search(estado.read_text(encoding="utf-8-sig", errors="replace"))
    return bool(m and "subió sola" in m.group(1).lower())


def medir(raiz):
    """(archivos de código, hay tests) sin contar docs ni dependencias."""
    codigo, tests = 0, False
    for actual, carpetas, nombres in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR]
        for n in nombres:
            if Path(n).suffix.lower() in EXT_CODIGO:
                codigo += 1
                if "test" in n.lower() or "spec" in n.lower() or "test" in Path(actual).name.lower():
                    tests = True
    return codigo, tests


def sugerir(codigo):
    """Nivel que sugiere el tamaño del código; es un indicio, la decisión es del usuario."""
    return "pequeño" if codigo < 20 else "mediano" if codigo < 150 else "grande"


EXT_INTERFAZ = {".html", ".htm", ".css", ".vue", ".svelte", ".jsx", ".tsx", ".tscn", ".xaml", ".storyboard", ".kv"}


def hay_interfaz(raiz):
    """True si el proyecto tiene interfaz: páginas, hojas de estilo, componentes o un proyecto de Godot."""
    if (Path(raiz) / "project.godot").exists():
        return True
    for actual, carpetas, nombres in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR]
        if any(Path(n).suffix.lower() in EXT_INTERFAZ for n in nombres):
            return True
    return False


def hay(raiz, patron_carpeta, ext=".md"):
    base = Path(raiz) / patron_carpeta
    return base.is_dir() and any(f.suffix == ext for f in base.rglob("*") if f.is_file() and f.name.lower() != "readme.md")


def umbral_de_cobertura(raiz):
    patron = re.compile(r"fail_under|fail-under|cov-fail-under|coverageThreshold|coverage_threshold|minimum_coverage|--coverage-min|threshold\s*[:=]", re.I)
    for nombre in ("pyproject.toml", ".coveragerc", "setup.cfg", "tox.ini", "package.json", "jest.config.js", "jest.config.ts",
                   "vitest.config.ts", "vitest.config.js", "phpunit.xml", "phpunit.xml.dist", "codecov.yml", ".codecov.yml"):
        f = Path(raiz) / nombre
        if f.exists() and patron.search(f.read_text(encoding="utf-8", errors="replace")):
            return True
    return False


def faltantes(raiz, nivel):
    """Lo que el nivel declarado exige y todavía no está."""
    falta = []
    codigo, tests = medir(raiz)
    if nivel in ("mediano", "grande"):
        if not any((Path(raiz) / n).exists() for n in ("README.md", "readme.md", "Readme.md")):
            falta.append("README.md")
        if codigo and not tests:
            falta.append("tests (hay código y ninguna prueba)")
    if nivel == "grande":
        if not hay(raiz, "docs/decisiones"):
            falta.append("ADR de arquitectura en docs/decisiones/")
        if not hay(raiz, "docs/diagramas"):
            falta.append("diagramas base (clases, entidad-relación) en docs/diagramas/")
        if not hay(raiz, "docs/requisitos"):
            falta.append("requisitos en docs/requisitos/")
        if not (Path(raiz) / "docs" / "seguridad" / "riesgos.md").exists():
            falta.append("registro de riesgos en docs/seguridad/riesgos.md")
        if not umbral_de_cobertura(raiz):
            falta.append("umbral de cobertura de tests configurado")
        estilo = Path(raiz) / "docs" / "diseno" / "estilo"
        if hay_interfaz(raiz) and not ((estilo / "tarjeta.html").exists() or (estilo / "tarjeta.md").exists()):
            falta.append("tarjeta de estilo en docs/diseno/estilo/ (el proyecto tiene interfaz)")
    return falta


def evaluar(raiz):
    """(líneas, ok) para verificar.py. Sin docs/ no dice nada: el proyecto todavía no adoptó la metodología."""
    raiz = Path(raiz)
    if not (raiz / "docs" / "ESTADO.md").exists():
        return [], True
    nivel = declarada(raiz)
    codigo, _ = medir(raiz)
    if not nivel:
        return ["Escala: sin declarar. Preguntarle al usuario (`escala.py niveles` muestra qué incluye cada nivel) y registrarla "
                "con `escala.py fijar <nivel>`."], False
    lineas, ok = [], True
    sug = sugerir(codigo)
    efectivo = sug if NIVELES.index(sug) > NIVELES.index(nivel) else nivel
    # un nivel que eligió el usuario se exige; uno al que el proyecto llegó creciendo es una guía, nunca un bloqueo
    guia = efectivo != nivel or subio_sola(raiz)
    falta = faltantes(raiz, efectivo)
    if falta:
        ok = guia
        lineas.append((f"Escala {efectivo} (el proyecto creció): para ese nivel todavía falta, como guía: " if guia else f"Escala {efectivo}: faltan ")
                      + "; ".join(falta) + ".")
    else:
        lineas.append(f"Escala {efectivo}: lo que exige el nivel está.")
    if efectivo != nivel:
        lineas.append(f"  El tamaño del código ({codigo} archivos) ya corresponde al nivel {efectivo}; `escala.py evolucionar` lo registra, sin preguntar.")
    return lineas, ok


def fijar(raiz, nivel, nota="", imprimir=True):
    estado = Path(raiz) / "docs" / "ESTADO.md"
    if not estado.exists():
        sys.exit("No existe docs/ESTADO.md: primero se adopta el proyecto (/adoptar-proyecto).")
    texto = estado.read_text(encoding="utf-8-sig", errors="replace")
    linea = f"**Escala del proyecto:** {nivel}" + (f" ({nota})" if nota else "")
    if RE_ESCALA.search(texto):
        texto = RE_ESCALA.sub(linea, texto, count=1)
    elif re.search(r"^\*\*Última actualización:\*\*.*$", texto, re.M):
        texto = re.sub(r"^(\*\*Última actualización:\*\*.*)$", r"\1\n\n" + linea, texto, count=1, flags=re.M)
    else:
        partes = texto.split("\n", 1)
        texto = partes[0] + "\n\n" + linea + "\n" + (partes[1] if len(partes) > 1 else "")
    estado.write_text(texto, encoding="utf-8", newline="\n")
    if imprimir:
        print(f"Escala del proyecto: {nivel} (registrada en docs/ESTADO.md).")


def evolucionar(raiz):
    """Sube la escala si el tamaño del proyecto ya corresponde a un nivel mayor. Sin preguntar y sin bajar nunca.

    Devuelve el mensaje informativo, o "" si no hizo falta cambiar nada."""
    actual = declarada(raiz)
    if not actual:
        return ""
    codigo, _ = medir(raiz)
    nuevo = sugerir(codigo)
    if NIVELES.index(nuevo) <= NIVELES.index(actual):
        return ""
    fijar(raiz, nuevo, f"subió sola desde {actual} el {datetime.date.today().isoformat()} por el tamaño del código: {codigo} archivos", imprimir=False)
    falta = faltantes(raiz, nuevo)
    return (f"El proyecto creció ({codigo} archivos de código): la escala subió de {actual} a {nuevo} sin preguntar. "
            + ("Lo que el nivel nuevo suma y todavía no está, como guía: " + "; ".join(falta) + "." if falta else "El proyecto ya tiene lo que el nivel nuevo pide."))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    n = sub.add_parser("niveles")
    n.add_argument("--nivel", choices=NIVELES)
    e = sub.add_parser("estado")
    e.add_argument("--raiz", default=".")
    v = sub.add_parser("evolucionar")
    v.add_argument("--raiz", default=".")
    f = sub.add_parser("fijar")
    f.add_argument("nivel", choices=NIVELES)
    f.add_argument("--raiz", default=".")
    args = ap.parse_args()
    if args.orden == "niveles":
        print(texto_niveles(args.nivel))
    elif args.orden == "fijar":
        fijar(args.raiz, args.nivel)
    elif args.orden == "evolucionar":
        print(evolucionar(args.raiz) or "Escala: no hace falta cambiarla.")
    else:
        aviso = evolucionar(args.raiz)
        if aviso:
            print(aviso)
        lineas, ok = evaluar(args.raiz)
        print("\n".join(lineas) if lineas else "Escala: el proyecto todavía no tiene docs/ (se adopta con /adoptar-proyecto).")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
