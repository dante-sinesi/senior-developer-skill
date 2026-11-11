#!/usr/bin/env python3
"""Duda con contexto fresco: ayuda mecánica para interrogar una decisión no trivial antes de darla por buena.

La idea (ver references/duda.md): después de una sesión larga, las suposiciones se vuelven hechos. Antes de dar por
buena una decisión que importa, un revisor sin el hilo de la conversación intenta romperla. Este script hace dos
cosas que no necesitan criterio, para que el modelo se concentre en lo que sí:

  armar     Arma el texto para el revisor a partir de lo que se le entrega: el ARTEFACTO (el diff, la función o la
            propuesta) y el CONTRATO (qué debería cumplir). No lleva la afirmación del autor ni su razonamiento:
            un revisor que sabe qué se quiere probar tiende a coincidir. Avisa si el artefacto es demasiado grande.
  decidir   Dado cómo se clasificó cada hallazgo en cada ciclo, dice qué sigue: corregir y repetir, aclarar el
            contrato, parar, escalar al usuario o frenar por «teatro de duda».

Uso:
    python duda.py armar --artefacto ruta [ruta ...] --contrato "texto o ruta de un archivo" [--max-lineas 400]
    python duda.py decidir "accionable,ruido" "ruido,compromiso" ...      (un argumento por ciclo, en orden)

Clases de hallazgo, en el orden en que se evalúan al reconciliar:
  contrato    el revisor se confundió por un contrato poco claro: se aclara el contrato y se repite
  accionable  válido y arreglable: se cambia el artefacto y se repite
  compromiso  válido, pero arreglarlo cuesta más que aceptarlo: se documenta para el usuario
  ruido       incorrecto por un contexto que el revisor no tenía: se anota (¿conviene sumar ese contexto al contrato?)
  trivial     menor o ya considerado

Un ciclo sin hallazgos se escribe «ninguno». Códigos de salida de `decidir`: 0 puede seguir o terminó, 1 hay que
frenar y hablar con el usuario. Solo biblioteca estándar.
"""
import argparse
import sys
from pathlib import Path

CLASES = ("contrato", "accionable", "compromiso", "ruido", "trivial")
MAX_CICLOS = 3

INSTRUCCION = """Eres un revisor adversarial. Quien escribió el ARTEFACTO está demasiado seguro de que está bien.
Tu trabajo es encontrar cómo falla, no confirmar que funciona.

Busca: supuestos que nadie dijo en voz alta, casos límite sin cubrir, acoplamientos escondidos, incumplimientos del
CONTRATO, convenciones rotas y formas de fallar ante entradas inesperadas.

Reglas:
- No resumas ni elogies el artefacto. No valides.
- Cada hallazgo lleva un caso concreto: «con esta entrada o en esta situación pasa este resultado». Sin caso, no es hallazgo.
- Si después de buscar de verdad no encuentras nada, escribe exactamente: «Sin hallazgos» y qué casos probaste.
- Clasifica cada hallazgo por gravedad: alta, media o baja.
"""


def contenido(ruta_o_texto):
    p = Path(ruta_o_texto)
    try:
        if p.is_file():
            return p.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        pass
    return ruta_o_texto.strip()


def armar(artefactos, contrato, max_lineas=400):
    """(texto, avisos). No incluye razonamiento del autor: solo artefacto y contrato."""
    partes, avisos, total = [], [], 0
    for a in artefactos:
        texto = contenido(a)
        n = len(texto.splitlines())
        total += n
        partes.append(f"--- {a if Path(a).is_file() else 'artefacto'} ---\n{texto}")
    if total > max_lineas:
        avisos.append(f"el artefacto tiene {total} líneas (más de {max_lineas}): conviene dividirlo y dudar de cada parte por separado, "
                      "porque una revisión sobre algo tan grande se vuelve superficial")
    if not contrato.strip():
        avisos.append("no hay contrato: sin saber qué debería cumplir, el revisor solo puede opinar de estilo")
    texto = (INSTRUCCION + "\nCONTRATO (lo que debe cumplir):\n" + contrato.strip() + "\n\nARTEFACTO:\n" + "\n\n".join(partes) + "\n")
    return texto, avisos


def parsear_ciclo(texto):
    t = texto.strip().lower()
    if t in ("", "ninguno", "ninguna", "-", "sin hallazgos"):
        return []
    clases = [c.strip() for c in t.split(",") if c.strip()]
    malas = [c for c in clases if c not in CLASES]
    if malas:
        raise ValueError(f"clase desconocida: {', '.join(malas)} (válidas: {', '.join(CLASES)})")
    return clases


def decidir(ciclos):
    """(código, mensaje) a partir de las clases de hallazgo de cada ciclo, en orden. Código: 'parar', 'seguir' o 'escalar'."""
    if not ciclos:
        return "seguir", "todavía no hay ciclos: se arma el texto para el revisor y se lanza el primero."
    ultimo = ciclos[-1]
    sustantivos = [c for c in ultimo if c != "trivial"]
    if not sustantivos:
        return "parar", "el último ciclo no trae nada sustantivo: la decisión aguanta. Se sigue."
    # teatro de duda: dos ciclos seguidos con hallazgos que no cambian nada
    if len(ciclos) >= 2:
        ultimos = ciclos[-2:]
        sin_cambio = all(
            any(c in ("compromiso", "ruido") for c in ciclo) and not any(c in ("accionable", "contrato") for c in ciclo)
            for ciclo in ultimos)
        if sin_cambio:
            return "escalar", ("teatro de duda: dos ciclos seguidos con hallazgos y ninguno accionable. Se está validando, no dudando: "
                               "se frena y se le plantea al usuario, con el revisor o con una mirada distinta.")
    if len(ciclos) >= MAX_CICLOS:
        return "escalar", (f"{MAX_CICLOS} ciclos y todavía hay hallazgos sustantivos: la decisión puede no estar lista o es demasiado grande. "
                           "Se le plantea al usuario en vez de seguir solo.")
    if "accionable" in ultimo:
        return "seguir", "hay hallazgos accionables: se cambia el artefacto y se repite el ciclo con la versión nueva."
    if "contrato" in ultimo:
        return "seguir", "el revisor se confundió por el contrato: se aclara y se repite; no se toca el artefacto por eso."
    return "parar", ("solo quedan compromisos o ruido: se documenta cada compromiso para el usuario y se anota qué contexto faltaba. "
                     "No se repite sobre un artefacto que no cambió.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("armar")
    a.add_argument("--artefacto", nargs="+", required=True)
    a.add_argument("--contrato", default="")
    a.add_argument("--max-lineas", type=int, default=400)
    d = sub.add_parser("decidir")
    d.add_argument("ciclos", nargs="*")
    args = ap.parse_args()
    if args.orden == "armar":
        texto, avisos = armar(args.artefacto, contenido(args.contrato) if args.contrato else "", args.max_lineas)
        for av in avisos:
            print("AVISO: " + av, file=sys.stderr)
        print(texto)
        return
    try:
        ciclos = [parsear_ciclo(c) for c in args.ciclos]
    except ValueError as e:
        sys.exit(f"Error: {e}")
    codigo, mensaje = decidir(ciclos)
    print(f"{codigo.upper()}: {mensaje}")
    sys.exit(1 if codigo == "escalar" else 0)


if __name__ == "__main__":
    main()
