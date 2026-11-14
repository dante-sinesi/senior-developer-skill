#!/usr/bin/env python3
"""Trabajo autónomo en sesiones largas: la parte mecánica y de seguridad, que hace cumplir el script y no el texto.

Pedir `/trabajo-autonomo` autoriza EXACTAMENTE commits locales en una rama `auto/<tema>-<fecha>` creada desde donde se estaba. Nunca push, Pull Request,
fusión, tag, `main`, reescribir historia ni borrar ramas: este script no tiene ninguna de esas operaciones.

Uso:
  python autonomo.py iniciar <tema> [--comando-tests "<comando>"] [--max-puntos N]   # rama auto/…, plan y registro en .temporal/autonomo/<tema>/
  python autonomo.py punto "<mensaje convencional>"                                 # commit local SOLO si los tests están en verde y la rama es auto/…
  python autonomo.py bloqueo "<pregunta>" [--opciones "a | b"] [--recomendacion "…"] # anota en docs/pendientes.md y sigue; no espera
  python autonomo.py estado                                                         # dónde va la sesión y si hay que parar
  python autonomo.py cerrar                                                         # informe para revisar al volver
Todo lo de trabajo (plan, estado, informe) va en `.temporal/autonomo/`, que git ignora. Solo biblioteca estándar.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

CONVENCIONAL = re.compile(r"^(feat|fix|docs|refactor|test|chore|perf|build|ci|style|revert|security)(\([^)]+\))?!?: \S.{0,70}$")
MAX_FALLOS_SEGUIDOS = 3
PLAN = """# Plan: {tema}

## Objetivo
(Una o dos líneas: qué se quiere lograr.)

## Criterios de terminado (cada uno con el comando que lo comprueba)
- [ ] (por ejemplo: `python -m unittest` en verde)
- [ ] (por ejemplo: la función X devuelve Y para Z)

## Alcance
(Carpetas y archivos que se pueden tocar. Lo que no está acá no se toca.)

## Límites
- Máximo de puntos de guardado: {max_puntos}
- Si algo exige una decisión o un permiso: `autonomo.py bloqueo`, y se sigue con otro paso independiente.

