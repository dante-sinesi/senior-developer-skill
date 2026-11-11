#!/usr/bin/env python3
"""Guardia de listones: avisa cuando un cambio afloja los controles de calidad para que "pase" en verde.

El riesgo: quien escribe el código también puede escribir el test, el umbral o la excepción que lo deja pasar.
Esta guardia mira el diff y marca las cinco formas habituales de aflojar el listón, sin gastar tokens:

  1. umbrales movidos      cobertura mínima, largo de línea o complejidad máximos, `strict` apagado,
                           `continue-on-error`, `|| true`, `--exit-zero`
  2. tests más fáciles     tests salteados o marcados como fallo esperado, archivos de test borrados,
                           asserts que desaparecen
  3. chequeos silenciados  `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `# nosec`, `pragma: no cover`,
                           `phpcs:ignore` y parecidos, y líneas nuevas en archivos de exclusión
  4. trabajo a medias      `NotImplementedError`, `throw new Error("not implemented")`, `except: pass`,
                           `catch {}` vacío, `TODO`/`FIXME` nuevos
  5. excepciones nuevas    `atajo:` nuevos (ver atajos.py)

Endurecer el listón es silencioso; aflojarlo es ruidoso. Solo se informa lo que afloja.

Cómo se aprueba una excepción: se escribe por qué, en la misma línea o en la anterior, con `motivo: …`
(o `senior-ignore: LIS-ID`). Queda contada como justificada y no como aviso. Sin motivo, no pasa.

Uso:
    python guardia_listones.py [--raiz .] [--base HEAD] [--max 20]
`--base` es contra qué se compara (por defecto los cambios sin guardar; en una rama, `--base main`).
Código de salida: 0 sin avisos, 1 con avisos. Solo biblioteca estándar.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

PATRON_TEST = re.compile(r"(^|/)(tests?|spec|__tests__|e2e)/|(^|/)(test_[^/]*|[^/]*_test\.[a-z]+|[^/]*\.(test|spec)\.[a-z]+|[^/]*Test\.[a-z]+)$", re.I)
CONFIG = re.compile(r"(\.toml|\.cfg|\.ini|\.ya?ml|\.json|\.jsonc|\.xml|\.neon|\.dist|rc|\.config\.[cm]?[jt]s|Makefile|\.sh|Dockerfile)$|(^|/)(\.flake8|\.coveragerc|\.eslintrc[^/]*|\.pylintrc|tox\.ini|setup\.cfg|pyproject\.toml|package\.json|phpunit\.xml[^/]*|phpstan\.neon|tsconfig[^/]*\.json|jest\.config\.[^/]*|\.github/workflows/[^/]+)$", re.I)
ARCHIVOS_EXCLUSION = re.compile(r"(^|/)(\.eslintignore|\.gitleaksignore|\.semgrepignore|\.prettierignore|\.dockerignore|\.snyk|\.trivyignore|\.bandit)$", re.I)

# (id, mensaje, patrón sobre la línea agregada)
SILENCIADOS = [
    ("LIS-SILENCIO", "supresión nueva de un chequeo",
     re.compile(r"#\s*noqa\b|#\s*type:\s*ignore|#\s*pylint:\s*disable|#\s*nosec\b|#\s*pragma:\s*no cover|#\s*fmt:\s*off|#\s*skipcq|"
                r"eslint-disable|@ts-ignore|@ts-nocheck|@ts-expect-error|//\s*nolint|//\s*NOSONAR|#\[allow\(|@SuppressWarnings|"
                r"phpcs:ignore|phpcs:disable|@phpstan-ignore|istanbul ignore|c8 ignore|@codeCoverageIgnore|# rubocop:disable|//\s*lgtm|"
                r"# semgrep|nosemgrep|gitleaks:allow")),
]
SALTADOS = ("LIS-TEST-SALTADO", "test salteado o marcado como fallo esperado",
            re.compile(r"@pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\(|@unittest\.(skip|expectedFailure)|\.skipTest\(|"
                       r"\b(xit|xdescribe|xtest)\(|\b(it|test|describe)\.(skip|todo)\(|t\.Skip\(|markTestSkipped|markTestIncomplete|"
                       r"@Disabled|@Ignore\b|#\[ignore\]|\[Ignore\]|@Test\(enabled\s*=\s*false"))
SOLO_FLOJO = [
    ("LIS-CONFIG-FLOJA", "chequeo que ya no bloquea",
     re.compile(r"continue-on-error:\s*true|\|\|\s*true\b|--exit-zero|--no-verify|--passWithNoTests|--allow-empty|ignore[-_]errors\s*[=:]\s*true|"
                r"\"?strict\"?\s*[=:]\s*false|noImplicitAny\"?\s*[=:]\s*false|--no-strict|failOnWarning\"?\s*[=:]\s*false|set \+e\b")),
]
MEDIOS = [
    ("LIS-A-MEDIAS", "implementación a medias",
     re.compile(r"raise NotImplementedError|throw new Error\(\s*[\"'](not implemented|no implementado|todo)|unimplemented!\(|todo!\(|"
                r"panic\(\s*\"(not implemented|todo)|\bpass\s*#\s*(TODO|FIXME)|except[^:\n]*:\s*pass\b|catch\s*(\([^)]*\))?\s*\{\s*\}")),
    ("LIS-PENDIENTE", "TODO/FIXME/HACK nuevo", re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")),
]
ATAJO = ("LIS-EXCEPCION", "atajo nuevo (excepción a la regla general)", re.compile(r"\batajo:"))
ASSERT = re.compile(r"\bassert\w*\b|\bexpect\(|\.should\b|\bself\.assert|\bt\.(Error|Fatal)f?\(|\bAssert\.")
# umbrales numéricos: clave → "min" (bajar afloja) o "max" (subir afloja)
UMBRALES = {
    "fail_under": "min", "fail-under": "min", "cov-fail-under": "min", "coverage_threshold": "min", "minimum_coverage": "min",
    "coveragethreshold": "min", "branches": "min", "statements": "min", "lines": "min", "functions": "min", "threshold": "min",
    "max-line-length": "max", "max_line_length": "max", "line-length": "max", "max-complexity": "max", "max_complexity": "max",
    "max-warnings": "max", "maxwarnings": "max", "max-lines": "max", "max-params": "max", "max-depth": "max", "maxfilesize": "max",
}
NUM = re.compile(r"([A-Za-z_][\w-]*)\"?\s*[:=]\s*\"?(-?\d+(?:\.\d+)?)|--([a-z-]+)[= ](\d+(?:\.\d+)?)")
DOCUMENTOS = (".md", ".txt", ".rst", ".adoc")
JUSTIFICADO = re.compile(r"motivo:|senior-ignore:\s*LIS-", re.I)


def git(raiz, *args):
    try:
        p = subprocess.run(["git", *args], cwd=raiz, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        return p.stdout, p.returncode
    except (OSError, subprocess.TimeoutExpired):
        return "", -1


def leer_diff(raiz, base):
    """[{archivo, estado, agregadas:[(n, texto, anterior)], quitadas:[texto]}] de los cambios respecto de `base`."""
    salida, rc = git(raiz, "diff", "--unified=0", "--no-color", "--no-ext-diff", base)
    archivos, actual, nuevo_n, previa = [], None, 0, ""
    for linea in salida.splitlines():
        if linea.startswith("diff --git"):
            actual = {"archivo": "", "estado": "M", "agregadas": [], "quitadas": []}
            archivos.append(actual)
        elif actual is None:
            continue
        elif linea.startswith("deleted file mode"):
            actual["estado"] = "D"
        elif linea.startswith("+++ "):
            ruta = linea[4:]
            if ruta != "/dev/null":
                actual["archivo"] = ruta[2:] if ruta.startswith("b/") else ruta
        elif linea.startswith("--- "):
            if not actual["archivo"]:
                actual["archivo"] = linea[6:] if linea.startswith("--- a/") else ""
        elif linea.startswith("@@"):
            m = re.search(r"\+(\d+)", linea)
            nuevo_n = int(m.group(1)) if m else 0
            previa = ""
        elif linea.startswith("+") and not linea.startswith("+++"):
            actual["agregadas"].append((nuevo_n, linea[1:], previa))
            previa = linea[1:]
            nuevo_n += 1
        elif linea.startswith("-") and not linea.startswith("---"):
            actual["quitadas"].append(linea[1:])
    nuevos, _ = git(raiz, "ls-files", "--others", "--exclude-standard")
    for ruta in nuevos.splitlines():
        try:
            texto = (Path(raiz) / ruta).read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue
        previa, agregadas = "", []
        for i, l in enumerate(texto.splitlines(), 1):
            agregadas.append((i, l, previa))
            previa = l
        archivos.append({"archivo": ruta, "estado": "A", "agregadas": agregadas, "quitadas": []})
    return archivos


def numeros(linea):
    """{clave: número} de lo que parece un umbral en la línea."""
    out = {}
    for m in NUM.finditer(linea):
        clave = (m.group(1) or m.group(3) or "").lower()
        valor = m.group(2) or m.group(4)
        if clave in UMBRALES and valor is not None:
            out[clave] = float(valor)
    return out


def analizar(archivos):
    """Devuelve (hallazgos, justificados). Cada hallazgo: (id, mensaje, archivo, línea, texto)."""
    hallazgos, justificados = [], 0

    def agregar(ident, msg, archivo, n, texto, previa=""):
        nonlocal justificados
        if JUSTIFICADO.search(texto) or JUSTIFICADO.search(previa):
            justificados += 1
        else:
            hallazgos.append((ident, msg, archivo, n, texto.strip()[:90]))

    for a in archivos:
        ruta = a["archivo"].replace("\\", "/")
        es_test = bool(PATRON_TEST.search(ruta))
        es_config = bool(CONFIG.search(ruta))
        if a["estado"] == "D" and es_test:
            hallazgos.append(("LIS-TEST-BORRADO", "archivo de test borrado", ruta, 0, "sin motivo escrito: confirmar que la regla ya no existe"))
        if ruta.lower().endswith(DOCUMENTOS) or ruta.endswith("guardia_listones.py"):
            continue  # la documentación y esta guardia nombran los patrones sin usarlos
        for n, texto, previa in a["agregadas"]:
            if ARCHIVOS_EXCLUSION.search(ruta) and texto.strip() and not texto.strip().startswith("#"):
                agregar("LIS-EXCLUSION", "exclusión nueva de un chequeo", ruta, n, texto, previa)
            if es_test:
                if SALTADOS[2].search(texto):
                    agregar(SALTADOS[0], SALTADOS[1], ruta, n, texto, previa)
            for ident, msg, pat in SILENCIADOS:
                if pat.search(texto):
                    agregar(ident, msg, ruta, n, texto, previa)
            if es_config or ruta.endswith(".sh"):
                for ident, msg, pat in SOLO_FLOJO:
                    if pat.search(texto):
                        agregar(ident, msg, ruta, n, texto, previa)
            for ident, msg, pat in MEDIOS:
                if pat.search(texto) and not (es_test and ident == "LIS-PENDIENTE"):
                    agregar(ident, msg, ruta, n, texto, previa)
            if ATAJO[2].search(texto):
                agregar(ATAJO[0], ATAJO[1], ruta, n, texto, previa)
        # umbrales: valor que cambia en el sentido que afloja
        if es_config and a["quitadas"] and a["agregadas"]:
            antes = {}
            for t in a["quitadas"]:
                antes.update(numeros(t))
            for n, texto, previa in a["agregadas"]:
                for clave, valor in numeros(texto).items():
                    if clave in antes:
                        v0 = antes[clave]
                        sentido = UMBRALES[clave]
                        if (sentido == "min" and valor < v0) or (sentido == "max" and valor > v0):
                            agregar("LIS-UMBRAL", f"umbral aflojado ({clave}: {v0:g} → {valor:g})", ruta, n, texto, previa)
        # asserts que desaparecen de un test sin que aparezcan otros
        if es_test and a["estado"] != "D":
            quitados = sum(1 for t in a["quitadas"] if ASSERT.search(t))
            puestos = sum(1 for _, t, _ in a["agregadas"] if ASSERT.search(t))
            if quitados > puestos:
                hallazgos.append(("LIS-ASSERT-MENOS", f"el test tiene {quitados - puestos} verificación(es) menos", ruta, 0,
                                  "confirmar que la regla sigue verificada"))
    return hallazgos, justificados


def informe(hallazgos, justificados, maximo=20):
    """Líneas del informe; vacío de avisos cuando todo está en orden."""
    if not hallazgos:
        extra = f" ({justificados} excepción(es) con motivo escrito)" if justificados else ""
        return [f"Listones: sin controles aflojados{extra}."]
    lineas = [f"Listones: {len(hallazgos)} cambio(s) aflojan un control" +
              (f" y {justificados} tienen motivo escrito" if justificados else "") +
              ". Cada uno se corrige, o se justifica con `motivo: …` en la misma línea o la anterior:"]
    for ident, msg, archivo, n, texto in hallazgos[:maximo]:
        lineas.append(f"  [{ident}] {archivo}{':' + str(n) if n else ''} — {msg}" + (f": {texto}" if texto else ""))
    if len(hallazgos) > maximo:
        lineas.append(f"  … y {len(hallazgos) - maximo} más (--max para ver más).")
    return lineas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--max", type=int, default=20)
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if git(raiz, "rev-parse", "--is-inside-work-tree")[0].strip() != "true":
        print("Listones: la carpeta no es un repositorio git (se omite).")
        return
    hallazgos, justificados = analizar(leer_diff(raiz, args.base))
    print("\n".join(informe(hallazgos, justificados, args.max)))
    sys.exit(1 if hallazgos else 0)


if __name__ == "__main__":
    main()
