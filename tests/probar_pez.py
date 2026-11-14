"""El pez: revisor a ciegas de planes no simples (con un CLI de Claude simulado, sin gastar nada)."""
import io
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "senior" / "scripts" / "pez.py"
sys.path.insert(0, str(SCRIPT.parent))
import pez  # noqa: E402

P = RAIZ / ".temporal" / "proy-pez"
mal = 0


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


def correr(*args, env=None):
    e = {**os.environ, **(env or {})}
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=e, cwd=RAIZ)
    return r.returncode, r.stdout + r.stderr


if P.exists():
    shutil.rmtree(P, onerror=_forzar)
P.mkdir(parents=True)

PLAN = """# Plan: migrar los recibos

## Contexto
Hay 8 000 recibos por día y un cron los envía.

## Decisiones ya tomadas (no reabrir)
- La cola es la que ya opera la empresa.

## Pasos
1. Crear el trabajador.
2. Apagar el cron.

## Qué pasa si falla
Se reactiva el cron.

## Terminado cuando
Siete días sin duplicados.
"""
(P / "plan.md").write_text(PLAN, encoding="utf-8")
(P / "incompleto.md").write_text("# Plan\n\n## Pasos\n1. Hacer algo.\n", encoding="utf-8")

# ---- validar
rc, s = correr("validar", str(P / "plan.md"))
chequear("un plan con sus secciones es válido", rc == 0 and "Plan válido" in s, s)
rc, s = correr("validar", str(P / "incompleto.md"))
chequear("un plan que no se basta solo dice qué le falta", rc == 1 and "Contexto" in s and "Decisiones ya tomadas" in s and "Terminado cuando" in s, s)
chequear("sin «Qué pasa si falla» solo avisa", pez.validar_plan(PLAN.replace("## Qué pasa si falla\nSe reactiva el cron.\n\n", ""))[0] == []
         and any("Qué pasa si falla" in a for a in pez.validar_plan(PLAN.replace("## Qué pasa si falla\nSe reactiva el cron.\n\n", ""))[1]))
chequear("un plan larguísimo avisa que conviene dividirlo", any("dividirlo" in a for a in pez.validar_plan(PLAN + "palabra " * 3000)[1]))

# ---- pedir: el pedido lleva el plan y las reglas, y nada de la sesión
rc, s = correr("pedir", str(P / "plan.md"))
chequear("el pedido lleva el plan, la regla del caso concreto, lo que no se discute y el formato JSON", rc == 0 and "migrar los recibos" in s and "CASO CONCRETO" in s and "no se discute" in s and '"veredicto"' in s, s[:200])

# ---- decidir
for args, codigo, texto in ((["pasa"], 0, "SEGUIR"), (["corregir"], 0, "SEGUIR"), (["bloquea"], 0, "REPETIR"), (["bloquea", "corregir"], 0, "SEGUIR"),
                            (["bloquea", "bloquea"], 1, "ESCALAR"), (["bloquea", "pasa"], 0, "SEGUIR"), (["raro"], 2, "desconocido")):
    rc, s = correr("decidir", *args)
    chequear(f"decidir {' '.join(args)} → {texto}", rc == codigo and texto in s, s)

# ---- extraer el JSON de una respuesta con vallas o con texto alrededor
chequear("se extrae el JSON aunque venga con vallas de código", pez.extraer_json('```json\n{"veredicto": "pasa", "hallazgos": []}\n```')["veredicto"] == "pasa")
chequear("y aunque el modelo agregue texto alrededor", pez.extraer_json('Acá va: {"veredicto": "corregir", "x": {"y": 1}} listo')["x"]["y"] == 1)
chequear("una respuesta que no es JSON da None", pez.extraer_json("no sé") is None)

