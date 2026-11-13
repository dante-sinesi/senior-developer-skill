#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): que las claves y los datos personales no pasen por el código ni por el historial.

Es la barrera de la primera hora: actúa antes de que algo se escriba (las de git actúan al commitear y al subir). Frena, sin
interrumpir el trabajo (no pregunta: bloquea y le explica a Claude qué hacer):
  - Escribir (Write, Edit, NotebookEdit) una clave, un token, una credencial o un dato personal en un archivo que va a git.
    Lo que se escribe en un archivo que git ignora (`.env`, `.temporal/`) no se juzga.
  - LEER un archivo de secretos (`.env`, claves, certificados): Read, Grep y comandos como `cat`, `type` o `Get-Content`. Lo que
    se lee queda en el contexto y en el historial de la sesión, que ya es una forma de filtrarlo.
  - Escribir un archivo de secretos con un comando (redirecciones, `tee`, `sed -i`…): `.env` se toca con el permiso del usuario.
  - `git add` de un archivo de secretos o con `-f` (forzar lo que .gitignore excluye).
  - Un mensaje de commit, de Pull Request o de issue (`git commit`, `gh pr`…) que contenga una clave.

`.env` y los demás archivos de secretos SÍ se pueden leer y modificar con el permiso del usuario, que lo da de antemano escribiendo
en el chat `/permitir .env` (Claude no puede darlo). Para el trabajo normal, `env_gestion.py` muestra los nombres de las variables
sin sus valores y declara variables nuevas: Claude lo usa, y le propone al usuario lo que no puede hacer solo.

Límites: no ve lo que un script guardado en un archivo lee o escribe, ni una clave partida o codificada. Para eso están los hooks de
git y, en el servidor, la protección de subida de GitHub. Si algo falla, deja pasar (con SENIOR_HOOK_DEPURAR=1 se ve el error).
Solo biblioteca estándar.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

COMANDOS_DE_TEXTO = re.compile(r"\bgit\s+(?:commit|tag)\b|\bgh\s+(?:pr|issue|release|gist)\b")
LEEN = {"cat", "type", "get-content", "gc", "head", "tail", "less", "more", "grep", "rg", "select-string", "findstr", "source", ".", "awk", "sed", "bat", "nl"}
ENV_GESTION = (AQUI / "env_gestion.py").as_posix()


def es_secreto(ruta):
    import hook_archivos_protegidos as hp
    return hp.categoria(ruta) == "secreto"


def absoluta(ruta, cwd):
    p = Path(ruta.strip("\"'"))
    return p if p.is_absolute() else Path(cwd or ".") / p


def ignorada_por_git(ruta, cwd):
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(ruta)], cwd=cwd or ".", capture_output=True, timeout=10)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def mensaje_lectura(ruta):
    return (f"{ruta} tiene secretos, y leerlo los pone en tu contexto y en el historial de la sesión. Para saber qué variables existen: "
            f"`python \"{ENV_GESTION}\" estructura` (muestra los nombres, no los valores). Si la tarea pide los valores, completala igual con los nombres "
            "y poné `<definido en .env>` donde iría el valor: los valores reales los agrega el usuario. Si de verdad hace falta leer el archivo, dejalo anotado en "
            "`docs/pendientes.md` (qué necesitás ver y por qué, y que el usuario puede autorizarlo con `/permitir <ruta de ese archivo>`; vos no podés) para que lo vea al volver, "
            "y seguí con el resto de la tarea sin esperar.")


def mensaje_escritura(ruta):
    return (f"{ruta} es un archivo de secretos y se toca con el permiso del usuario. Para declarar una variable nueva usá "
            f"`python \"{ENV_GESTION}\" declarar NOMBRE --comentario \"para qué sirve\"`: la agrega a `.env.example` con un valor falso y, si el usuario "
            "autorizó `.env`, también a `.env` sin valor. Si necesitás estructurar o editar `.env` a mano, dejalo anotado en "
            "`docs/pendientes.md` (qué variables y para qué, y que el usuario puede autorizarlo con `/permitir .env`; vos no podés) para que lo vea al volver, "
            "y seguí con el código leyendo la variable de entorno, sin esperar.")


def mensaje_secreto(hallazgos, ruta):
    lista = "; ".join(f"{h['id']}" + (f" en la línea {h['linea']}" if h["linea"] else "") for h in hallazgos[:3])
    return (f"se intentó escribir en {ruta} algo que parece una clave o un dato personal ({lista}). Nada de eso se escribe en archivos que van a GitHub: "
            "el código lee el valor de una variable de entorno (`os.environ`, `process.env`, `getenv`), la variable se declara en `.env.example` con un valor "
            f"falso (`python \"{ENV_GESTION}\" declarar NOMBRE`) y el valor real lo completa el usuario en `.env`. Si no es un secreto (un ejemplo, un dato de "
            "prueba), agregá en esa línea el comentario `senior-ignore: <ID> motivo` y volvé a escribirlo.")


def saltea_hooks_de_git(args):
    """True si los argumentos de un `git` (ya sin comillas ni el verbo) saltean los hooks: `commit`, `merge`, `push` o `am` con --no-verify (en `commit` también -n,
    solo o dentro de un grupo como -nm), o cualquier `-c core.hooksPath=…`. Una palabra dentro de un mensaje entre comillas es un solo argumento y no cuenta."""
    if any(a.lower().startswith("core.hookspath=") or a.lower().startswith("-ccore.hookspath=") for a in args):
        return True
    sub = next((a for a in args if not a.startswith("-") and "=" not in a), "")
    if sub not in ("commit", "merge", "push", "am"):
        return False
    resto = args[args.index(sub) + 1:]
    if "--no-verify" in resto:
        return True
    return sub == "commit" and any(re.fullmatch(r"-[A-Za-z]*n[A-Za-z]*", a) for a in resto)