## Pasos
- [ ] 1.
- [ ] 2.
"""


def git(raiz, *args):
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def carpeta(raiz):
    return Path(raiz) / ".temporal" / "autonomo"


def activo(raiz):
    marca = carpeta(raiz) / "ACTIVO"
    if not marca.exists():
        return None, None
    tema = marca.read_text(encoding="utf-8").strip()
    ruta = carpeta(raiz) / tema / "estado.json"
    if not ruta.exists():
        return None, None
    return tema, json.loads(ruta.read_text(encoding="utf-8"))


def guardar(raiz, tema, estado):
    (carpeta(raiz) / tema / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


def rama_actual(raiz):
    return git(raiz, "branch", "--show-current")[1]


def error(msg):
    print(f"No se hizo nada: {msg}")
    return 1


def cmd_iniciar(raiz, a):
    tema = re.sub(r"[^a-z0-9-]+", "-", a.tema.lower()).strip("-")[:40]
    if not tema:
        return error("el tema no puede quedar vacío.")
    if git(raiz, "rev-parse", "--git-dir")[0] != 0:
        return error("esto no es un repositorio git.")
    if activo(raiz)[0]:
        return error(f"ya hay una sesión autónoma activa ({activo(raiz)[0]}): `estado` o `cerrar`.")
    if git(raiz, "status", "--porcelain")[1]:
        return error("hay cambios sin commitear. Se commitean o se guardan antes (con tu aprobación): así lo que se haga acá no se mezcla con lo tuyo.")
    base = git(raiz, "rev-parse", "HEAD")[1]
    rama = f"auto/{tema}-{time.strftime('%Y%m%d')}"
    rc, o = git(raiz, "switch", "-c", rama)
    if rc != 0:
        return error(f"no se pudo crear la rama {rama}: {o[:200]}")
    d = carpeta(raiz) / tema
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.md").write_text(PLAN.format(tema=tema, max_puntos=a.max_puntos), encoding="utf-8")
    estado = {"tema": tema, "rama": rama, "base": base, "comando_tests": a.comando_tests, "max_puntos": a.max_puntos,
              "puntos": [], "bloqueos": [], "fallos_seguidos": 0, "inicio": time.strftime("%Y-%m-%d %H:%M")}
    guardar(raiz, tema, estado)
    (carpeta(raiz) / "ACTIVO").write_text(tema, encoding="utf-8")
    print(f"Sesión autónoma «{tema}» iniciada en la rama {rama} (desde {base[:8]}).")
    print(f"Plan para completar: {(d / 'plan.md').as_posix()} (objetivo, criterios con su comando, alcance, pasos).")
    print("Autorizado: commits locales en esta rama con `punto`. No autorizado: push, PR, fusión, main, reescribir historia.")
    return 0


def cmd_punto(raiz, a):
    tema, e = activo(raiz)
    if not tema:
        return error("no hay una sesión autónoma activa (`iniciar`).")
    rama = rama_actual(raiz)
    if not rama.startswith("auto/") or rama != e["rama"]:
        return error(f"se está en «{rama}» y la sesión usa «{e['rama']}»: los puntos de guardado solo se hacen en la rama auto/ de la sesión.")
    if not CONVENCIONAL.match(a.mensaje):
        return error("el mensaje tiene que ser Conventional Commits en español neutro, por ejemplo `feat(envio): calcula el costo por peso` (hasta 72 caracteres).")
    if len(e["puntos"]) >= e["max_puntos"]:
        return error(f"se llegó al máximo de {e['max_puntos']} puntos de guardado: cerrá la sesión (`cerrar`) o pedí más al usuario.")
    if not git(raiz, "status", "--porcelain")[1]:
        return error("no hay cambios para guardar.")
    if e["comando_tests"]:
        r = subprocess.run(e["comando_tests"], cwd=raiz, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            e["fallos_seguidos"] += 1
            guardar(raiz, tema, e)
            print(f"Tests en rojo: no se guarda un punto con tests rotos (fallo {e['fallos_seguidos']} de {MAX_FALLOS_SEGUIDOS} seguidos).")
            print("\n".join((r.stdout + r.stderr).strip().splitlines()[-8:]))
            if e["fallos_seguidos"] >= MAX_FALLOS_SEGUIDOS:
                print(f"ALTO: {MAX_FALLOS_SEGUIDOS} intentos fallidos seguidos. Dejá de insistir en este paso: `bloqueo` con lo que probaste y pasá a otro paso independiente.")
            return 1
    git(raiz, "add", "-A")
    rc, o = git(raiz, "commit", "-q", "-m", a.mensaje)
    if rc != 0:
        return error(f"git rechazó el commit (los hooks de git, de secretos o de autoría, lo frenan por una razón): {o[:300]}")
    sha = git(raiz, "rev-parse", "--short", "HEAD")[1]
    e["puntos"].append({"sha": sha, "mensaje": a.mensaje, "hora": time.strftime("%H:%M")})
    e["fallos_seguidos"] = 0
    guardar(raiz, tema, e)
    print(f"Punto de guardado {len(e['puntos'])}/{e['max_puntos']}: {sha} {a.mensaje} (commit local; no se sube).")
    return 0


def cmd_bloqueo(raiz, a):
    tema, e = activo(raiz)
    if not tema:
        return error("no hay una sesión autónoma activa.")
    linea = f"- [ ] **Bloqueo del trabajo autónomo «{tema}» ({time.strftime('%Y-%m-%d %H:%M')}):** {a.pregunta}"
    if a.opciones:
        linea += f" Opciones: {a.opciones}."
    if a.recomendacion:
        linea += f" Recomendación: {a.recomendacion}."
    ruta = Path(raiz) / "docs" / "pendientes.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    previo = ruta.read_text(encoding="utf-8") if ruta.exists() else "# Pendientes\n\n"
    ruta.write_text(previo.rstrip("\n") + "\n" + linea + "\n", encoding="utf-8")
    e["bloqueos"].append({"pregunta": a.pregunta, "hora": time.strftime("%H:%M")})
    e["fallos_seguidos"] = 0
    guardar(raiz, tema, e)
    print("Bloqueo anotado en docs/pendientes.md. No se espera ni se pregunta: seguí con otro paso que no dependa de esto; si no queda ninguno, `cerrar`.")
    return 0


def cmd_estado(raiz, a):
    tema, e = activo(raiz)
    if not tema:
        print("No hay una sesión autónoma activa.")
        return 0
    print(f"Sesión «{tema}» en {e['rama']} desde {e['inicio']}: {len(e['puntos'])}/{e['max_puntos']} puntos de guardado, {len(e['bloqueos'])} bloqueos, "
          f"{e['fallos_seguidos']} fallos seguidos.")
    if rama_actual(raiz) != e["rama"]:
        print(f"AVISO: se está en «{rama_actual(raiz)}», no en {e['rama']}.")
    if e["fallos_seguidos"] >= MAX_FALLOS_SEGUIDOS:
        print("ALTO: demasiados intentos fallidos seguidos en el mismo paso.")
    if len(e["puntos"]) >= e["max_puntos"]:
        print("ALTO: se llegó al máximo de puntos de guardado.")
    return 0


def cmd_cerrar(raiz, a):
    tema, e = activo(raiz)
    if not tema:
        return error("no hay una sesión autónoma activa.")
    d = carpeta(raiz) / tema
    plan = (d / "plan.md").read_text(encoding="utf-8") if (d / "plan.md").exists() else ""
    criterios = [l.strip() for l in plan.splitlines() if re.match(r"^- \[[ xX]\]", l.strip())]
    log = git(raiz, "log", "--oneline", f"{e['base']}..HEAD")[1] or "(ningún commit)"
    stat = git(raiz, "diff", "--stat", f"{e['base']}..HEAD")[1] or "(sin cambios)"
    informe = [f"# Informe del trabajo autónomo «{tema}»", "", f"Rama: `{e['rama']}` (desde `{e['base'][:8]}`). Inicio {e['inicio']}, cierre {time.strftime('%Y-%m-%d %H:%M')}.", "",
               "## Qué se hizo (commits locales)", "", "```", log, "```", "", "```", stat, "```", "", "## Criterios de terminado y pasos del plan", ""]
    informe += criterios or ["(el plan no tiene casillas)"]
    informe += ["", "## Bloqueos (decisiones que esperan al usuario)", ""]
    informe += [f"- {b['pregunta']}" for b in e["bloqueos"]] or ["(ninguno)"]
    informe += ["", "## Cómo revisarlo", "", f"- `git log --oneline {e['base'][:8]}..{e['rama']}` y `git diff {e['base'][:8]}..{e['rama']}`",
                "- Lo que se aprueba al volver, por separado y cada vez: subir la rama (push), abrir el Pull Request y fusionar. Nada de eso se hizo.",
                f"- Para descartarlo todo: volver a la rama de origen y borrar `{e['rama']}` (lo decide el usuario).", ""]
    (d / "informe.md").write_text("\n".join(informe), encoding="utf-8")
    (carpeta(raiz) / "ACTIVO").unlink(missing_ok=True)
    print(f"Informe en {(d / 'informe.md').as_posix()}: {len(e['puntos'])} puntos de guardado, {len(e['bloqueos'])} bloqueos. Sesión cerrada; nada se subió.")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("iniciar")
    p.add_argument("tema")
    p.add_argument("--comando-tests", default="")
    p.add_argument("--max-puntos", type=int, default=20)
    p = sub.add_parser("punto")
    p.add_argument("mensaje")
    p = sub.add_parser("bloqueo")
    p.add_argument("pregunta")
    p.add_argument("--opciones", default="")
    p.add_argument("--recomendacion", default="")
    sub.add_parser("estado")
    sub.add_parser("cerrar")
    a = ap.parse_args()
    raiz = Path(a.raiz).resolve()
    return {"iniciar": cmd_iniciar, "punto": cmd_punto, "bloqueo": cmd_bloqueo, "estado": cmd_estado, "cerrar": cmd_cerrar}[a.cmd](raiz, a)


if __name__ == "__main__":
    sys.exit(main())
