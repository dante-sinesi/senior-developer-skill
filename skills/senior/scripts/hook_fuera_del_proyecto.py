#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): nada se crea fuera del directorio del proyecto sin autorización.

Regla máxima del paquete senior: los archivos, carpetas y descargas que Claude crea viven dentro del proyecto. Lo
temporal (muestras, capturas, pruebas, borradores) va en `.temporal/`, una carpeta que git ignora y que prepara
`temporal.py`. Si un caso puntual necesita salir del proyecto (un servidor local, una carpeta de otro programa),
el usuario lo autoriza de antemano.

Qué cuenta como «dentro del proyecto» (para no frenar trabajo legítimo):
  - la raíz de la sesión (CLAUDE_PROJECT_DIR) y la raíz del repositorio git del directorio de trabajo;
  - los proyectos hermanos: otros repositorios git que viven en la misma carpeta que el proyecto de la sesión
    (por ejemplo, otro proyecto del usuario dentro de su carpeta de trabajo). Se puede apagar con `permisos_hooks.py hermanos no`;
  - lo que el usuario autorizó de antemano (`/permitir <ruta>` en el chat o `permisos_hooks.py permitir`);
  - la memoria y los planes de Claude Code (`~/.claude/projects/*/memory/`, `~/.claude/plans/`).

Qué cubre:
  - Write, Edit y NotebookEdit: la ruta del archivo.
  - Bash y PowerShell, de forma aproximada: redirecciones (`>`, `>>`), mkdir, touch, New-Item, cp, mv, copy, move,
    tee, Set-Content, Add-Content, Out-File, curl -o, wget -O, Invoke-WebRequest -OutFile y `git clone <url> <destino>`.
    Las variables del propio comando (`D=.temporal/x; cp a $D/b`) se resuelven; una variable que no se puede resolver no
    se juzga (se deja pasar), salvo las del sistema como TEMP o APPDATA, que son siempre «afuera».
  - Del código que viaja dentro del comando (`python -c`, `node -e`, heredocs) ve las escrituras con una ruta literal
    (`open("/tmp/x", "w")`, `writeFileSync`, `Path(...).write_text`…). No ve lo que hace un script que está en un archivo
    ni rutas armadas con código: para eso está la regla escrita en la skill.

