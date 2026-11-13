#!/usr/bin/env python3
"""Corre todas las baterías de `tests/` y resume. Sale con 1 si alguna falla.

Uso:
    python tests/correr_todo.py            # todas
    python tests/correr_todo.py hook escala  # solo las que contengan esas palabras

Cada batería es un script `probar_*.py` que imprime «ok»/«MAL» por caso y sale con 1 si hay alguno mal. Lo que crean
va en `.temporal/` (git lo ignora). Solo biblioteca estándar.
"""
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    filtros = [a.lower() for a in sys.argv[1:]]
    baterias = [b for b in sorted(AQUI.glob("probar_*.py")) if not filtros or any(f in b.name.lower() for f in filtros)]
    if not baterias:
        sys.exit("No hay baterías que coincidan.")
    fallan = []
    for b in baterias:
        t = time.perf_counter()
        r = subprocess.run([sys.executable, str(b)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=AQUI.parent)
        malos = [l for l in r.stdout.splitlines() if l.startswith("MAL")]
        estado = "ok " if r.returncode == 0 else "MAL"
        print(f"{estado}  {b.name:42} {time.perf_counter() - t:5.1f} s" + (f"  ({len(malos)} casos mal)" if malos else ""))
        if r.returncode != 0:
            fallan.append(b.name)
            for l in (malos or (r.stdout + r.stderr).strip().splitlines()[-5:])[:8]:
                print("      " + l)
    print(f"\n{len(baterias) - len(fallan)} de {len(baterias)} baterías en verde." + (f" Fallan: {', '.join(fallan)}" if fallan else ""))
    sys.exit(1 if fallan else 0)


if __name__ == "__main__":
    main()