def evaluar(herramienta, entrada, cwd, raiz):
    """(detalle, motivo) si hay que bloquear; None si pasa."""
    import modo_hooks
    import secretos

    def permitida(ruta):
        return modo_hooks.esta_permitido(raiz, ruta)

    if herramienta in ("Read", "Grep"):
        ruta = str(entrada.get("file_path") or entrada.get("path") or "")
        if ruta and es_secreto(ruta) and not permitida(absoluta(ruta, cwd)):
            return f"se intentó leer {ruta}", mensaje_lectura(ruta)
        return None
    if herramienta in ("Write", "Edit", "NotebookEdit"):
        ruta = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
        texto = str(entrada.get("content") or entrada.get("new_string") or entrada.get("new_source") or "")
        if not ruta or not texto or es_secreto(ruta) or ".temporal" in re.split(r"[\\/]+", ruta):
            return None  # los archivos de secretos los resuelve hook_archivos_protegidos
        destino = absoluta(ruta, cwd)
        hallazgos = [h for h in secretos.escanear_texto(destino.name, texto) if h["id"].startswith(("SEC-SECRETO", "SEC-DATO"))]
        if hallazgos and not ignorada_por_git(destino, cwd):
            return f"se intentó escribir un secreto o un dato personal en {ruta}", mensaje_secreto(hallazgos, ruta)
        return None
    if herramienta in ("Bash", "PowerShell"):
        comando = str(entrada.get("command", ""))
        if COMANDOS_DE_TEXTO.search(comando):
            hallazgos = [h for l in comando.splitlines() for h in secretos.hallazgos_de_linea(l) if h[0].startswith("SEC-SECRETO")]
            if hallazgos:
                return "se intentó enviar una clave en un mensaje de commit, Pull Request o issue", \
                    "el texto contiene algo que parece una clave. Los mensajes y descripciones se publican en GitHub: sacala del texto y, si ya está en un archivo, resolvelo ahí."
        import hook_fuera_del_proyecto as hf
        variables = hf.variables_del_comando(comando)
        for destino in (hf.sustituir(t, variables) for t in hf.objetivos_de_shell(comando)):
            if destino and es_secreto(destino) and not permitida(absoluta(destino, cwd)):
                return f"se intentó escribir {destino} con un comando", mensaje_escritura(destino)
        for seg in hf.SEPARADORES.split(comando):
            tokens = [t.strip("\"'") for t in hf.TOKEN.findall(seg)]
            while tokens and tokens[0].lower() in ("sudo", "env", "command", "time"):
                tokens = tokens[1:]
            if not tokens:
                continue
            verbo = hf.sin_exe(Path(tokens[0].replace("\\", "/")).name.lower())
            args = [hf.sustituir(t, variables) for t in tokens[1:]]
            if verbo in LEEN:
                for a in (a for a in args if not a.startswith("-")):
                    if es_secreto(a) and not permitida(absoluta(a, cwd)):
                        return f"se intentó leer {a} con un comando", mensaje_lectura(a)
            if verbo == "git" and args[:1] == ["add"]:
                forzado = [a for a in args[1:] if a in ("-f", "--force")]
                secretos_a_subir = [a for a in args[1:] if not a.startswith("-") and es_secreto(a)]
                if forzado or secretos_a_subir:
                    return "se intentó agregar a git un archivo de secretos o forzar lo que .gitignore excluye", \
                        ("`git add` de un archivo de secretos o con `-f` salta la protección de .gitignore. Lo que git ignora no se fuerza; "
                         "si de verdad hay que versionarlo (por ejemplo, un archivo de ejemplo), dejalo anotado en `docs/pendientes.md` para que lo haga el usuario y seguí sin ese paso.")
            if verbo == "git" and saltea_hooks_de_git(args):
                return "se intentó saltear los hooks de git (--no-verify o hooksPath)",                     ("los hooks de git (secretos y autoría) existen para que ninguna clave llegue a GitHub y no se saltean. Si dan un falso positivo, resolvelo ahí: sacá el valor "
                     "o marcá la línea con `senior-ignore: ID motivo`; si fallan por otra causa, anotalo en `docs/pendientes.md` y seguí con otro paso. Corré el mismo comando sin `--no-verify`.")
    return None


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        cwd = datos.get("cwd") or os.getcwd()
        import modo_hooks
        raiz = modo_hooks.raiz_del_proyecto(cwd)
        resultado = evaluar(datos.get("tool_name"), datos.get("tool_input") or {}, cwd, raiz)
    except Exception:  # noqa: BLE001 motivo: si algo falla, no se frena nada (SENIOR_HOOK_DEPURAR=1 lo hace visible)
        if os.environ.get("SENIOR_HOOK_DEPURAR") == "1":
            raise
        return 0
    if not resultado:
        return 0
    detalle, motivo = resultado
    veces = modo_hooks.registrar_bloqueo(raiz, "secretos", detalle)
    print(modo_hooks.respuesta_fija("deny", modo_hooks.razon_de_bloqueo("secretos", detalle, motivo, veces)))  # senior-ignore: SEC-LOG-SENSIBLE motivo: mensaje fijo, no imprime valores
    return 0


if __name__ == "__main__":
    sys.exit(main())