Qué decide: según el modo de `modo_hooks.py`. Por defecto («denegar») NO interrumpe: bloquea y le dice a Claude que escriba
en `.temporal/` y siga, y deja registrado lo bloqueado. En modo «preguntar» le pregunta al usuario y espera. La configuración de
los hooks la edita el usuario, no Claude: cualquier intento de cambiarla se deniega, pero LEERLA está permitido. Si algo falla
o no se puede juzgar, deja pasar. Solo biblioteca estándar.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SEPARADORES = re.compile(r"\|\||&&|[|;\n]")
TOKEN = re.compile(r"\"[^\"]*\"|'[^']*'|\S+")
REDIRECCION = re.compile(r"(?<![<>&\w-])(?:\d?>>?)\s*(?!&)[\"']?([^\s\"'|;&<>]+)")
CREAN = {"mkdir", "md", "touch", "new-item", "ni", "tee", "set-content", "sc", "add-content", "ac", "out-file"}
COPIAN = {"cp", "copy", "copy-item", "mv", "move", "move-item", "robocopy", "xcopy", "rsync", "ren", "rename-item"}
DESCARGAN = {"curl", "wget", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"}
OPCION_DESTINO = {"-o", "-O", "--output", "--output-document", "-outfile", "-out-file"}
SIN_EFECTO = {"/dev/null", "/dev/stdout", "/dev/stderr", "nul", "$null", "con"}
VARIABLE = re.compile(r"^(?:\$env:|\$\{env:|\$\{|\$|%)([A-Za-z_]\w*)")
ASIGNACION = re.compile(r"(?:^|[;&\n]\s*|\|\|\s*)(?:export\s+|set\s+)?\$?([A-Za-z_]\w*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s;&|=]+)")
SISTEMA = {"temp", "tmp", "tmpdir", "appdata", "localappdata", "userprofile", "homepath", "homedrive", "home", "programfiles",
           "programdata", "windir", "systemroot", "public", "systemdrive", "onedrive"}
DEL_PROYECTO = {"claude_project_dir", "pwd", "cd", "oldpwd"}
LECTURA = {"cat", "type", "get-content", "gc", "head", "tail", "less", "more", "ls", "dir", "get-childitem", "gci", "grep", "rg",
           "select-string", "findstr", "wc", "stat", "file", "jq", "test-path"}


def sin_exe(nombre):
    """Quita «.exe» (no se usa str.removesuffix: es de Python 3.9; se mantiene el código simple)."""
    return nombre[:-4] if nombre.endswith(".exe") else nombre


def raiz_del_proyecto(cwd):
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or ".", capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path(cwd or ".")


def raices_propias(cwd, raiz):
    """La raíz de la sesión y la del repositorio git del directorio de trabajo (si es otra)."""
    raices = [Path(raiz)]
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd or ".", capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            raices.append(Path(r.stdout.strip()))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return raices


def normal(ruta):
    return os.path.normcase(os.path.normpath(str(ruta))).replace("\\", "/")


def adentro(ruta, raiz):
    a, b = normal(ruta), normal(raiz).rstrip("/")
    return a == b or a.startswith(b + "/")


def de_claude(ruta):
    base = normal(Path.home() / ".claude")
    r = normal(ruta)
    return r.startswith(base + "/plans/") or bool(re.match(re.escape(base) + r"/projects/[^/]+/memory/", r))


def variables_del_comando(comando):
    """{nombre en minúscula: valor} de las asignaciones del propio comando (`D=.temporal/x`, `$d = "..."`)."""
    res = {}
    for m in ASIGNACION.finditer(comando):  # en orden: `D=/tm; D=${D}p` vale /tmp
        res[m.group(1).lower()] = sustituir(m.group(2).strip("\"'"), res)
    return res


def sustituir(texto, variables):
    """Reemplaza $NOMBRE y ${NOMBRE} por lo asignado en el mismo comando (hasta tres niveles)."""
    for _ in range(3):
        nuevo = re.sub(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)",
                       lambda m: variables.get((m.group(1) or m.group(2)).lower(), m.group(0)), texto)
        if nuevo == texto:
            break
        texto = nuevo
    return texto


def a_ruta(token, cwd):
    """Ruta absoluta del token o None si no es una ruta o no se puede juzgar. Una variable del sistema (TEMP, APPDATA…) es 'afuera'."""
    t = token.strip("\"'")
    if not t or t.startswith("-") and not t.startswith("-/"):
        return None
    if t.lower() in SIN_EFECTO or re.match(r"^[a-z][a-z0-9+.-]*://", t, re.IGNORECASE):
        return None
    m_var = VARIABLE.match(t)
    if m_var:
        nombre = m_var.group(1).lower()
        if nombre in DEL_PROYECTO:
            return None
        return Path("/__variable_de_entorno__") if nombre in SISTEMA else None  # una variable desconocida no se puede juzgar
    if len(t) > 2 and t[:2] in ("//", chr(92) * 2) and t[2] not in "/" + chr(92):  # ruta de red (UNC): siempre afuera, sin tocar la red
        return Path("/__ruta_de_red__")
    if t.startswith("~"):
        t = str(Path.home()) + t[1:]
    m = re.match(r"^/([a-zA-Z])(/.*)?$", t)  # /c/Users/... de Git Bash
    if m:
        t = f"{m.group(1).upper()}:{m.group(2) or '/'}"
    p = Path(t)
    if not p.is_absolute() and not os.path.isabs(t):
        p = Path(cwd or ".") / t
    return Path(os.path.abspath(str(p)))


HEREDOC = re.compile(r"<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")
CADENA = re.compile(r"\"[^\"]*\"|'[^']*'")


