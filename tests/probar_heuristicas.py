"""Heurísticas de `documentar-proyecto` (reglas de negocio candidatas): precisión y recall medidos contra un corpus etiquetado, con mínimos que no se pueden
bajar sin avisar. El corpus de desarrollo se usó para ajustar; el de RESERVA no (es la medida honesta). Detalle: `python tests/medir_heuristicas.py --reserva --detalle`."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(RAIZ / "tests"))
import medir_heuristicas as m  # noqa: E402
import corpus_heuristicas_reserva  # noqa: E402

an = m.an
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


_, dev = m.medir(m.CORPUS)
chequear(f"desarrollo: recall al menos 95 % ({dev['recall']:.0%})", dev["recall"] >= 0.95, dev)
chequear(f"desarrollo: precisión al menos 95 % ({dev['precision']:.0%})", dev["precision"] >= 0.95, dev)
_, res = m.medir(corpus_heuristicas_reserva.RESERVA)
chequear(f"reserva: recall al menos 85 % ({res['recall']:.0%})", res["recall"] >= 0.85, res)
chequear(f"reserva: precisión al menos 90 % ({res['precision']:.0%})", res["precision"] >= 0.90, res)

# palabras enteras: ni `age` dentro de PAGE ni `iva` dentro de private
chequear("`age` no coincide dentro de PAGE", not an.PALABRAS_DOMINIO.search(an.canonica("PAGE_SIZE = 20")))
chequear("`iva` no coincide dentro de private", not an.PALABRAS_DOMINIO.search(an.canonica("private_total = 4")) or an.PALABRAS_DOMINIO.search(an.canonica("private_total = 4")).group(0).startswith("total"))
chequear("el camelCase se separa (`totalPrice` ve `total` y `price`)", an.PALABRAS_DOMINIO.search(an.canonica("if totalPrice > 5:")) is not None)
chequear("el plural cuenta (`descuentos`)", an.PALABRAS_DOMINIO.search(an.canonica("descuentos = 3")) is not None)

# el ruido típico se descarta y la regla de verdad se conserva
for linea in ("if resp.status == 404:", "if i < 10:", "if version >= 3:", "PAGE_SIZE = 20", "TIMEOUT_SEGUNDOS = 30", "if (width > 768) {"):
    chequear(f"ruido descartado: {linea}", an.es_ruido(linea), linea)
for linea in ("if total > 10000:", "IVA = 21", "if edad < 18:"):
    chequear(f"regla conservada: {linea}", not an.es_ruido(linea), linea)

# cada candidata trae su confianza
base = RAIZ / ".temporal" / "proy-heuristicas-confianza"
(base / "src").mkdir(parents=True, exist_ok=True)
(base / "src" / "a.py").write_text("if total_descuento > 5000:\n    pass\nif x > 7:\n    pass\n", encoding="utf-8")
candidatas = an.reglas_candidatas(an.Proyecto(base))
chequear("cada candidata trae una confianza alta, media o baja", candidatas and all(c.get("confianza") in ("alta", "media", "baja") for c in candidatas), candidatas)
chequear("más palabras de dominio, más confianza", {c["texto"]: c["confianza"] for c in candidatas}.get("if total_descuento > 5000:") in ("alta", "media"), candidatas)

sys.exit(1 if mal else 0)
