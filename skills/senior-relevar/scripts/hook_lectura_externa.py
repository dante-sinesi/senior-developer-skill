#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): impide leer directamente documentos e imágenes externos.

Regla del paquete senior: ningún documento externo se lee sin convertirlo antes (convertir_fuentes.py) ni ninguna
imagen grande sin reducirla. Este hook lo hace obligatorio para la herramienta Read y, de forma aproximada, para
comandos de lectura de Bash y PowerShell (cat, type, Get-Content, head, tail, pdftotext…).

Qué cubre:
  - PDF, Word, Excel, PowerPoint, EPUB, RTF y OpenDocument: siempre (nunca son código).
  - HTML, JSON, CSV, XML, TXT y MD: solo dentro de una carpeta `documentos-externos/` (fuera de ella son código
    o configuración del proyecto y se leen normalmente).
  - Imágenes: las de más de 1024 px en su lado más largo (las chicas pasan; las reducidas por el conversor, también).
  - Siempre se puede leer lo que está en docs/fuentes/ (los .md convertidos y las imágenes reducidas).

Qué decide:
  - Bloquea (código 2) y le dice a Claude qué comando usar: `convertir_fuentes.py --importar <ruta>`, o leer el .md
    ya convertido.
  - EXCEPCIONES (PDF escaneado sin texto, documentos donde importa el diseño visual): no bloquea sino que le
    PREGUNTA AL USUARIO en la interfaz de Claude Code. Pasa lo mismo si el .md convertido quedó marcado con
    «lectura-directa: sugerida». El usuario también puede dejar escrita la autorización en
    documentos-externos/.lectura-directa (un nombre de archivo por línea); modificar esa lista también requiere
    su aprobación, para que Claude no pueda autorizarse solo.
  - Si algo falla o no se puede juzgar, deja pasar.
