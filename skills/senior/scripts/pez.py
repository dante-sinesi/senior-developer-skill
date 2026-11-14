#!/usr/bin/env python3
"""El pez: un revisor a ciegas para planes no simples. Recibe SOLO el .md del plan (no conoce la sesión ni el proyecto), busca fallas y devuelve un veredicto.

Un plan largo escrito después de una sesión larga arrastra suposiciones que ya no se ven. Antes de ejecutarlo, un revisor sin contexto intenta romperlo (método en
`references/plan-pez.md`). Este script hace lo que no necesita criterio:

  validar  Comprueba que el plan se baste solo: Contexto, Decisiones ya tomadas, Pasos y Terminado cuando (y avisa si falta «Qué pasa si falla»).
  pedir    Imprime el pedido completo para el revisor (por si no hay CLI de Claude y se lo pasa a un subagente).
  revisar  Corre al pez en una sesión nueva de `claude -p`: sin herramientas, sin skills ni configuración del proyecto, solo con el plan. Guarda la respuesta y
           muestra un resumen corto: veredicto, puntaje y los hallazgos por severidad.
  decidir  Dado el veredicto de cada ronda, dice qué sigue: ejecutar, repetir la revisión o plantearle el problema al usuario.

Uso:
    python pez.py validar <plan.md>
    python pez.py pedir <plan.md>
    python pez.py revisar <plan.md> [--salida .temporal/planes] [--max-usd 1]
    python pez.py decidir bloquea corregir ...            (un veredicto por ronda, en orden)

Veredictos: «bloquea» (no se ejecuta sin corregir), «corregir» (se ejecuta tras cambios acotados), «pasa». Un plan bueno suele recibir «corregir», no «pasa».
Salida de `decidir`: 0 si se puede seguir o repetir, 1 si hay que hablar con el usuario. `revisar` sale con 2 si no encuentra el CLI de Claude
(variable SENIOR_CLAUDE, `claude` en el PATH o la copia de la aplicación de escritorio) y con 3 si la respuesta no es el JSON pedido. Solo biblioteca estándar.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

SISTEMA = "Sos un revisor de planes de trabajo. Respondés solo con el JSON pedido, sin texto antes ni después."

PEDIDO = """Recibís un plan de trabajo en Markdown. No tenés ninguna otra información: no conocés a quien lo escribió, ni la conversación donde nació, ni el proyecto. \
Tu trabajo es hallar fallas que harían fracasar el plan o causarían un daño si se ejecutara tal cual.

Reglas:
- Cada hallazgo lleva un CASO CONCRETO (qué pasa, en qué paso, con qué consecuencia) y el arreglo mínimo. Sin caso concreto no hay hallazgo.
- Lo que figura en «Decisiones ya tomadas» no se discute.
- No inventes fallas ni listes preferencias de estilo: si el plan está bien, el veredicto es «pasa» y la lista de hallazgos puede estar vacía.
- Que un plan no diga algo sólo es una falla si ese vacío puede romperlo; leelo entero antes de afirmar que algo falta.
- Severidad: «alta» si el plan fracasa o causa un daño serio; «media» si se resuelve con un cambio acotado; «baja» si es un detalle.

Revisá el plan en todos sus aspectos: ejecución (orden, dependencias, cuentas), riesgo (irreversibilidad, vuelta atrás, seguridad) y alcance y verificación (objetivo, supuestos, criterio de terminado).

Veredicto: «bloquea» (no se debe ejecutar sin corregir), «corregir» (se puede ejecutar tras cambios acotados) o «pasa» (ejecutable como está). \
Puntaje de 0 a 10: 10 es ejecutable sin cambios.

Respondé únicamente con este JSON:
{{"veredicto": "bloquea|corregir|pasa", "puntaje": 0, "resumen": "una o dos frases", "hallazgos": [{{"severidad": "alta|media|baja", "paso": "número o nombre del paso", "caso": "qué pasa", "arreglo": "el cambio mínimo"}}]}}

