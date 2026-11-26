#!/usr/bin/env python3
"""Instalador del paquete senior: deja todo listo la primera vez (o en una máquina nueva).

Uso:
    python instalar.py                         # instala las skills y registra los hooks, y dice qué falta
    python instalar.py --verificar             # solo informa el estado (incluye si lo instalado está al día con este repositorio); no escribe nada

Qué hace:
  1. Comprueba Python 3.10 o superior, Git, el CLI `gh` (opcional, para GitHub) y `pip`.
  2. Copia las skills de este repositorio a ~/.claude/skills, reemplazando las del paquete (no toca ninguna otra
     skill) y pasando los archivos de texto a fin de línea de Unix. Las skills que instaló antes y ya no están en el paquete
     se listan y se sacan a ~/.claude/senior-retiradas (no se borran).
  3. Registra en ~/.claude/settings.json los hooks globales de Claude Code (un despachador de controles, los permisos
     desde el chat y el recordatorio del estado al abrir y compactar), conservando los ajustes que ya haya y con una copia de seguridad.
  4. Comprueba si Token Diet (skill de ahorro de tokens, recomendada, no obligatoria) está instalada y lo informa.
  5. Imprime un informe con lo que quedó listo y los pasos que faltan (por ejemplo `gh auth login` y la identidad
     de Git de cada repositorio).
Los hooks de Git de cada proyecto no se instalan aquí: la skill los activa sola la primera vez que se usa en cada
repositorio (guardia_autoria.py asegurar). Solo biblioteca estándar. Código de salida: 0 todo listo, 1 faltan cosas.
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SKILLS = RAIZ / "skills"
DESTINO = Path.home() / ".claude" / "skills"
# skills que dejaron de estar en el paquete (para instalaciones sin registro) y las que se mudaron a otro paquete: esas nunca se tocan
RETIRADAS = {"senior-memoria", "senior-refactor", "senior-lenguajes"}
MUDADAS = {"senior-diseno", "auditar-diseno"}
TEXTO = {".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".sh", ".yml", ".yaml"}



def cargar_guardia():
    ruta = SKILLS / "senior-git" / "scripts" / "guardia_autoria.py"
    espec = importlib.util.spec_from_file_location("guardia_autoria", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


def normalizado(ruta):
    datos = ruta.read_bytes()
    if ruta.suffix.lower() in TEXTO:
        datos = datos.replace(b"\r\n", b"\n")
    return datos


def huella(ruta):
    return hashlib.sha256(normalizado(ruta)).hexdigest()


def archivos_de(carpeta):
    return sorted(f for f in carpeta.rglob("*") if f.is_file() and "__pycache__" not in f.parts)


def desactualizadas():
    """Skills del repositorio que no están instaladas o difieren de lo instalado."""
    res = []
    for origen in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
        destino = DESTINO / origen.name
        if not destino.is_dir():
            res.append(origen.name)
            continue
        esperados = {f.relative_to(origen).as_posix(): huella(f) for f in archivos_de(origen)}
        presentes = {f.relative_to(destino).as_posix(): huella(f) for f in archivos_de(destino)}
        if esperados != presentes:
            res.append(origen.name)
    return res


def instalar_skills():
    copiadas = []
    DESTINO.mkdir(parents=True, exist_ok=True)
    for origen in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
        destino = DESTINO / origen.name
        if destino.exists():
            shutil.rmtree(destino)
        for f in archivos_de(origen):
            salida = destino / f.relative_to(origen)
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(normalizado(f))
            shutil.copystat(f, salida)
        copiadas.append(origen.name)
    return copiadas


def registradas_en(manifiesto):
    try:
        return set(json.loads(manifiesto.read_text(encoding="utf-8-sig"))["skills"])
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def retiradas_instaladas():
    """Lo que este instalador puso alguna vez y ya no está en el paquete; nunca lo que registra otro paquete ni lo que se mudó."""
    propio = DESTINO / ".senior-instalacion.json"
    ajenas = set().union(*(registradas_en(m) for m in DESTINO.glob(".*-instalacion.json") if m != propio))
    candidatas = (registradas_en(propio) | RETIRADAS) - {d.name for d in SKILLS.iterdir() if d.is_dir()} - MUDADAS - ajenas
    return sorted(n for n in candidatas if (DESTINO / n / "SKILL.md").is_file())


def quitar(nombres):
    """Las saca de skills sin borrarlas: quedan en ~/.claude/senior-retiradas por si hiciera falta recuperarlas."""
    guardado = DESTINO.parent / "senior-retiradas"
    guardado.mkdir(parents=True, exist_ok=True)
    sello = time.strftime("%Y%m%d-%H%M%S")
    for n in nombres:
        shutil.move(str(DESTINO / n), str(guardado / f"{n}-{sello}"))
    return guardado


def programa(nombre, *args):
    ruta = shutil.which(nombre)
    if not ruta:
        return None, ""
    try:
        p = subprocess.run([ruta, *args], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verificar", action="store_true", help="solo informar; no escribir nada")
    ap.add_argument("--python", default=None, help="intérprete a usar para los hooks y las dependencias")
    args = ap.parse_args()
    listo, falta, avisos = [], [], []

    if sys.version_info >= (3, 10):
        listo.append(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        falta.append("Python 3.10 o superior (instalarlo desde python.org y repetir)")
    codigo, salida = programa("git", "--version")
    (listo if codigo == 0 else falta).append(salida.splitlines()[0] if codigo == 0 else "Git (instalarlo desde git-scm.com y repetir)")
    codigo, salida = programa("gh", "--version")
    if codigo == 0:
        listo.append(salida.splitlines()[0])
        codigo_auth, _ = programa("gh", "auth", "status")
        if codigo_auth != 0:
            avisos.append("gh no tiene sesión iniciada: ejecutar `gh auth login` (necesario para Pull Requests)")
    else:
        avisos.append("`gh` no está instalado: solo hace falta para crear y fusionar Pull Requests (cli.github.com)")

    if not SKILLS.is_dir():
        falta.append(f"no se encontró la carpeta skills/ junto a instalar.py ({SKILLS})")
        pendientes = []
    else:
        pendientes = desactualizadas()
        retiradas = retiradas_instaladas()  # antes de reescribir el registro
        if retiradas and args.verificar:
            falta.append("skills retiradas del paquete todavía instaladas: " + ", ".join(retiradas) + " (`python instalar.py` las saca)")
        elif retiradas:
            print("Skills retiradas del paquete que se van a sacar: " + ", ".join(retiradas))
            avisos.append(f"saqué de las skills las retiradas del paquete ({', '.join(retiradas)}); no se borraron: están en {quitar(retiradas).as_posix()}")
        if (DESTINO / "senior-diseno").is_dir() and not (DESTINO / ".senior-diseno-instalacion.json").exists():
            avisos.append("el diseñador (senior-diseno, auditar-diseno) ahora es un paquete de diseño aparte: lo instalado se conserva; para actualizarlo, correr el instalador de ese paquete")
        if args.verificar:
            if (SKILLS / "senior-git" / "scripts" / "guardia_autoria.py").exists():
                avisos.extend(l.removeprefix("AVISO: ") for l in cargar_guardia().asegurar_instalacion())
            (falta if pendientes else listo).append(
                "skills instaladas al día en ~/.claude/skills" if not pendientes else
                "skills sin instalar o desactualizadas: " + ", ".join(pendientes) + " (ejecutar `python instalar.py`)")
        else:
            copiadas = instalar_skills()
            listo.append(f"{len(copiadas)} skills instaladas en {DESTINO}")
            cargar_guardia().escribir_manifiesto(SKILLS)

    if SKILLS.is_dir() and (SKILLS / "senior-git" / "scripts" / "guardia_autoria.py").exists():
        guardia = cargar_guardia()
        lineas, hay_falta = guardia.asegurar_claude(args.verificar)
        for l in lineas:
            (falta if l.startswith(("FALTA", "NO")) else listo).append(l)
        py = args.python or guardia.python_que_funciona() or sys.executable
    else:
        py = args.python or sys.executable

    # Token Diet es una dependencia blanda: si falta o es anterior a la 1.0.2 solo se avisa; senior sigue funcionando con lo suyo.
    espec_td = importlib.util.spec_from_file_location("senior_token_diet", RAIZ / "skills" / "senior" / "scripts" / "token_diet.py")
    modulo_td = importlib.util.module_from_spec(espec_td)
    espec_td.loader.exec_module(modulo_td)
    aviso_td = modulo_td.aviso()
    if aviso_td:
        avisos.append(aviso_td)
    else:
        listo.append(f"Token Diet {modulo_td.estado()['version']} instalada y con su hook de lectura activo (ella lee los PDF; senior le cede la auditoría)")

    print("Primeros pasos: estado de la instalación\n")
    for l in listo:
        print(f"  LISTO  {l}")
    for l in falta:
        print(f"  FALTA  {l}")
    for l in avisos:
        print(f"  AVISO  {l}")
    print("\nPasos que quedan en cada proyecto (los hace la skill o se hacen una vez por repositorio):")
    print("  - Identidad de Git, solo local, en cada repositorio: la skill usa la sesión de GitHub (gh auth login) y, si no")
    print("    hay ninguna, Claude pregunta en nombre de quién se hace el trabajo. No se usa la configuración global.")
    print("  - Los hooks de Git los prepara la skill al iniciar el proyecto.")
    print("  - Los hooks de Claude Code se aplican al abrir una sesión nueva si se registraron en esta ejecución.")
    if falta:
        print("\nResultado: faltan cosas (ver FALTA).")
        return 1
    print("\nResultado: todo listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
