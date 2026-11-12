"""El guardián de la regla máxima: 28 formas de escribir fuera del proyecto (y de leer, que es legítimo) contra el hook real."""
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
HOOK = RAIZ / "skills" / "senior" / "scripts" / "hook_fuera_del_proyecto.py"
mal = 0


def bloquea(herramienta, entrada):
    ev = {"tool_name": herramienta, "tool_input": entrada, "cwd": str(RAIZ), "hook_event_name": "PreToolUse"}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True, text=True, encoding="utf-8", cwd=RAIZ,
                       env={**os.environ, "SENIOR_HOOK_DEPURAR": "1"})  # si el hook se rompe, la prueba lo ve en lugar de «dejar pasar»
    if "Traceback" in r.stderr:
        raise RuntimeError("el hook falló por dentro: " + r.stderr[-400:])
    return r.returncode == 2 or "deny" in r.stdout or '"ask"' in r.stdout


GT = chr(62)  # el signo de redirección; se arma así para que el hook vivo no frene a quien edita este archivo
casos = [
    ("escribir fuera con ruta absoluta", "Write", {"file_path": "C:/Users/Public/x.txt", "content": "a"}, True),
    ("escribir dentro", "Write", {"file_path": str(RAIZ / ".temporal" / "x.txt"), "content": "a"}, False),
    ("redirección a /tmp en bash", "Bash", {"command": "echo hola " + GT + " /tmp/x.txt"}, True),
    ("redirección con doble signo a una ruta de Windows", "Bash", {"command": "echo hola " + GT * 2 + " C:/Users/Public/x.txt"}, True),
    ("tee a ruta fuera", "Bash", {"command": "echo hola | tee /tmp/x.txt"}, True),
    ("cp hacia fuera", "Bash", {"command": "cp README.md /tmp/README.md"}, True),
    ("python -c que escribe fuera", "Bash", {"command": "python -c \"open('/tmp/x','w').write('a')\""}, True),
    ("python en heredoc que escribe fuera", "Bash", {"command": "python - <<'E'\nopen('/tmp/x','w').write('a')\nE"}, True),
    ("python -c que solo lee fuera", "Bash", {"command": "python -c \"print(open('/etc/hostname').read())\""}, False),
    ("pathlib que escribe fuera", "Bash", {"command": "python -c \"from pathlib import Path; Path('/tmp/x').write_text('a')\""}, True),
    ("PowerShell Set-Content fuera", "PowerShell", {"command": "Set-Content -Path C:/Users/Public/x.txt -Value a"}, True),
    ("PowerShell con redirección", "PowerShell", {"command": "'a' " + GT + " C:/Users/Public/x.txt"}, True),
    ("curl -o a ruta fuera", "Bash", {"command": "curl -o /tmp/x https://example.com"}, True),
    ("git clone fuera", "Bash", {"command": "git clone https://example.com/r.git /tmp/r"}, True),
    ("node -e que escribe fuera", "Bash", {"command": "node -e \"require('fs').writeFileSync('/tmp/x','a')\""}, True),
    ("ruta con .. que sale", "Write", {"file_path": str(RAIZ / ".." / ".." / "afuera.txt"), "content": "a"}, True),
    ("mkdir fuera", "Bash", {"command": "mkdir /tmp/carpeta"}, True),
    ("mv hacia fuera con comillas", "Bash", {"command": "mv README.md \"/tmp/otro nombre.md\""}, True),
    ("lectura legítima fuera (cat)", "Bash", {"command": "cat /etc/hostname"}, False),
    ("ls fuera", "Bash", {"command": "ls C:/Users"}, False),
    ("pip install (escribe en site-packages)", "Bash", {"command": "pip install requests"}, False),
    ("NotebookEdit fuera", "NotebookEdit", {"notebook_path": "C:/Users/Public/n.ipynb", "new_source": "a"}, True),
    ("Edit fuera", "Edit", {"file_path": "C:/Users/Public/x.txt", "old_string": "a", "new_string": "b"}, True),
    ("variable $env:TEMP en PowerShell", "PowerShell", {"command": "Set-Content $env:TEMP/x.txt a"}, True),
    ("variable $TMPDIR en bash", "Bash", {"command": "echo a " + GT + " $TMPDIR/x.txt"}, True),
    ("ruta de red", "Bash", {"command": "echo a " + GT + " //servidor/compartida/x.txt"}, True),
    ("sed -i fuera", "Bash", {"command": "sed -i 's/a/b/' /tmp/x.txt"}, True),
    ("dd of= fuera", "Bash", {"command": "dd if=/dev/zero of=/tmp/x bs=1 count=1"}, True),
    ("base64 -d hacia fuera", "Bash", {"command": "echo YQ== | base64 -d " + GT + " /tmp/x"}, True),
    ("ruta armada con variables", "Bash", {"command": "D=/tm; D=${D}p; echo a " + GT + " $D/x"}, True),
    ("variable que apunta adentro", "Bash", {"command": "D=.temporal/m; echo a " + GT + " $D/x"}, False),
]
for desc, h, e, debe in casos:
    b = bloquea(h, e)
    mal += 0 if b == debe else 1
    print(("ok   " if b == debe else "MAL  ") + desc + ("" if b == debe else f"  (esperado {'bloquea' if debe else 'pasa'})"))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
