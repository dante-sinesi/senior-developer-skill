"""Los comandos del chat que recoge hook_permisos_chat.py tienen su skill atajo: así aparecen al escribir «/» con su pista de uso."""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:300]))


hook = (RAIZ / "skills" / "senior" / "scripts" / "hook_permisos_chat.py").read_text(encoding="utf-8")
comandos = re.search(r"COMANDO = re\.compile\(.*?/\(([a-z|-]+)\)", hook).group(1).split("|")
chequear("el hook de chat reconoce los comandos esperados", set(comandos) == {"ci-modo", "permitir-fusion", "permitir", "quitar-permiso", "hooks-modo", "hooks-hermanos", "permisos"}, comandos)
readme = (RAIZ / "README.md").read_text(encoding="utf-8")
for c in comandos:
    ruta = RAIZ / "skills" / c / "SKILL.md"
    sk = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
    fm = sk.split("---")[1] if sk.count("---") >= 2 else ""
    desc = re.search(r"(?m)^description:\s*(.+)$", fm)
    chequear(f"/{c} tiene su skill atajo: solo la invoca el usuario, con descripción corta y figura en el README",
             bool(sk) and f"name: {c}" in fm and "disable-model-invocation: true" in fm and desc and len(desc.group(1)) <= 160 and f"`{c}`" in readme, c)
    chequear(f"/{c}: el atajo aclara que lo aplica el hook y no la skill", "no esta skill" in sk, c)
chequear("los comandos con argumentos muestran su pista de uso en el menú", all(re.search(r'(?m)^argument-hint:', (RAIZ / "skills" / c / "SKILL.md").read_text(encoding="utf-8"))
                                                                              for c in comandos if c != "permisos"))
chequear("ci-modo muestra los dos modos en la pista", 'argument-hint: "local [comando de pruebas] | estricto"' in (RAIZ / "skills" / "ci-modo" / "SKILL.md").read_text(encoding="utf-8"))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
