#!/usr/bin/env python3
"""Mide la precisión y el recall de las reglas candidatas de `documentar-proyecto` contra el corpus etiquetado (`corpus_heuristicas.py`).

Uso: python tests/medir_heuristicas.py [--reserva] [--detalle]
Imprime, por tipo y en total, cuántas reglas verdaderas se encontraron (recall), cuántas de las propuestas eran de verdad reglas (precisión) y, con
--detalle, cada línea que falló. No es una prueba: la que hace cumplir los mínimos es `probar_heuristicas.py`.
"""
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "skills" / "documentar-proyecto" / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))
import analisis as an  # noqa: E402
import corpus_heuristicas  # noqa: E402
import corpus_heuristicas_reserva  # noqa: E402
CORPUS = corpus_heuristicas.CORPUS

EXT = {"py": "py", "php": "php", "js": "js"}


def medir(corpus=None):
    """Devuelve (resultados por línea, resumen). Cada línea del corpus va en su propio archivo para no mezclar contexto."""
    corpus = CORPUS if corpus is None else corpus
    base = RAIZ / ".temporal" / "proy-heuristicas"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    esperado = {}
    for i, (leng, linea, tipo) in enumerate(corpus):
        rel = f"src/c{i:03d}.{EXT[leng]}"
        (base / "src").mkdir(exist_ok=True)
        (base / rel).write_text(linea + "\n", encoding="utf-8")
        esperado[rel] = (linea, tipo)
    proyecto = an.Proyecto(base)
    propuestas = {}
    for c in an.reglas_candidatas(proyecto):
        propuestas.setdefault(c["rel"], []).append(c)
    filas, por_tipo = [], {}
    for rel, (linea, tipo) in esperado.items():
        prop = propuestas.get(rel, [])
        tipos = {c["tipo"] for c in prop}
        if tipo is not None:
            ok = tipo in tipos
            por_tipo.setdefault(tipo, [0, 0, 0])[0] += 1          # esperadas
            por_tipo[tipo][1] += 1 if ok else 0                   # encontradas
            filas.append(("falta" if not ok else "ok", rel, linea, tipo, sorted(tipos)))
        if prop:
            hubo_verdadera = tipo is not None and tipo in tipos
            for c in prop:
                por_tipo.setdefault(c["tipo"], [0, 0, 0])[2] += 1  # propuestas
            if tipo is None:
                filas.append(("ruido", rel, linea, None, sorted(tipos)))
            elif not hubo_verdadera:
                filas.append(("tipo-equivocado", rel, linea, tipo, sorted(tipos)))
    esperadas = sum(1 for _, _, t in corpus if t)
    encontradas = sum(1 for f in filas if f[0] == "ok")
    propuestas_total = sum(len(v) for v in propuestas.values())
    verdaderas = encontradas
    resumen = {"esperadas": esperadas, "encontradas": encontradas, "propuestas": propuestas_total, "verdaderas": verdaderas,
               "recall": encontradas / esperadas if esperadas else 0, "precision": verdaderas / propuestas_total if propuestas_total else 1,
               "ruido": sum(1 for f in filas if f[0] == "ruido"), "por_tipo": por_tipo}
    return filas, resumen


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    corpus = corpus_heuristicas_reserva.RESERVA if "--reserva" in sys.argv else CORPUS
    filas, r = medir(corpus)
    print("Corpus de " + ("RESERVA (no usado para ajustar)" if "--reserva" in sys.argv else "desarrollo (usado para ajustar)"))
    print(f"Corpus: {len(corpus)} líneas ({r['esperadas']} reglas verdaderas, {len(corpus) - r['esperadas']} de ruido).")
    print(f"Recall    {r['encontradas']}/{r['esperadas']} = {r['recall']:.0%}")
    print(f"Precisión {r['verdaderas']}/{r['propuestas']} = {r['precision']:.0%}  (líneas de ruido propuestas: {r['ruido']})")
    for t, (esp, enc, prop) in sorted(r["por_tipo"].items()):
        print(f"  {t:11} esperadas {esp:>2}, encontradas {enc:>2}, propuestas {prop:>2}")
    if "--detalle" in sys.argv:
        for estado, rel, linea, tipo, tipos in filas:
            if estado != "ok":
                print(f"  {estado:15} {linea!r}  esperado={tipo} propuesto={tipos}")


if __name__ == "__main__":
    main()
