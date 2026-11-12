import json
import io
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "skills" / "senior-git" / "scripts" / "repo_meta.py"
P = RAIZ / ".temporal" / "proy-meta"
shutil.rmtree(P, ignore_errors=True)
P.mkdir(parents=True)
(P / "app").mkdir()
(P / "app" / "a.py").write_text("x = 1\n", encoding="utf-8")
(P / "app" / "b.py").write_text("y = 2\n", encoding="utf-8")
(P / "app" / "c.js").write_text("let z\n", encoding="utf-8")
(P / "requirements.txt").write_text("flask==3.0\npytest\n", encoding="utf-8")
(P / "Dockerfile").write_text("FROM python\n", encoding="utf-8")
(P / "README.md").write_text("# Gestor de turnos\n\n[![x](y)](z)\n\nAplicación para reservar **turnos** en una peluquería. Incluye agenda y avisos.\n\n## Uso\n", encoding="utf-8")
subprocess.run(["git", "init", "-q"], cwd=P)
SIM = P / "sim.json"
mal = 0


def esc(estado, *args):
    SIM.write_text(json.dumps(estado), encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(P), "--simular", str(SIM), *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def chequear(nombre, cond, salida=""):
    global mal
    if not cond:
        mal += 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "\n" + salida))


vacio = {"repo": "o/r", "description": "", "topics": [], "permiso": "ADMIN", "privado": True}
rc, s = esc(vacio)
chequear("detecta lenguajes, flask, pytest y docker", all(x in s for x in ("python", "flask", "pytest", "docker")), s)
chequear("el borrador sale del README sin formato", "Aplicación para reservar turnos en una peluquería." in s and "**" not in s, s)
rc, s = esc(vacio, "--descripcion", "Reserva de turnos para una peluquería.", "--topics", "turnos,peluqueria")
chequear("muestra los cambios y no escribe", "Cambios:" in s and "No se escribió nada" in s and "turnos" in s, s)
rc, s = esc(vacio, "--descripcion", "Reserva de turnos.", "--topics", "turnos", "--aplicar")
chequear("simula el comando de gh con los topics", 'gh repo edit o/r --description "Reserva de turnos."' in s and "--add-topic turnos" in s and "--add-topic flask" in s, s)
rc, s = esc({**vacio, "permiso": "READ"}, "--descripcion", "Algo.", "--aplicar")
chequear("sin permiso no aplica", rc == 1 and "NO se aplicó" in s, s)
rc, s = esc({**vacio, "description": "La puso el usuario"}, "--descripcion", "Otra cosa.")
chequear("no pisa una descripción ajena", "no la puso senior" in s and "descripción →" not in s, s)
rc, s = esc({**vacio, "description": "La puso el usuario"}, "--descripcion", "Otra cosa.", "--reemplazar-descripcion")
chequear("la pisa si se pide", "descripción → Otra cosa." in s, s)
rc, s = esc(vacio, "--descripcion", "Escribime a dante@example.com")
chequear("rechaza un correo en la descripción", rc == 1 and "NO VÁLIDO" in s, s)
rc, s = esc(vacio, "--topics", "Mal Topic")
chequear("rechaza un topic inválido", rc == 1 and "no es válido" in s, s)
rc, s = esc(vacio, "--descripcion", "x" * 351)
chequear("rechaza más de 350 caracteres", rc == 1 and "351" in s, s)
rc, s = esc({**vacio, "topics": ["python", "flask", "docker", "pytest", "turnos"]}, "--descripcion", "Reserva de turnos.", "--topics", "turnos")
chequear("lo que ya está no se repite", "topics a agregar" not in s or "turnos" not in s.split("topics a agregar")[1], s)
muchos = {**vacio, "topics": [f"t{i}" for i in range(19)]}
rc, s = esc(muchos, "--topics", "uno,dos")
chequear("avisa si pasa de 20 topics", "admite 20" in s, s)
# quitar solo lo que puso senior
git_dir = P / ".git"
(git_dir / "senior-repo-meta.json").write_text(json.dumps({"descripcion": "Vieja", "topics": ["viejo", "python"], "huella": "x"}), encoding="utf-8")
rc, s = esc({**vacio, "description": "Vieja", "topics": ["viejo", "python", "del-usuario"]}, "--topics", "nuevo")
chequear("quita lo viejo de senior y respeta lo del usuario", "a quitar (los había puesto senior) → viejo" in s and "del-usuario" not in s.split("Cambios:")[1], s)
rc, s = esc(vacio)
chequear("avisa que el proyecto cambió desde la última vez", "cambió desde la última vez" in s, s)
rc = subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(P), "--simular", str(P / "no-existe.json")], capture_output=True).returncode
print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
