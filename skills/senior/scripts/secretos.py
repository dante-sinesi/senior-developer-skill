#!/usr/bin/env python3
"""Detector de claves, credenciales y datos personales antes de que lleguen a GitHub.

Es el motor de tres barreras: el hook `pre-commit` y el `pre-push` de git (revisan lo que se va a commitear y todo lo que se
va a subir, commit por commit), el hook de Claude Code (`hook_secretos_claude.py`) y el chequeo `secretos` del verificador.
Nunca imprime un valor completo: muestra el principio y el largo (`AKIA…(20)`), o «dato oculto» para datos personales.

Uso:
    python secretos.py staged  [--raiz .]              # lo preparado para el próximo commit (pre-commit)
    python secretos.py rango <args de git log>         # commits de un rango, p. ej. `origin/main..HEAD`
    python secretos.py todo    [--raiz .]              # todo lo versionado y lo que git todavía no ignora
    python secretos.py gitignore [--aplicar] [--raiz .]  # comprueba (y con --aplicar completa) el .gitignore de secretos
    python secretos.py github  [--raiz .]              # ¿están activos el escaneo de secretos y la protección de subida?

Qué detecta:
  - Claves y tokens con formato conocido (AWS, GitHub, Anthropic, OpenAI, Stripe, Slack, Google, SendGrid, npm, JWT),
    claves privadas y credenciales dentro de una dirección (`postgres://usuario:<clave>@servidor`).
  - Credenciales asignadas como texto (`password = "..."`, `api_key: '...'`), salvo valores de ejemplo o marcadores.
  - Datos personales: números de tarjeta (con control Luhn) y documentos de identidad (DNI, CUIL, CUIT, cédula).
  - Archivos que no deben versionarse: `.env` con valores, claves y certificados, `credentials.json`, estados de Terraform,
    bases de datos locales y volcados con muchos datos (SQL con muchos INSERT, CSV con muchos correos).

Un falso positivo se descarta con un comentario en la misma línea (o en la anterior): `senior-ignore: ID-DE-LA-ALERTA`.
Salida: 0 sin hallazgos, 1 con hallazgos. Solo biblioteca estándar.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".idea", ".vscode", ".temporal",
           "documentos-externos", "coverage", ".next"}
CEROS = "0" * 40
MAX_BYTES = 1_000_000
SALTAR_NOMBRES = ("package-lock.json", "composer.lock", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "go.sum", ".min.js", ".min.css")

VALOR_FALSO = re.compile(r"(?i)(example|ejemplo|changeme|cambiar|your|tu_|xxx|\*\*\*|<.*>|\$\{|%s|process\.env|getenv|environ|placeholder|dummy|sample|fake|falso)")

TOKENS = [
    ("SEC-SECRETO-AWS", "clave de acceso de AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("SEC-SECRETO-GITHUB", "token de GitHub", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("SEC-SECRETO-ANTHROPIC", "clave de API de Anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("SEC-SECRETO-OPENAI", "clave de API con formato sk-", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("SEC-SECRETO-STRIPE", "clave de Stripe en producción", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}\b")),
    ("SEC-SECRETO-SLACK", "token de Slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("SEC-SECRETO-GOOGLE", "clave de API de Google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("SEC-SECRETO-SENDGRID", "clave de SendGrid", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")),
    ("SEC-SECRETO-NPM", "token de npm", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("SEC-SECRETO-CLAVE-PRIVADA", "clave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("SEC-SECRETO-JWT", "token JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]
URL_CON_CLAVE = re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@\"']+:([^/\s:@\"']{4,})@[^/\s\"']+")
LITERAL = re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|apikey|access[_-]?key|auth[_-]?token|token|clave|contrasena|contraseña)\w*"
                     r"\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']")
TARJETA = re.compile(r"(?<![\w.])(\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}|3[47]\d{2}[ -]?\d{6}[ -]?\d{5})(?![\w])")
DOCUMENTO = re.compile(r"(?i)\b(?:dni|cuil|cuit|cedula|cédula|documento)\b\D{0,12}(\d{1,2}[.]?\d{3}[.]?\d{3})\b")
CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# archivos que no deben versionarse: (expresión sobre la ruta con «/», id, descripción)
ARCHIVOS = [
    (re.compile(r"(^|/)\.env(\.(?!example$|sample$|template$|dist$|defaults$)[^/]+)?$"), "SEC-ARCHIVO-ENV", "archivo .env con valores reales"),
    (re.compile(r"\.(pem|key|p12|pfx|jks|keystore)$", re.I), "SEC-ARCHIVO-CLAVE", "clave o certificado"),
    (re.compile(r"(^|/)(id_rsa|id_ed25519|id_ecdsa)$"), "SEC-ARCHIVO-CLAVE", "clave SSH privada"),
    (re.compile(r"(^|/)(\.netrc|\.pgpass|\.pypirc)$"), "SEC-ARCHIVO-CLAVE", "archivo de credenciales"),
    (re.compile(r"(^|/)(credentials|service[-_]?account[^/]*|client_secret[^/]*)\.json$", re.I), "SEC-ARCHIVO-CLAVE", "credenciales de un servicio"),
    (re.compile(r"\.tfstate(\.backup)?$|(^|/)terraform\.tfvars$"), "SEC-ARCHIVO-CLAVE", "estado o variables de Terraform"),
    (re.compile(r"\.(sqlite3?|db)$", re.I), "SEC-ARCHIVO-DATOS", "base de datos local"),
    (re.compile(r"\.(dump|bak)$", re.I), "SEC-ARCHIVO-DATOS", "copia o volcado de datos"),
]
VOLCADO_SQL = 20     # líneas INSERT para considerar que un .sql es un volcado de datos
VOLCADO_CSV = 50     # correos distintos para considerar que un .csv es una lista de personas

GITIGNORE_BASE = [
    ".env", ".env.*", "!.env.example", "!.env.sample", "!.env.template",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore",
    "credentials.json", "service-account*.json", "client_secret*.json",
    "*.tfstate", "*.tfstate.backup", "terraform.tfvars",
    ".netrc", ".pgpass", ".pypirc", "*.sqlite", "*.sqlite3", ".temporal/",
]
CABECERA_GITIGNORE = "# Secretos y datos sensibles (senior): nunca se versionan; los valores van en .env"


def luhn(digitos):
    total = 0
    for i, c in enumerate(reversed(digitos)):
        n = int(c)
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def tarjeta_valida(texto):
    d = re.sub(r"\D", "", texto)
    if len(d) not in (15, 16) or len(set(d)) < 4 or not luhn(d):
        return False
    return d[0] in "4" or d[:2] in {"34", "37", "65"} or d[:4] == "6011" or 51 <= int(d[:2]) <= 55 or 2221 <= int(d[:4]) <= 2720


def ocultar(valor):
    return f"{valor[:4]}…({len(valor)})" if len(valor) > 8 else "valor oculto"


def suprimida(id_alerta, actual, anterior):
    marca = f"senior-ignore: {id_alerta}"
    return marca in actual or marca in (anterior or "")


def hallazgos_de_linea(linea, anterior=""):
    """[(id, descripción, extracto)] de una línea de texto."""
    res = []
    for id_a, desc, rx in TOKENS:
        m = rx.search(linea)
        if m and not VALOR_FALSO.search(m.group(0)):
            res.append((id_a, desc, ocultar(m.group(0))))
    m = URL_CON_CLAVE.search(linea)
    if m and not VALOR_FALSO.search(m.group(1)):
        res.append(("SEC-SECRETO-URL", "credenciales dentro de una dirección", ocultar(m.group(1))))
    m = LITERAL.search(linea)
    if m and not VALOR_FALSO.search(m.group(1) + " " + linea) and len(set(m.group(1))) >= 4:
        res.append(("SEC-SECRETO-LITERAL", "credencial escrita como texto", ocultar(m.group(1))))
    m = TARJETA.search(linea)
    if m and tarjeta_valida(m.group(1)):
        res.append(("SEC-DATO-TARJETA", "número de tarjeta", "dato oculto"))
    if DOCUMENTO.search(linea):
        res.append(("SEC-DATO-DOCUMENTO", "documento de identidad", "dato oculto"))
    return [h for h in res if not suprimida(h[0], linea, anterior)]


def hallazgos_de_ruta(ruta):
    r = ruta.replace("\\", "/")
    return [(id_a, desc) for rx, id_a, desc in ARCHIVOS if rx.search(r)]


def hallazgos_de_volcado(ruta, lineas):
    """Un .sql con muchos INSERT o un .csv con muchos correos distintos es una copia de datos de personas."""
    r = ruta.lower()
    if r.endswith(".sql") and sum(1 for l in lineas if re.match(r"\s*INSERT\s+INTO", l, re.I)) >= VOLCADO_SQL:
        return [("SEC-DATO-VOLCADO", "volcado de base de datos con muchos registros")]
    if r.endswith(".csv") and len({c.lower() for l in lineas for c in CORREO.findall(l)}) >= VOLCADO_CSV:
        return [("SEC-DATO-VOLCADO", "lista con muchos correos de personas")]
    return []


def escanear_texto(ruta, texto):
    """Hallazgos [{id, archivo, linea, descripcion, extracto}] de un archivo completo (por ruta y por contenido)."""
    nombre = ruta.replace("\\", "/")
    if nombre.endswith(SALTAR_NOMBRES):
        return []
    res = [{"id": i, "archivo": nombre, "linea": 0, "descripcion": d, "extracto": ""} for i, d in hallazgos_de_ruta(nombre)]
    lineas = texto.splitlines()
    for i, l in enumerate(lineas):
        for id_a, desc, ext in hallazgos_de_linea(l, lineas[i - 1] if i else ""):
            res.append({"id": id_a, "archivo": nombre, "linea": i + 1, "descripcion": desc, "extracto": ext})
    for id_a, desc in hallazgos_de_volcado(nombre, lineas):
        res.append({"id": id_a, "archivo": nombre, "linea": 0, "descripcion": desc, "extracto": ""})
    return res


def git(raiz, *args):
    r = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def analizar_diff(texto, commit=""):
    """Hallazgos de las líneas AGREGADAS de un diff con contexto (`-U1`); el contexto sirve para el `senior-ignore` de la línea anterior."""
    res, archivo, anterior, n, lineas_por_archivo = [], "", "", 0, {}
    for l in texto.splitlines():
        if l.startswith("@@commit "):
            commit = l.split()[1][:8]
            archivo = ""
        elif l.startswith("+++ "):
            archivo = l[6:] if l.startswith("+++ b/") else ""
            anterior = ""
            if archivo:
                for id_a, desc in hallazgos_de_ruta(archivo):
                    res.append({"id": id_a, "archivo": archivo, "linea": 0, "descripcion": desc, "extracto": "", "commit": commit})
        elif l.startswith("@@"):
            m = re.search(r"\+(\d+)", l)
            n = int(m.group(1)) - 1 if m else 0
            anterior = ""
        elif archivo and not l.startswith(("---", "diff ", "index ", "\\")):
            if l.startswith("+"):
                n += 1
                if not archivo.endswith(SALTAR_NOMBRES):
                    lineas_por_archivo.setdefault(archivo, []).append(l[1:])
                    for id_a, desc, ext in hallazgos_de_linea(l[1:], anterior):
                        res.append({"id": id_a, "archivo": archivo, "linea": n, "descripcion": desc, "extracto": ext, "commit": commit})
                anterior = l[1:]
            elif l.startswith(" "):
                n += 1
                anterior = l[1:]
    for archivo, lineas in lineas_por_archivo.items():
        for id_a, desc in hallazgos_de_volcado(archivo, lineas):
            res.append({"id": id_a, "archivo": archivo, "linea": 0, "descripcion": desc, "extracto": "", "commit": commit})
    return res


def escanear_staged(raiz):
    return analizar_diff(git(raiz, "diff", "--cached", "-U1", "--no-color", "--no-ext-diff", "--diff-filter=AMR"))


def escanear_rango(raiz, argumentos):
    return analizar_diff(git(raiz, "log", "-p", "-U1", "--no-color", "--no-ext-diff", "--no-merges", "--diff-filter=AMR",
                             "--format=@@commit %H", *argumentos))


def revisar_push(raiz, lineas_stdin):
    """Hallazgos de todo lo que un `git push` va a subir (`lineas_stdin` es lo que git entrega al hook pre-push)."""
    res = []
    for linea in lineas_stdin:
        partes = linea.split()
        if len(partes) < 4 or partes[1] == CEROS:
            continue
        _, local, _, remoto = partes[:4]
        res += escanear_rango(raiz, [local, "--not", "--remotes"] if remoto == CEROS else [f"{remoto}..{local}"])
    return res


def archivos_del_proyecto(raiz):
    """Rutas de lo versionado y de lo que git todavía no ignora; sin git, un recorrido que salta las carpetas de paso."""
    salida = git(raiz, "ls-files", "-co", "--exclude-standard")
    if salida:
        return [l for l in salida.splitlines() if l and not set(Path(l).parts) & IGNORAR]
    return [p.relative_to(raiz).as_posix() for p in Path(raiz).rglob("*") if p.is_file() and not set(p.relative_to(raiz).parts) & IGNORAR]


def escanear_todo(raiz):
    res = []
    for rel in archivos_del_proyecto(raiz):
        p = Path(raiz) / rel
        try:
            if not p.is_file() or p.stat().st_size > MAX_BYTES:
                continue
            datos = p.read_bytes()
        except OSError:
            continue
        if b"\x00" in datos[:2048]:
            res += [{"id": i, "archivo": rel, "linea": 0, "descripcion": d, "extracto": ""} for i, d in hallazgos_de_ruta(rel)]
            continue
        res += escanear_texto(rel, datos.decode("utf-8-sig", errors="replace"))
    return res


def versionados_que_no_deben(raiz):
    """Archivos que git ya sigue y que no deberían estar versionados (un .env, una clave): ignorarlos no alcanza, hay que sacarlos y rotar."""
    return [{"id": i, "archivo": rel, "linea": 0, "descripcion": d + " (ya versionado)", "extracto": ""}
            for rel in git(raiz, "ls-files").splitlines() for i, d in hallazgos_de_ruta(rel)]


def gitignore_faltante(raiz):
    p = Path(raiz) / ".gitignore"
    existentes = {l.strip() for l in p.read_text(encoding="utf-8", errors="replace").splitlines()} if p.exists() else set()
    return [l for l in GITIGNORE_BASE if l not in existentes]


def completar_gitignore(raiz):
    faltan = gitignore_faltante(raiz)
    if not faltan:
        return []
    p = Path(raiz) / ".gitignore"
    previo = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    bloque = ("" if not previo or previo.endswith("\n") else "\n") + ("\n" if previo else "") + CABECERA_GITIGNORE + "\n" + "\n".join(faltan) + "\n"
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(bloque)
    return faltan


def mensaje_de_arreglo(hallazgos):
    return ("Cómo resolverlo: el valor va en `.env` (git lo ignora; se declara en `.env.example` con un valor falso) y el código lo lee de una variable "
            "de entorno. Si ya se subió, no alcanza con borrarlo: hay que rotar la clave. Si es un falso positivo, un comentario "
            "`senior-ignore: <ID> motivo` en esa línea (o en la anterior).")


def imprimir(hallazgos, salida=None):
    salida = salida or sys.stdout
    for h in hallazgos:
        donde = f"{h['archivo']}:{h['linea']}" if h["linea"] else h["archivo"]
        commit = f" (commit {h['commit']})" if h.get("commit") else ""
        extracto = f" [{h['extracto']}]" if h["extracto"] else ""
        print(f"  {h['id']} {donde}{commit}: {h['descripcion']}{extracto}", file=salida)


def gh_cmd():
    """El `gh` a usar: SENIOR_GH (lista JSON, para las pruebas) o el de la máquina."""
    env = os.environ.get("SENIOR_GH")
    if env:
        try:
            return list(json.loads(env))
        except ValueError:
            pass
    return ["gh"]


def _consultar_repo(raiz):
    """(datos, error): la respuesta de la API del repositorio al que apunta origin."""
    r = subprocess.run([*gh_cmd(), "api", "repos/{owner}/{repo}"], cwd=raiz, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None, (r.stderr or r.stdout).strip()[:200]
    try:
        return json.loads(r.stdout or "{}"), ""
    except ValueError:
        return None, "respuesta ilegible"


def estado_de_github(raiz):
    """(líneas, ok): ¿el repositorio tiene el escaneo de secretos y la protección de subida de GitHub? Consulta la API con `gh`.
    En un repositorio privado GitHub solo los ofrece con «GitHub Secret Protection» (de pago): se dice tal cual y no es un fallo que se pueda corregir."""
    datos, error = _consultar_repo(raiz)
    if datos is None:
        return ["No se pudo consultar GitHub (¿está `gh` instalado y con sesión iniciada?). Se revisa en Settings → Code security."], False

    def estado(clave):
        return ((datos.get("security_and_analysis") or {}).get(clave) or {}).get("status", "sin información")
    escaneo, proteccion = estado("secret_scanning"), estado("secret_scanning_push_protection")
    lineas = [f"GitHub: escaneo de secretos {escaneo}; protección de subida {proteccion}."]
    if escaneo == "enabled" and proteccion == "enabled":
        return lineas, True
    if datos.get("private"):
        lineas.append("AVISO: es un repositorio privado y GitHub solo ofrece ambas protecciones con «GitHub Secret Protection» (de pago). Hasta entonces las barreras "
                      "son locales: los hooks de git (que `--no-verify` saltearía) y el hook de Claude, que lo impide. Hacer público el repositorio o contratar el servicio las activa.")
        return lineas, True  # no hay nada que corregir sin decidir lo anterior
    lineas.append("Activarlas con `secretos.py github --activar` o en Settings → Code security (en repositorios públicos son gratis). Es la única barrera que no se saltea con `git push --no-verify`.")
    return lineas, False


def activar_en_github(raiz):
    """(líneas, ok): activa el escaneo de secretos y la protección de subida en un repositorio público. Cambia la configuración del repositorio en GitHub."""
    datos, error = _consultar_repo(raiz)
    if datos is None:
        return [f"No se pudo consultar GitHub: {error}"], False
    if datos.get("private"):
        return ["El repositorio es privado: GitHub solo ofrece el escaneo de secretos y la protección de subida con «GitHub Secret Protection» (de pago); no se activó nada."], False
    cuerpo = json.dumps({"security_and_analysis": {"secret_scanning": {"status": "enabled"}, "secret_scanning_push_protection": {"status": "enabled"}}})
    r = subprocess.run([*gh_cmd(), "api", "-X", "PATCH", "repos/{owner}/{repo}", "--input", "-"], cwd=raiz, input=cuerpo, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return [f"GitHub no la activó: {(r.stderr or r.stdout).strip()[:200]}"], False
    lineas, ok = estado_de_github(raiz)
    return ["Activada la protección de subida y el escaneo de secretos de GitHub."] + lineas, ok


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["staged", "rango", "todo", "gitignore", "github"])
    ap.add_argument("--activar", action="store_true", help="con «github»: activa el escaneo de secretos y la protección de subida (cambia la configuración del repositorio en GitHub)")
    ap.add_argument("resto", nargs="*", help="argumentos de git log (solo con «rango»)")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    if args.modo == "gitignore":
        faltan = gitignore_faltante(raiz)
        if not faltan:
            print("El .gitignore ya cubre los secretos y datos sensibles.")  # senior-ignore: SEC-LOG-SENSIBLE motivo: mensaje fijo, no imprime valores
            return 0
        if args.aplicar:
            completar_gitignore(raiz)
            print(f"Se agregaron {len(faltan)} líneas al .gitignore: {', '.join(faltan)}")
            return 0
        print(f"Al .gitignore le faltan {len(faltan)} líneas: {', '.join(faltan)}. Con --aplicar se agregan.")
        return 1
    if args.modo == "github":
        lineas, ok = activar_en_github(raiz) if args.activar else estado_de_github(raiz)
        print("\n".join(lineas))
        return 0 if ok else 1
    if args.modo == "staged":
        hallazgos = escanear_staged(raiz)
    elif args.modo == "rango":
        hallazgos = escanear_rango(raiz, args.resto or ["HEAD"])
    else:
        hallazgos = versionados_que_no_deben(raiz) + escanear_todo(raiz)
    if not hallazgos:
        print("Secretos: sin claves, credenciales ni datos personales a la vista.")  # senior-ignore: SEC-LOG-SENSIBLE motivo: mensaje fijo, no imprime valores
        return 0
    print(f"SECRETOS: {len(hallazgos)} hallazgos que no deben llegar a GitHub:", file=sys.stderr)  # senior-ignore: SEC-LOG-SENSIBLE motivo: mensaje fijo, no imprime valores
    imprimir(hallazgos, sys.stderr)
    print("  " + mensaje_de_arreglo(hallazgos), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
