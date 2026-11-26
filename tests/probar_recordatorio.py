#!/usr/bin/env python3
"""El recordatorio al abrir, retomar, limpiar y compactar (hook SessionStart) y su registro por la guardia."""
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
CARGAR = RAIZ / "skills" / "senior-docs" / "scripts" / "cargar_estado.py"
GUARDIA = RAIZ / "skills" / "senior-git" / "scripts" / "guardia_autoria.py"
BASE = RAIZ / ".temporal" / "proy-recordatorio"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def escribir(raiz, ruta, texto):
    f = raiz / ruta
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


def git(raiz, *args):
    subprocess.run(["git", "-c", "user.name=x", "-c", "user.email=x@example.com", "-c", "core.hooksPath=/dev/null", *args], cwd=raiz, capture_output=True, check=True)


def entorno(casa):
    e = {**os.environ, "USERPROFILE": str(casa), "HOME": str(casa), "SENIOR_TOKEN_DIET_HOME": str(casa)}
    e.pop("CLAUDE_PROJECT_DIR", None)
    return e


def hook(cwd, fuente="startup", entrada=None):
    datos = entrada if entrada is not None else json.dumps({"session_id": "s1", "hook_event_name": "SessionStart", "source": fuente, "cwd": str(cwd)})
    r = subprocess.run([sys.executable, str(CARGAR), "--hook"], input=datos.encode("utf-8"), capture_output=True, env=entorno(CASA), cwd=BASE, timeout=120)
    return r.returncode, r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")


shutil.rmtree(BASE, onerror=_forzar) if BASE.exists() else None
CASA = BASE / "casa"
CASA.mkdir(parents=True)

# 1. un proyecto que no usa la metodología no recibe nada: ni salida, ni archivos, ni hooks de git
ajeno = BASE / "ajeno"
ajeno.mkdir()
git(ajeno, "init", "-q")
antes = sorted(p.relative_to(ajeno).as_posix() for p in ajeno.rglob("*"))
rc, s, e = hook(ajeno)
chequear("sin docs/ESTADO.md no imprime nada", rc == 0 and s.strip() == "", (rc, s, e))
chequear("y no toca el repositorio", sorted(p.relative_to(ajeno).as_posix() for p in ajeno.rglob("*")) == antes)

# 2. un proyecto adoptado: escala, estado, documentos, commits sin documentar y la secuencia
p = BASE / "adoptado"
p.mkdir()
git(p, "init", "-q")
escribir(p, "docs/ESTADO.md", "# Estado\n\n**Escala del proyecto:** grande\n\nEn curso: el cobro con tarjeta.\n")
escribir(p, "docs/requisitos/RF-001.md", "# RF-001\n")
escribir(p, "docs/requisitos/RF-002.md", "# RF-002\n")
escribir(p, "docs/casos-de-uso/CU-01.md", "# CU-01\n")
escribir(p, "docs/cambios/2026-cobro.md", "estado: en curso\n- [ ] probar el rechazo\n")
escribir(p, "src/a.py", "x = 1\n")
git(p, "add", "-A")
git(p, "commit", "-qm", "base")
for i in (2, 3):
    escribir(p, "src/a.py", f"x = {i}\n")
    git(p, "commit", "-qam", f"cambio {i}")
escribir(p, "README.md", "# solo texto\n")
git(p, "add", "-A")
git(p, "commit", "-qm", "readme")
rc, s, e = hook(p)
chequear("trae la escala y el estado", rc == 0 and "grande" in s and "cobro con tarjeta" in s, (rc, s, e))
chequear("cuenta los documentos por tipo", "requisitos: 2" in s and "casos-de-uso: 1" in s, s)
chequear("dice cuántos commits de código pasaron sin tocar docs (el de solo README no cuenta)", "2 commits de código" in s, s)
chequear("muestra la ficha en curso y su paso abierto", "2026-cobro.md" in s and "probar el rechazo" in s, s)
chequear("recuerda la secuencia", "test" in s.lower() and "documentar" in s.lower(), s)
for fuente in ("resume", "clear", "compact"):
    rc, s2, _ = hook(p, fuente)
    chequear(f"también al volver por «{fuente}»", rc == 0 and "cobro con tarjeta" in s2, s2[:200])