def partir_heredocs(comando):
    """(comando sin los cuerpos de heredoc que son solo texto, cuerpos que alimentan a un intérprete).

    Lo que va dentro de `cat > nota.md <<'EOF' … EOF` o de un cuerpo de Pull Request es texto: puede mencionar rutas, redirecciones o el nombre de
    un archivo sin que el comando haga nada con ellas. Lo que va dentro de `python - <<'E' … E` es código y se sigue analizando."""
    lineas, salida, codigos, i = comando.split("\n"), [], [], 0
    while i < len(lineas):
        linea = lineas[i]
        salida.append(linea)
        i += 1
        for delimitador in [m.group(2) for m in HEREDOC.finditer(linea)]:
            cuerpo = []
            while i < len(lineas) and lineas[i].strip() != delimitador:
                cuerpo.append(lineas[i])
                i += 1
            i += 1  # el delimitador de cierre
            if INTERPRETE_EN_LINEA.search(linea):
                codigos.append("\n".join(cuerpo))
    return "\n".join(salida), codigos


def blanquear_comillas(seg):
    """El segmento sin el texto entre comillas, salvo lo que es el destino de una redirección (`> "ruta"`): `-m "a > b"` no redirige nada."""
    def reemplazo(m):
        return m.group(0) if seg[:m.start()].rstrip().endswith(">") else '""'
    return CADENA.sub(reemplazo, seg)


def objetivos_de_shell(comando):
    """Textos que el comando usa como destino de una escritura (aproximado)."""
    res = []
    for seg in SEPARADORES.split(comando):
        res.extend(REDIRECCION.findall(blanquear_comillas(seg)))
        tokens = [t.strip("\"'") for t in TOKEN.findall(seg)]
        if not tokens:
            continue
        verbo = sin_exe(Path(tokens[0].replace("\\", "/")).name.lower())
        args = [t for t in tokens[1:] if not t.startswith("-") or t.startswith("-/")]
        if verbo in CREAN:
            res.extend(args)
        elif verbo in COPIAN and len(args) >= 2:
            res.append(args[-1])
        elif verbo in DESCARGAN:
            for i, t in enumerate(tokens[1:-1], 1):
                if t in OPCION_DESTINO or t.lower() in OPCION_DESTINO:
                    res.append(tokens[i + 1])
        elif verbo == "sed" and any(re.match(r"^-[a-zA-Z]*i", t) or t.startswith("--in-place") for t in tokens[1:]):
            posicionales = [t for t in tokens[1:] if not t.startswith("-")]
            res.extend(posicionales[1:])  # el primero es el guion de sed
        elif verbo in ("truncate", "shred", "install", "ln") and tokens[1:]:
            res.extend(t for t in tokens[1:] if not t.startswith("-"))
        elif verbo == "dd":
            res.extend(t[3:] for t in tokens[1:] if t.startswith("of="))
        elif verbo == "git" and len(tokens) > 3 and tokens[1] == "clone":
            posicionales = [t for t in tokens[2:] if not t.startswith("-")]
            if len(posicionales) >= 2:
                res.append(posicionales[-1])
    return res


# Lo que un intérprete escribe «por dentro» cuando el código va en el propio comando (python -c, node -e, heredoc):
# solo se ve el destino cuando es un texto literal que es una ruta.
INTERPRETE_EN_LINEA = re.compile(r"\b(?:python[\d.]*|py|node|php|perl|ruby|deno|bun)(?:\.exe)?\b")
ESCRIBE_EN_CODIGO = re.compile(
    r"\b(open|writeFileSync|writeFile|appendFileSync|appendFile|createWriteStream|file_put_contents|fopen|mkdirSync|mkdir|makedirs|"
    r"copyFileSync|copyfile|copy2|rename|rmtree|unlink)\s*\(\s*[rbfu]?([\"'])(.+?)\2"
    r"(?:\s*,\s*[\"']([^\"']*)[\"'])?")
PATH_ESCRIBE = re.compile(r"Path\(\s*[rbfu]?([\"'])(.+?)\1\s*\)\.(?:write_text|write_bytes|mkdir|touch)")
RUTA_ABSOLUTA = re.compile(r"^(?:[a-zA-Z]:[/\\]|/|~|//)")


