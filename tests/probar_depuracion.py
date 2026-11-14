"""Un hook que falla por dentro deja pasar sin avisar; con SENIOR_HOOK_DEPURAR=1 la caída se ve. Todos los hooks lo respetan."""
import ast
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


hooks = sorted((RAIZ / "skills").glob("*/scripts/hook_*.py"))
chequear("se encontraron los hooks (autoría, lectura externa, fuera del proyecto, protegidos, secretos y permisos del chat)", len(hooks) >= 6, [h.name for h in hooks])

# 1. cada bloque «except Exception» de un hook lo respeta, salvo los que son una alternativa declarada (no un silencio)
for h in hooks:
    texto = h.read_text(encoding="utf-8")
    arbol = ast.parse(texto)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ExceptHandler) and isinstance(nodo.type, ast.Name) and nodo.type.id == "Exception":
            codigo = ast.get_source_segment(texto, nodo) or ""
            linea = texto.splitlines()[nodo.lineno - 1]
            ok = "SENIOR_HOOK_DEPURAR" in codigo or "se conserva el comportamiento de preguntar" in linea
            chequear(f"{h.name}:{nodo.lineno}: el «except Exception» deja ver el error con SENIOR_HOOK_DEPURAR=1", ok, linea.strip())

# 2. con una entrada que rompe el hook por dentro (una lista en lugar de un objeto): silencio normal, error visible al depurar
for h in hooks:
    base = {k: v for k, v in os.environ.items() if k != "SENIOR_HOOK_DEPURAR"}
    normal = subprocess.run([sys.executable, str(h)], input="[]", capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ, env=base)
    depurando = subprocess.run([sys.executable, str(h)], input="[]", capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ,
                               env={**base, "SENIOR_HOOK_DEPURAR": "1"})
    if h.name == "hook_autoria_claude.py":
        # este no atrapa nada: ante una entrada inesperada falla con ruido en ambos modos, nunca en silencio
        chequear(f"{h.name}: no falla en silencio", normal.returncode != 0 and "Traceback" in normal.stderr, normal.stderr[-200:])
        continue
    chequear(f"{h.name}: en uso normal una entrada inesperada deja pasar sin ruido", normal.returncode == 0 and not normal.stdout.strip() and "Traceback" not in normal.stderr, normal.stderr[-200:])
    chequear(f"{h.name}: con SENIOR_HOOK_DEPURAR=1 la misma entrada muestra el error", depurando.returncode != 0 and "Traceback" in depurando.stderr, depurando.stdout + depurando.stderr)

rd = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el README explica SENIOR_HOOK_DEPURAR", "SENIOR_HOOK_DEPURAR" in rd)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