Con SENIOR_LECTURA_DIRECTA=1 no controla nada. Solo biblioteca estándar.
"""
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

BINARIOS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".epub", ".rtf", ".odt", ".ods", ".odp"}
TEXTUALES = {".html", ".htm", ".json", ".csv", ".xml", ".txt", ".md"}
IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
CARPETA = "documentos-externos"
MAX_PX = 1024
VERBOS = {"cat", "type", "get-content", "gc", "head", "tail", "more", "less", "strings", "xxd", "od", "pdftotext",
          "pandoc", "bat", "nl"}  # comandos que muestran el contenido de un archivo
SEPARADORES = re.compile(r"\|\||&&|[|;&\n]")
RUTA_EN_COMANDO = re.compile(r"""["']?([^\s"'|;&<>]+\.(?:pdf|docx?|xlsx?|pptx?|epub|rtf|od[tsp]|html?|json|csv|xml|txt|md))["']?""", re.IGNORECASE)


def dimensiones(ruta):
    """(ancho, alto) leyendo solo la cabecera del archivo, o None si no se puede determinar."""
    try:
        with open(ruta, "rb") as f:
            cab = f.read(32)
            ext = Path(ruta).suffix.lower()
            if cab[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", cab[16:24])
            if cab[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", cab[6:10])
            if cab[:2] == b"BM":
                ancho, alto = struct.unpack("<ii", cab[18:26])
                return abs(ancho), abs(alto)
            if cab[:4] == b"RIFF" and cab[8:12] == b"WEBP":
                if cab[12:16] == b"VP8X":
                    return (int.from_bytes(cab[24:27], "little") + 1, int.from_bytes(cab[27:30], "little") + 1)
                if cab[12:16] == b"VP8 ":
                    f.seek(26)
                    a, b = struct.unpack("<HH", f.read(4))
                    return a & 0x3FFF, b & 0x3FFF
                if cab[12:16] == b"VP8L":
                    f.seek(21)
                    bits = int.from_bytes(f.read(4), "little")
                    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if cab[:2] == b"\xff\xd8" or ext in (".jpg", ".jpeg"):
                f.seek(2)
                while True:
                    marca = f.read(2)
                    if len(marca) < 2 or marca[0] != 0xFF:
                        return None
                    tam = struct.unpack(">H", f.read(2))[0]
                    if marca[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        _, alto, ancho = struct.unpack(">BHH", f.read(5))
                        return ancho, alto
                    f.seek(tam - 2, 1)
    except (OSError, struct.error):
        return None
    return None


def raiz_de(ruta, cwd):
    """Raíz del proyecto: el ancestro que contiene documentos-externos/, .git o docs; si no, el directorio de trabajo."""
    for p in [ruta.parent, *ruta.parents]:
        if (p / CARPETA).is_dir() or (p / ".git").exists() or (p / "docs").is_dir():
            return p
    return Path(cwd or ".")


def en_carpeta(ruta, nombre):
    return nombre in ruta.parts


def en_fuentes(ruta):
    partes = [p.lower() for p in ruta.parts]
    return any(a == "docs" and b == "fuentes" for a, b in zip(partes, partes[1:]))


def autorizado(ruta, raiz):
    lista = raiz / CARPETA / ".lectura-directa"
    try:
        nombres = {l.strip().lower() for l in lista.read_text(encoding="utf-8", errors="replace").splitlines()
                   if l.strip() and not l.lstrip().startswith("#")}
    except OSError:
        return False
    return ruta.name.lower() in nombres or str(ruta).lower() in nombres


def hash_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def estado_conversion(ruta, raiz):
    """(ruta del .md si está convertido y al día, marca de lectura directa sugerida o '')."""
    base = re.sub(r"[^\w\-.]+", "_", ruta.stem, flags=re.UNICODE).strip("_") or "documento"
    for candidato in sorted((raiz / "docs" / "fuentes").glob(base + "*.md")):
        try:
            cab = candidato.read_text(encoding="utf-8", errors="replace")[:700]
            m = re.search(r"(?m)^sha256:\s*([0-9a-f]{64})", cab)
            if m and m.group(1) == hash_de(ruta):
                s = re.search(r"(?m)^lectura-directa:\s*(.+)$", cab)
                return candidato, (s.group(1).strip() if s else "")
        except OSError:
            continue
    return None, ""


def conversor():
    return Path(__file__).resolve().with_name("convertir_fuentes.py")


def decidir(ruta, cwd, es_shell=False):
    """Devuelve None (deja pasar), ('negar', mensaje) o ('preguntar', mensaje)."""
    ext = ruta.suffix.lower()
    if en_fuentes(ruta):
        return None
    if ext in BINARIOS:
        cubierto = True
    elif ext in TEXTUALES:
        cubierto = en_carpeta(ruta, CARPETA) and ruta.name.lower() != "leeme.md"
    elif ext in IMAGENES and not es_shell:
        d = dimensiones(ruta)
        if d is None:
            if ruta.exists() and ruta.stat().st_size <= 150_000:
                return None  # una imagen chica no pesa lo suficiente como para frenar el trabajo
            comando_img = f'python "{conversor().as_posix()}" --importar "{ruta}"'
            return "negar", (f"No se pudo medir la imagen {ruta.name} (formato no reconocido) y pesa más de 150 KB. Copiarla y reducirla con: {comando_img} "
                             "y leer la copia de docs/fuentes/imagenes/. Si el conversor tampoco puede abrirla, decírselo al usuario en el resumen y seguir sin ella.")
        if max(d) <= MAX_PX:
            return None
        cubierto = True
    else:
        cubierto = False
    if not cubierto:
        return None
    raiz = raiz_de(ruta, cwd)
    if autorizado(ruta, raiz):
        return None
    comando = f'python "{conversor().as_posix()}" --importar "{ruta}"'
    if ext in IMAGENES:
        d = dimensiones(ruta)
        return "negar", (f"La imagen {ruta.name} mide {d[0]}x{d[1]} px y las imágenes externas no se leen sin reducirlas "
                         f"a un máximo de {MAX_PX} px (ahorra entre 50 % y 75 % de tokens). Copiarla y reducirla con: {comando} "
                         "y leer la copia de docs/fuentes/imagenes/. Si hace falta más detalle, pedirle al usuario un máximo "
                         "mayor con --max-px.")
    if ruta.exists() and en_carpeta(ruta, CARPETA):
        md, marca = estado_conversion(ruta, raiz)
        if md is not None and marca:
            return "preguntar", (f"{ruta.name} se convirtió, pero quedó marcado «{marca}»: puede ser un PDF escaneado o un "
                                 "documento donde importa el diseño. ¿Se permite leer el original?")
        if md is not None:
            return "negar", (f"{ruta.name} ya está convertido: leer {md.as_posix()} en lugar del original "
                             "(los documentos externos no se leen directo).")
    return "negar", (f"{ruta.name} es un documento externo y no se lee directo: primero se convierte. Copiarlo y convertirlo con: "
                     f"{comando} y leer el .md resultante en docs/fuentes/. Excepciones (PDF escaneado sin texto o diseño visual "
                     "que importa): pedirle al usuario que autorice la lectura del original; no se resuelve por cuenta propia.")


def rutas_de_shell(comando, cwd):
    """Rutas cubiertas que lee un comando de lectura. Se mira cada segmento (separado por | ; &&) por separado:
    solo cuenta si el comando del segmento es de los que muestran contenido y la ruta es su argumento."""
    res = []
    for segmento in SEPARADORES.split(comando):
        palabras = segmento.strip().split()
        while palabras and palabras[0].lower() in ("sudo", "env", "command", "time"):
            palabras = palabras[1:]
        if not palabras or Path(palabras[0].strip("\"'")).name.lower() not in VERBOS:
            continue
        for m in RUTA_EN_COMANDO.finditer(" ".join(palabras[1:])):
            p = Path(m.group(1))
            res.append(p if p.is_absolute() else Path(cwd or ".") / p)
    return res


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    if os.environ.get("SENIOR_LECTURA_DIRECTA") == "1":
        return 0
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        herramienta = datos.get("tool_name")
        entrada = datos.get("tool_input") or {}
        cwd = datos.get("cwd")
        resultado = None
        if herramienta == "Read":
            ruta = entrada.get("file_path")
            if ruta:
                resultado = decidir(Path(ruta) if Path(ruta).is_absolute() else Path(cwd or ".") / ruta, cwd)
        elif herramienta in ("Write", "Edit"):
            ruta = str(entrada.get("file_path", ""))
            if Path(ruta).name == ".lectura-directa":
                resultado = ("preguntar", "Claude quiere modificar la lista de originales que se pueden leer directo "
                                          f"({ruta}). ¿Lo autorizás?")
        elif herramienta in ("Bash", "PowerShell"):
            for ruta in rutas_de_shell(str(entrada.get("command", "")), cwd):
                resultado = decidir(ruta, cwd, es_shell=True)
                if resultado:
                    break
    except Exception:  # noqa: BLE001 - si algo falla, no se bloquea nada
        return 0
    if not resultado:
        return 0
    accion, mensaje = resultado
    if accion == "preguntar":
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "senior" / "scripts"))
            import modo_hooks
            raiz = modo_hooks.raiz_del_proyecto(cwd)
            instruccion = ("esa lectura directa necesita la autorización del usuario y no se resuelve por cuenta propia: anotá en `docs/pendientes.md` "
                           "qué original hay que leer y por qué, y trabajá con el .md convertido o con lo demás.")
            print(modo_hooks.respuesta(raiz, "lectura de documentos externos", mensaje, mensaje, instruccion))
        except Exception:  # noqa: BLE001 motivo: si falta modo_hooks se conserva el comportamiento de preguntar
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                     "permissionDecisionReason": mensaje}}, ensure_ascii=False))
        return 0
    print("BLOQUEADO por la regla de documentos externos: " + mensaje, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