def escrituras_en_codigo(comando):
    """Destinos literales de escrituras dentro de código que viaja en el comando (python -c, node -e, heredoc)."""
    if not INTERPRETE_EN_LINEA.search(comando):
        return []
    res = []
    for m in ESCRIBE_EN_CODIGO.finditer(comando):
        modo = m.group(4)
        if m.group(1) == "open" and (modo is None or not re.search(r"[wax+]", modo)):
            continue  # open(ruta) y open(ruta, "r") solo leen
        ruta = m.group(3).replace("\\\\", "/")
        if RUTA_ABSOLUTA.match(ruta):
            res.append(ruta)
    for m in PATH_ESCRIBE.finditer(comando):
        if RUTA_ABSOLUTA.match(m.group(2)):
            res.append(m.group(2).replace("\\\\", "/"))
    return res


# senior-ignore: ESCRIBE-AFUERA motivo: este archivo muestra rutas de ejemplo (/tmp/x) en sus expresiones y docstrings
# Segunda capa: un script guardado en un archivo. Antes de guardarlo (Write o Edit) y antes de ejecutarlo (`python x.py`, `node x.js`, `bash x.sh`,
# `powershell -File x.ps1`) se le aplican las mismas reglas que al código que viaja en el comando: sus escrituras a rutas literales absolutas.
# Lo que NO se ve (una ruta armada con código, `Path.home() / ...`, una variable de entorno) no se puede juzgar de forma estática: ahí la defensa
# es `permissions.blockWritesOutsideWorkingDirectories` (ver capas_extra.py).
EXT_CODIGO = {".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".php", ".rb", ".pl"}
EXT_SHELL = {".sh", ".bash", ".ps1", ".bat", ".cmd"}
INTERPRETES = re.compile(r"^(?:python[\d.]*|py|node|deno|bun|php|ruby|perl|bash|sh|zsh|pwsh|powershell)$")
MAX_SCRIPT = 200_000


MARCA = re.compile(r"senior-ignore:[ 	]*ESCRIBE-AFUERA[ 	]+motivo:[ 	]*\S")  # un script que menciona rutas de ejemplo (por ejemplo, las pruebas de este hook) lo declara con motivo


def literales_de_script(texto, sufijo):
    """Destinos literales de escrituras dentro del texto de un script, según su tipo. Un script con la marca `senior-ignore: ESCRIBE-AFUERA motivo` no se analiza."""
    sufijo = (sufijo or "").lower()
    if MARCA.search(texto):
        return []
    if sufijo in EXT_CODIGO:
        return escrituras_en_codigo("python " + texto)
    if sufijo in EXT_SHELL:
        variables = variables_del_comando(texto)
        return [sustituir(t, variables) for t in objetivos_de_shell(texto)]
    return []


def scripts_del_comando(comando, cwd):
    """Rutas de los archivos de script que el comando ejecuta con un intérprete (los que existen y no son enormes)."""
    res = []
    for seg in SEPARADORES.split(comando):
        tokens = [t.strip("\"'") for t in TOKEN.findall(seg)]
        while tokens and tokens[0].lower() in ("sudo", "env", "command", "time"):
            tokens = tokens[1:]
        if not tokens or not INTERPRETES.match(sin_exe(Path(tokens[0].replace("\\", "/")).name.lower())):
            continue
        resto, candidato = tokens[1:], None
        for i, a in enumerate(resto):
            if a.lower() in ("-file", "-f") and i + 1 < len(resto):
                candidato = resto[i + 1]
                break
            if not a.startswith("-") and Path(a).suffix.lower() in EXT_CODIGO | EXT_SHELL:
                candidato = a
                break
        ruta = a_ruta(candidato, cwd) if candidato else None
        try:
            if ruta is not None and Path(ruta).is_file() and Path(ruta).stat().st_size <= MAX_SCRIPT:
                res.append(Path(ruta))
        except OSError:
            continue
    return res


def fuera_del_proyecto(textos, cwd, raices, hermano=None):
    """Los textos que apuntan fuera de todas las raíces propias (y de un proyecto hermano, si `hermano` lo acepta)."""
    fuera = []
    for t in textos:
        ruta = a_ruta(t, cwd)
        if ruta is None or de_claude(ruta) or any(adentro(ruta, r) for r in raices):
            continue
        if hermano is not None and not str(ruta).startswith(("/__", "\\__")) and hermano(ruta):
            continue
        fuera.append(t.strip("\"'"))
    return fuera


CAMBIAN = CREAN | {"rm", "del", "erase", "remove-item", "ri", "rmdir", "unlink", "truncate", "shred", "clear-content", "clc",
                   "mv", "move", "move-item", "ren", "rename-item", "rename", "install", "ln"}  # todos sus argumentos son archivos que cambian
SUBCOMANDOS_QUE_CAMBIAN = {"modo", "permitir", "quitar", "limpiar", "hermanos"}
ESCRIBE_ALGO = re.compile(r"write|unlink|remove|rename|truncate|rmtree|[.]dump\(|open\s*\([^)]*,\s*[\"'][^\"']*[wax+]")


def es_la_configuracion(ruta, nombre):
    return ruta.strip("\"'").replace("\\", "/").rstrip("/").split("/")[-1] == nombre


def toca_configuracion(herramienta, entrada, comando, nombre):
    """True si se intenta CAMBIAR la configuración de los hooks. Leerla (cat, type, Get-Content…) está permitido, y mencionarla en un texto
    (un cuerpo de heredoc, un mensaje de commit o de Pull Request) tampoco la cambia: solo cuenta cuando es el DESTINO de un cambio."""
    if herramienta in ("Write", "Edit", "NotebookEdit"):
        return Path(str(entrada.get("file_path") or entrada.get("notebook_path") or "")).name == nombre
    sin_cuerpos, codigos = partir_heredocs(comando)
    for seg in SEPARADORES.split(sin_cuerpos):
        tokens = [t.strip("\"'") for t in TOKEN.findall(seg)]
        while tokens and tokens[0].lower() in ("sudo", "env", "command", "time"):
            tokens = tokens[1:]
        if not tokens:
            continue
        verbo = sin_exe(Path(tokens[0].replace("\\", "/")).name.lower())
        for i, t in enumerate(tokens):  # el script de permisos con un subcomando que cambia algo (su nombre es un argumento, no texto suelto)
            if Path(t.replace("\\", "/")).name == "permisos_hooks.py":
                resto = tokens[i + 1:]
                if resto[:1] == ["--raiz"]:
                    resto = resto[2:]
                if resto[:1] and resto[0] in SUBCOMANDOS_QUE_CAMBIAN:
                    return True
        args = [t for t in tokens[1:] if not t.startswith("-") or t.startswith("-/")]
        destinos = list(REDIRECCION.findall(blanquear_comillas(seg)))
        if verbo in CAMBIAN:
            destinos += args
        elif verbo in COPIAN and len(args) >= 2:
            destinos.append(args[-1])
        elif verbo == "sed" and any(re.match(r"^-[a-zA-Z]*i", t) or t.startswith("--in-place") for t in tokens[1:]):
            destinos += args[1:]
        elif verbo == "dd":
            destinos += [t[3:] for t in tokens[1:] if t.startswith("of=")]
        if any(es_la_configuracion(d, nombre) for d in destinos):
            return True
        if INTERPRETE_EN_LINEA.search(seg) and nombre in seg and ESCRIBE_ALGO.search(seg):  # python -c "open('…','w')…"
            return True
    return any(nombre in c and ESCRIBE_ALGO.search(c) for c in codigos)


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        herramienta = datos.get("tool_name")
        entrada = datos.get("tool_input") or {}
        cwd = datos.get("cwd") or os.getcwd()
        raiz = raiz_del_proyecto(cwd)
        if herramienta in ("Write", "Edit", "NotebookEdit"):
            textos = [str(entrada.get("file_path") or entrada.get("notebook_path") or "")]
            comando = ""
            contenido = str(entrada.get("content") or entrada.get("new_string") or entrada.get("new_source") or "")
            if contenido and Path(textos[0]).suffix.lower() in EXT_CODIGO | EXT_SHELL:
                try:  # si el archivo que se edita ya tiene la marca, un fragmento suyo tampoco se analiza
                    previo = Path(a_ruta(textos[0], cwd) or "").read_text(encoding="utf-8", errors="replace") if Path(a_ruta(textos[0], cwd) or "").is_file() else ""
                except OSError:
                    previo = ""
                if not MARCA.search(previo):
                    textos += literales_de_script(contenido, Path(textos[0]).suffix)  # el script que se va a guardar
        elif herramienta in ("Bash", "PowerShell"):
            comando = str(entrada.get("command", ""))
            variables = variables_del_comando(comando)
            sin_cuerpos, cuerpos_de_codigo = partir_heredocs(comando)
            textos = [sustituir(t, variables) for t in objetivos_de_shell(sin_cuerpos) + escrituras_en_codigo(sin_cuerpos + "\n" + "\n".join(cuerpos_de_codigo))]
            for script in scripts_del_comando(sin_cuerpos, cwd):  # el script guardado que se va a ejecutar
                textos += literales_de_script(script.read_text(encoding="utf-8", errors="replace"), script.suffix)
        else:
            return 0
        import modo_hooks
        toca_config = toca_configuracion(herramienta, entrada, comando, modo_hooks.NOMBRE)
        config = modo_hooks.cargar(raiz)

        def hermano(ruta):
            return bool(config.get("hermanos", True)) and modo_hooks.proyecto_hermano(raiz, ruta)
        fuera = [] if toca_config else fuera_del_proyecto([t for t in textos if t], cwd, raices_propias(cwd, raiz), hermano)
        fuera = [t for t in fuera if not modo_hooks.esta_permitido(raiz, a_ruta(t, cwd))]
    except Exception:  # noqa: BLE001 motivo: si algo falla, no se frena nada (en las pruebas SENIOR_HOOK_DEPURAR=1 lo hace visible)
        if os.environ.get("SENIOR_HOOK_DEPURAR") == "1":
            raise
        return 0
    if toca_config:
        print(modo_hooks.respuesta_fija("deny", "Los permisos de los hooks de senior los configura el usuario (`permisos_hooks.py` o escribiendo "
                                                 "`/permitir <ruta>` en el chat); no se pueden cambiar desde Claude, pero sí leer. Seguí con el resto del trabajo."))
        return 0
    if not fuera:
        return 0
    lista = ", ".join(fuera[:3]) + (f" y {len(fuera) - 3} más" if len(fuera) > 3 else "")
    pregunta = (f"Claude quiere crear algo fuera del proyecto ({raiz}): {lista}. La regla máxima de senior es trabajar "
                "dentro del proyecto: lo temporal va en `.temporal/` (git lo ignora; lo prepara temporal.py). "
                "¿Autorizás esta excepción?")
    destinos = ", ".join(f"{t} → {(Path(raiz) / '.temporal' / Path(t).name).as_posix()}" for t in fuera[:3])
    instruccion = (f"rehacé exactamente lo mismo dentro del proyecto y seguí desde ahí ({destinos}). Lo de paso va en `.temporal/` "
                   "(git lo ignora; `temporal.py` la prepara; se crea sola al escribir ahí): ni la carpeta de trabajo del entorno "
                   "ni la temporal del sistema, y los comandos posteriores usan esa ruta nueva. Si de verdad hace falta salir del proyecto "
                   "(un servidor local, la carpeta de otro programa), seguí sin ese paso, anotalo en `docs/pendientes.md` (o en `.temporal/pendientes.md` "
                   "si no hay docs/) y en tu resumen final dejá dicho que el usuario puede autorizarlo de antemano escribiendo en el chat "
                   "`/permitir <ruta>` (vos no podés).")
    print(modo_hooks.respuesta(raiz, "escritura fuera del proyecto", f"se intentó crear algo fuera del proyecto: {lista}", pregunta, instruccion))
    return 0


if __name__ == "__main__":
    sys.exit(main())
