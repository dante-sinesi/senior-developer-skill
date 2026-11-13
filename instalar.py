#!/usr/bin/env python3
"""Instalador del paquete senior: deja todo listo la primera vez (o en una máquina nueva).

Uso:
    python instalar.py                         # instala las skills y registra los hooks, y dice qué falta
    python instalar.py --instalar-dependencias # además instala markitdown y Pillow (tu aprobación explícita)
    python instalar.py --verificar             # solo informa el estado (incluye si lo instalado está al día con este repositorio); no escribe nada

Qué hace:
  1. Comprueba Python 3.10 o superior, Git, el CLI `gh` (opcional, para GitHub) y `pip`.
  2. Copia las skills de este repositorio a ~/.claude/skills, reemplazando las del paquete (no toca ninguna otra
     skill) y pasando los archivos de texto a fin de línea de Unix.
  3. Registra en ~/.claude/settings.json los cinco hooks globales de Claude Code (autoría, lectura de documentos
     externos, escritura fuera del proyecto, archivos protegidos y permisos desde el chat), conservando los ajustes que ya haya y con una copia de seguridad.
  4. Comprueba las dos bibliotecas de Python obligatorias para documentos e imágenes externos: `markitdown` y
     `Pillow`. Solo las instala con --instalar-dependencias: nunca lo hace por su cuenta.
  5. Imprime un informe con lo que quedó listo y los pasos que faltan (por ejemplo `gh auth login` y la identidad
     de Git de cada repositorio).
Los hooks de Git de cada proyecto no se instalan aquí: la skill los activa sola la primera vez que se usa en cada
repositorio (guardia_autoria.py asegurar). Solo biblioteca estándar. Código de salida: 0 todo listo, 1 faltan cosas.
"""
import argparse
import hashlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SKILLS = RAIZ / "skills"
DESTINO = Path.home() / ".claude" / "skills"
TEXTO = {".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".sh", ".yml", ".yaml"}
DEPENDENCIAS = (("markitdown", 'markitdown[all]', "documentos externos (PDF, Word, Excel, PowerPoint, HTML, JSON…)"),
                ("PIL", "pillow", "imágenes externas (reducción a 1024 px)"))


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


def modulo_disponible(py, modulo):
    try:
        return subprocess.run([py, "-c", f"import {modulo}"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


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
    ap.add_argument("--instalar-dependencias", action="store_true", help="instalar markitdown y Pillow con pip")
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

    faltantes = [(m, p, para) for m, p, para in DEPENDENCIAS if not modulo_disponible(py, m)]
    if faltantes and args.instalar_dependencias and not args.verificar:
        paquetes = [p for _, p, _ in faltantes]
        print(f"Instalando con pip (aprobado con --instalar-dependencias): {', '.join(paquetes)}")
        p = subprocess.run([py, "-m", "pip", "install", *paquetes], encoding="utf-8", errors="replace")
        if p.returncode != 0:
            avisos.append("pip no pudo instalar alguna dependencia: revisar el mensaje de arriba")
        faltantes = [(m, pk, para) for m, pk, para in DEPENDENCIAS if not modulo_disponible(py, m)]
    for m, p, para in DEPENDENCIAS:
        if (m, p, para) in faltantes:
            falta.append(f"biblioteca `{p}` para {para}: `{py} -m pip install \"{p}\"` o `python instalar.py --instalar-dependencias`")
        else:
            listo.append(f"biblioteca `{p}` disponible")

    # Token Diet: por ahora solo se avisa (la dependencia obligatoria llega al final del traspaso de mecánicas).
    espec_td = importlib.util.spec_from_file_location("senior_token_diet", RAIZ / "skills" / "senior" / "scripts" / "token_diet.py")
    modulo_td = importlib.util.module_from_spec(espec_td)
    espec_td.loader.exec_module(modulo_td)
    aviso_td = modulo_td.aviso()
    if aviso_td:
        avisos.append(aviso_td)
    else:
        listo.append(f"Token Diet {modulo_td.estado()['version']} instalada y con su hook de lectura activo (el de senior se hace a un lado)")

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
    print("  - Los hooks de Git y la carpeta documentos-externos/ los prepara la skill al iniciar el proyecto.")
    print("  - Los hooks de Claude Code se aplican al abrir una sesión nueva si se registraron en esta ejecución.")
    if falta:
        print("\nResultado: faltan cosas (ver FALTA).")
        return 1
    print("\nResultado: todo listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
