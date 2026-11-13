"""Si falta `markitdown` o `Pillow`, el primer bloqueo ya dice el comando exacto para instalarlas (con aprobación del usuario) y el conversor lo repite."""
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = RAIZ / "skills" / "senior-relevar" / "scripts"
BASE = RAIZ / ".temporal" / "proy-dependencias"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
P = BASE / "proyecto"
(P / "documentos-externos").mkdir(parents=True)
subprocess.run(["git", "init", "-q"], cwd=P)
(P / "documentos-externos" / "manual.pdf").write_bytes(b"%PDF-1.4\n" + b"0" * 200)
(P / "documentos-externos" / "foto.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 300)

# 1. el hook, con la biblioteca ausente y presente
espec = importlib.util.spec_from_file_location("hook_lectura_externa", SCRIPTS / "hook_lectura_externa.py")
hook = importlib.util.module_from_spec(espec)
espec.loader.exec_module(hook)
pdf = P / "otros" / "contrato.pdf"
pdf.parent.mkdir()
pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 200)
exacto_doc = f'"{sys.executable}" -m pip install "markitdown[all]"'
exacto_img = f'"{sys.executable}" -m pip install "pillow"'

hook.modulo_instalado = lambda nombre: False
accion, msg = hook.decidir(pdf, str(P))
chequear("un documento: el primer bloqueo avisa que falta markitdown con el comando exacto", accion == "negar" and "ANTES DE CONVERTIR" in msg and exacto_doc in msg, msg)
chequear("aclara que necesita la aprobación del usuario, que se anota para cuando vuelva y que se sigue sin esperar", "aprobación del usuario" in msg and "nunca se instala sola" in msg and "docs/pendientes.md" in msg and "sin esperar" in msg, msg)
chequear("y conserva la instrucción de convertir", "convertir_fuentes.py" in msg and "--importar" in msg, msg)
hook.dimensiones = lambda ruta: (3000, 2000)
grande = P / "otros" / "plano.png"
grande.write_bytes(b"\x89PNG" + b"0" * 100)
chequear("una imagen grande ya no se bloquea (la lectura nativa la reduce; bloquearla costó +8 %)", hook.decidir(grande, str(P)) is None)

hook.modulo_instalado = lambda nombre: True
accion, msg = hook.decidir(pdf, str(P))
chequear("con las bibliotecas instaladas no agrega ningún aviso", accion == "negar" and "ANTES DE CONVERTIR" not in msg and "convertir_fuentes.py" in msg, msg)

# 2. el conversor, con las bibliotecas simuladas como ausentes (módulos que fallan al importar, puestos primero en el camino de búsqueda)
SIM = BASE / "simulado"
(SIM / "PIL").mkdir(parents=True)
(SIM / "markitdown.py").write_text('raise ImportError("simulado: no instalada")\n', encoding="utf-8")
(SIM / "PIL" / "__init__.py").write_text('raise ImportError("simulado: no instalada")\n', encoding="utf-8")


def convertir(*args):
    r = subprocess.run([sys.executable, str(SCRIPTS / "convertir_fuentes.py"), "--raiz", str(P), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONPATH": str(SIM)}, cwd=P)
    return r.returncode, r.stdout + r.stderr


rc, s = convertir()
chequear("sin markitdown el conversor sale con 2 y repite el comando exacto", rc == 2 and exacto_doc in s and "Falta `markitdown`" in s, (rc, s))
chequear("dice que la instalación necesita la aprobación del usuario, que no lea el original y que anote el pendiente y siga", "aprobación del usuario" in s and "NO leer los originales" in s and "docs/pendientes.md" in s and "sin esperar" in s, s)
chequear("sin Pillow las imágenes ya no son obligatorias: no pide instalarla ni falla por ella", exacto_img not in convertir("documentos-externos/foto.png")[1], convertir("documentos-externos/foto.png")[1])
chequear("el conversor no instaló nada", not (P / "docs" / "fuentes" / "manual.md").exists())

sk = (RAIZ / "skills" / "senior-relevar" / "SKILL.md").read_text(encoding="utf-8")
chequear("la skill de relevar lo explica", "comando exacto" in sk or "primer bloqueo" in sk)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