# ---- revisar con un CLI de Claude simulado
FALSO = P / "claude_falso.py"
FALSO.write_text('''import json, os, sys
open(os.environ["PEZ_ARGS"], "w", encoding="utf-8").write(json.dumps(sys.argv[1:]))
j = {"veredicto": os.environ.get("PEZ_VEREDICTO", "corregir"), "puntaje": 6, "resumen": "Falta la vuelta atrás.",
     "hallazgos": [{"severidad": "baja", "paso": "2", "caso": "detalle", "arreglo": "x"}, {"severidad": "alta", "paso": "1", "caso": "El trabajador cae y se duplica el recibo", "arreglo": "idempotencia"}]}
print(json.dumps({"result": "```json\\n" + json.dumps(j) + "\\n```", "total_cost_usd": 0.031, "is_error": False}))
''', encoding="utf-8")
ARGS = P / "args.json"
env = {"SENIOR_CLAUDE": str(FALSO), "PEZ_ARGS": str(ARGS)}
rc, s = correr("revisar", str(P / "plan.md"), "--salida", str(P / "salida"), env=env)
llamada = json.loads(ARGS.read_text(encoding="utf-8")) if ARGS.exists() else []
chequear("revisar muestra el veredicto, el puntaje y los hallazgos con la alta primero", rc == 0 and "veredicto «corregir»" in s and "6/10" in s and s.index("[alta]") < s.index("[baja]"), s)
chequear("el resumen manda a registrar cada decisión y a correr decidir", "Registro de revisión" in s and "pez.py decidir" in s)
chequear("guarda la respuesta de la ronda 1", (P / "salida" / "plan-pez-1.json").exists() and json.loads((P / "salida" / "plan-pez-1.json").read_text(encoding="utf-8"))["ronda"] == 1)
chequear("el revisor corre sin herramientas, sin skills ni configuración del proyecto y con un sistema propio",
         "--tools" in llamada and llamada[llamada.index("--tools") + 1] == "" and "--disable-slash-commands" in llamada and "--setting-sources" in llamada
         and "--system-prompt" in llamada and "--no-session-persistence" in llamada, llamada)
chequear("el pedido que recibe lleva solo el plan: nada de la sesión", "migrar los recibos" in llamada[llamada.index("-p") + 1] and "Siete días sin duplicados" in llamada[llamada.index("-p") + 1])
rc, s = correr("revisar", str(P / "plan.md"), "--salida", str(P / "salida"), env={**env, "PEZ_VEREDICTO": "bloquea"})
chequear("la segunda revisión se guarda como ronda 2", rc == 0 and "ronda 2" in s and (P / "salida" / "plan-pez-2.json").exists(), s)
rc, s = correr("revisar", str(P / "incompleto.md"), "--salida", str(P / "salida"), env=env)
chequear("no se revisa un plan que no se basta solo", rc == 1 and "no se basta solo" in s, s)
rc, s = correr("revisar", str(P / "plan.md"), "--salida", str(P / "salida"), env={"SENIOR_CLAUDE": str(P / "no_existe.py"), "PEZ_ARGS": str(ARGS)})
chequear("si el CLI falla, lo dice con código 3", rc == 3, s)
chequear("el CLI se busca en SENIOR_CLAUDE, en el PATH y en la copia de la aplicación de escritorio", all(x in SCRIPT.read_text(encoding="utf-8") for x in ("SENIOR_CLAUDE", "shutil.which", "Claude-Data")))

# ---- está explicado y cableado
ref = (RAIZ / "skills" / "senior" / "references" / "plan-pez.md").read_text(encoding="utf-8")
nucleo = (RAIZ / "skills" / "senior" / "SKILL.md").read_text(encoding="utf-8")
chequear("el núcleo manda a revisar los planes no simples con el pez", "plan no simple" in nucleo and "references/plan-pez.md" in nucleo)
chequear("la referencia explica cuándo, cómo, el corte y lo medido, y que los tres peces se descartaron",
         all(x in ref for x in ("## Cuándo", "## Cómo", "pez.py decidir", "## Qué se midió", "se descartaron", "Registro de revisión")))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