PLAN:
-----
{plan}
-----"""

REQUERIDAS = [("Contexto", "contexto"), ("Decisiones ya tomadas", "decisiones ya tomadas"), ("Pasos", "pasos"), ("Terminado cuando", "terminado cuando")]
RECOMENDADAS = [("Qué pasa si falla", "que pasa si")]
MAX_PALABRAS = 2500
SEVERIDAD = {"alta": 0, "media": 1, "baja": 2}
VEREDICTOS = ("pasa", "corregir", "bloquea")
MAX_RONDAS = 2


def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def encabezados(texto):
    return [sin_acentos(m.group(1)).strip() for m in re.finditer(r"^#{1,3}\s+(.+?)\s*$", texto, re.M)]


def validar_plan(texto):
    """(errores, avisos) de un plan: debe bastarse solo."""
    hs = encabezados(texto)
    errores = [f"falta la sección «{nombre}»" for nombre, clave in REQUERIDAS if not any(h.startswith(clave) for h in hs)]
    avisos = [f"conviene una sección «{nombre}»: dice qué se hace si un paso falla a mitad" for nombre, clave in RECOMENDADAS if not any(h.startswith(clave) for h in hs)]
    if len(texto.split()) > MAX_PALABRAS:
        avisos.append(f"el plan tiene más de {MAX_PALABRAS} palabras: un revisor sin contexto lo lee peor; conviene dividirlo")
    return errores, avisos


def pedido(texto):
    return PEDIDO.format(plan=texto.strip())


def extraer_json(texto):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    i = t.find("{")
    if i < 0:
        return None
    prof = 0
    for j in range(i, len(t)):
        prof += t[j] == "{"
        prof -= t[j] == "}"
        if prof == 0:
            try:
                return json.loads(t[i:j + 1])
            except ValueError:
                return None
    return None


def buscar_claude():
    """Comando (lista) para llamar al CLI de Claude, o None. SENIOR_CLAUDE manda; un .py se corre con el mismo Python."""
    env = os.environ.get("SENIOR_CLAUDE")
    if env:
        return [sys.executable, env] if env.lower().endswith(".py") else [env]
    ruta = shutil.which("claude")
    if ruta:
        return [ruta]
    base = os.environ.get("LOCALAPPDATA")
    if base:
        copias = glob.glob(str(Path(base) / "Claude-Data" / "*" / "claude-code" / "*" / "*" / "claude.exe"))
        if copias:
            return [max(copias, key=os.path.getmtime)]
    return None


def resumen(j, ronda):
    lineas = [f"Pez, ronda {ronda}: veredicto «{j.get('veredicto')}», puntaje {j.get('puntaje')}/10. {j.get('resumen', '')}".strip()]
    hall = sorted(j.get("hallazgos") or [], key=lambda h: SEVERIDAD.get(h.get("severidad"), 3))
    for i, h in enumerate(hall, 1):
        lineas.append(f"  {i}. [{h.get('severidad')}] paso {h.get('paso')}: {h.get('caso')}  →  {h.get('arreglo')}")
    if not hall:
        lineas.append("  (sin hallazgos)")
    lineas.append("Siguiente: decidir cada hallazgo (aceptado o rechazado, con su motivo) en el «Registro de revisión» del plan y correr `pez.py decidir <veredictos>`.")
    return "\n".join(lineas)


def siguiente(veredictos):
    """(mensaje, código de salida) según el veredicto de cada ronda."""
    for v in veredictos:
        if v not in VEREDICTOS:
            return f"veredicto desconocido «{v}» (usar pasa, corregir o bloquea)", 2
    ultimo, n = veredictos[-1], len(veredictos)
    if ultimo == "pasa":
        return "SEGUIR: el pez no encontró nada que frene el plan. Se ejecuta con la aprobación del usuario.", 0
    if ultimo == "corregir":
        return "SEGUIR tras aplicar los cambios aceptados (son acotados: no hace falta otra ronda). Se ejecuta con la aprobación del usuario.", 0
    if n < MAX_RONDAS:
        return f"REPETIR: el pez dijo «bloquea». Corregir el plan según lo aceptado y volver a revisarlo (ronda {n + 1} de {MAX_RONDAS}).", 0
    return f"ESCALAR: después de {n} rondas el pez sigue diciendo «bloquea». Se le plantea al usuario qué se decide y no se hace otra ronda.", 1


def cmd_validar(a):
    errores, avisos = validar_plan(Path(a.plan).read_text(encoding="utf-8-sig"))
    for e in errores:
        print("FALTA " + e)
    for v in avisos:
        print("AVISO " + v)
    print("Plan válido para el pez." if not errores else "El plan no se basta solo: completarlo antes de pedir la revisión.")
    return 1 if errores else 0


def cmd_pedir(a):
    print(pedido(Path(a.plan).read_text(encoding="utf-8-sig")))
    return 0


def cmd_revisar(a):
    plan = Path(a.plan)
    texto = plan.read_text(encoding="utf-8-sig")
    errores, _ = validar_plan(texto)
    if errores:
        print("El plan no se basta solo (" + "; ".join(errores) + "): completarlo antes de pedir la revisión.")
        return 1
    claude = buscar_claude()
    if not claude:
        print("No se encontró el CLI de Claude (variable SENIOR_CLAUDE, `claude` en el PATH o la aplicación de escritorio). "
              "Alternativa: `pez.py pedir` imprime el pedido para pasárselo a un subagente (menos aislado: puede leer el proyecto).")
        return 2
    salida = Path(a.salida)
    (salida / "cwd").mkdir(parents=True, exist_ok=True)  # carpeta vacía de trabajo del revisor, dentro del proyecto
    cmd = claude + ["-p", pedido(texto), "--output-format", "json", "--tools", "", "--disable-slash-commands", "--setting-sources", "",
                    "--system-prompt", SISTEMA, "--no-session-persistence", "--max-budget-usd", str(a.max_usd)]
    try:
        r = subprocess.run(cmd, cwd=salida / "cwd", capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, stdin=subprocess.DEVNULL)
        d = json.loads(r.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        print(f"No se pudo correr al pez: {e!r}")
        return 3
    if d.get("is_error"):
        print("El pez respondió con un error: " + str(d.get("result"))[:200])
        return 3
    j = extraer_json(d.get("result", ""))
    if not j or j.get("veredicto") not in VEREDICTOS:
        print("La respuesta del pez no es el JSON pedido: " + str(d.get("result"))[:200])
        return 3
    previas = sorted(salida.glob(f"{plan.stem}-pez-*.json"))
    ronda = len(previas) + 1
    destino = salida / f"{plan.stem}-pez-{ronda}.json"
    destino.write_text(json.dumps({"ronda": ronda, "costo_usd": d.get("total_cost_usd"), **j}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(resumen(j, ronda))
    print(f"(guardado en {destino.as_posix()}; costo {float(d.get('total_cost_usd') or 0):.3f} USD)")
    return 0


def cmd_decidir(a):
    mensaje, codigo = siguiente([v.lower() for v in a.veredictos])
    print(mensaje)
    return codigo


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    for nombre in ("validar", "pedir", "revisar"):
        s = sub.add_parser(nombre)
        s.add_argument("plan")
        if nombre == "revisar":
            s.add_argument("--salida", default=".temporal/planes")
            s.add_argument("--max-usd", type=float, default=1.0)
    s = sub.add_parser("decidir")
    s.add_argument("veredictos", nargs="+")
    a = ap.parse_args()
    if a.orden != "decidir" and not Path(a.plan).is_file():
        sys.exit(f"No existe el plan: {a.plan}")
    sys.exit({"validar": cmd_validar, "pedir": cmd_pedir, "revisar": cmd_revisar, "decidir": cmd_decidir}[a.orden](a))


if __name__ == "__main__":
    main()