rc, s2, _ = hook(p / "src")
chequear("desde una subcarpeta encuentra el proyecto", "cobro con tarjeta" in s2, s2[:200])
escribir(p, "docs/requisitos/RF-001.md", "# RF-001 cambiado\n")
git(p, "commit", "-qam", "docs")
chequear("con la documentación al día no marca atraso", "commits de código" not in hook(p)[1])

# 3. el tope: un estado enorme no se vuelca entero
escribir(p, "docs/ESTADO.md", "# Estado\n\n**Escala del proyecto:** grande\n\n" + ("palabra " * 80 + "\n") * 55)
escribir(p, "docs/cambios/otra.md", "estado: en curso\n" + "- [ ] " + "paso largo " * 40 + "\n")
rc, s, _ = hook(p, "compact")
chequear("no pasa de 600 palabras y avisa que hay más", len(s.split()) <= 600 and "leerlo completo" in s, len(s.split()))
chequear("aun recortado conserva la secuencia y el conteo de documentos", "documentar" in s.lower() and "requisitos: 2" in s, s[-300:])

# 4. entradas raras: nunca rompe la sesión
for nombre, datos in (("basura", "no es json"), ("vacía", ""), ("una lista", "[1]"), ("cwd que no existe", json.dumps({"cwd": str(BASE / "nada")}))):
    rc, s, e = hook(p, entrada=datos)
    chequear(f"entrada {nombre}: sale con 0 y sin error", rc == 0 and "Traceback" not in e, (rc, e[-200:]))


# 5. la guardia registra el hook, repara una ruta vieja y cada hook registrado existe y corre
def asegurar():
    return subprocess.run([sys.executable, str(GUARDIA), "asegurar", "--raiz", str(BASE)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=entorno(CASA))


def comandos(evento):
    ajustes = json.loads((CASA / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return [h["command"] for g in ajustes["hooks"].get(evento, []) for h in g["hooks"]]


r = asegurar()
inicio = comandos("SessionStart")
chequear("registra el recordatorio en SessionStart, en modo hook", len(inicio) == 1 and "cargar_estado.py" in inicio[0] and inicio[0].endswith("--hook"), (inicio, r.stdout))
asegurar()
chequear("repetir no lo duplica", len(comandos("SessionStart")) == 1)
vieja = BASE / "vieja" / "cargar_estado.py"
vieja.parent.mkdir()
vieja.write_text("pass\n", encoding="utf-8")
ajustes = json.loads((CASA / ".claude" / "settings.json").read_text(encoding="utf-8"))
ajustes["hooks"]["SessionStart"][0]["hooks"][0]["command"] = f'python "{vieja.as_posix()}" --hook'
ajustes["hooks"]["SessionStart"].append({"hooks": [{"type": "command", "command": "echo ajeno"}]})
(CASA / ".claude" / "settings.json").write_text(json.dumps(ajustes), encoding="utf-8")
asegurar()
inicio = comandos("SessionStart")
chequear("reescribe una ruta vieja aunque el archivo viejo siga existiendo, sin tocar hooks ajenos",
         len(inicio) == 2 and CARGAR.as_posix() in inicio[0] and inicio[1] == "echo ajeno", inicio)
ajustes = json.loads((CASA / ".claude" / "settings.json").read_text(encoding="utf-8"))
registrados = [h["command"] for ev in ajustes["hooks"].values() for g in ev for h in g["hooks"] if "echo" not in h["command"]]
chequear("hay un hook registrado por cada uno de la guardia", len(registrados) == 3, registrados)
for c in registrados:
    ruta = Path(re.search(r'"([^"]+\.py)"', c).group(1))
    resto = c.split('"')[2].split()
    corre = subprocess.run([sys.executable, str(ruta), *resto], input=b"{}", capture_output=True, env=entorno(CASA), cwd=ajeno, timeout=60)
    chequear(f"el hook registrado {ruta.name} existe y corre", ruta.exists() and corre.returncode == 0 and b"Traceback" not in corre.stderr, corre.stderr[-200:])

shutil.rmtree(BASE, onerror=_forzar)
print("\nfallos:", mal)
sys.exit(1 if mal else 0)
