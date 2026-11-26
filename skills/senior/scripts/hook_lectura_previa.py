#!/usr/bin/env python3
"""Hook de Claude Code (PreToolUse): no se edita código sin haber leído antes la documentación del proyecto.

Vale solo en proyectos con `docs/ESTADO.md`. Cada lectura hecha con la herramienta Read de ese archivo, de `docs/INDEX.md` o de
un requisito o caso de uso se anota por sesión y por agente en `.temporal/senior-lecturas/` del proyecto. Al editar un archivo de
código (Write, Edit, NotebookEdit) se exige haber leído el estado y, si el proyecto tiene índice, requisitos o casos de uso,
al menos uno de ellos. Las marcas se borran al compactar o limpiar la conversación (lo hace el recordatorio de inicio).

El proyecto se busca por el archivo que se lee o edita, no por la carpeta de la sesión. No alcanza a `docs/`, tests ni
`.temporal/`, ni ve lo que cambia un comando de consola. `/docs-modo aviso` (del usuario) deja pasar y solo lo advierte.
Si algo falla, deja pasar (con SENIOR_HOOK_DEPURAR=1 el error se ve). Solo biblioteca estándar.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CARPETA = Path(".temporal") / "senior-lecturas"
EXT_CODIGO = {".py", ".ipynb", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".html", ".css", ".scss", ".php",
              ".java", ".kt", ".cs", ".go", ".rs", ".rb", ".c", ".cc", ".cpp", ".h", ".hpp", ".swift", ".lua", ".sql", ".sh", ".ps1"}
SIN_EXIGENCIA = {"docs", "tests", "test", "__tests__", "spec", "specs", ".temporal", "node_modules", "vendor"}
RE_TEST = re.compile(r"(^test_|_test\.|_spec\.|\.test\.|\.spec\.)", re.IGNORECASE)
CARPETAS_DE_REQUISITOS = ("requisitos", "casos-de-uso")


def raiz_de(archivo):
    """La primera carpeta, subiendo desde el archivo, que tiene docs/ESTADO.md."""
    for carpeta in archivo.parents:
        if (carpeta / "docs" / "ESTADO.md").is_file():
            return carpeta
    return None


def limpio(texto):
    return re.sub(r"[^A-Za-z0-9_-]", "", str(texto or ""))


def archivo_de_marcas(raiz, sesion, agente):
    return raiz / CARPETA / f"{sesion}__{agente or 'principal'}.json"


def leer_marcas(archivo):
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        return datos if isinstance(datos, list) else []
    except (OSError, ValueError):
        return []


def anotar(raiz, sesion, agente, clave):
    archivo = archivo_de_marcas(raiz, sesion, agente)
    marcas = leer_marcas(archivo)
    if clave in marcas:
        return
    archivo.parent.mkdir(parents=True, exist_ok=True)
    propio = archivo.parent / ".gitignore"
    if not propio.exists():  # la carpeta se ignora sola: no toca el .gitignore del proyecto
        propio.write_text("*\n", encoding="utf-8")
    archivo.write_text(json.dumps(marcas + [clave], ensure_ascii=False) + "\n", encoding="utf-8")


def olvidar(sesion, carpetas):
    """Borra las marcas de la sesión (y de sus subagentes) en los proyectos de esas carpetas, de las que las contienen y de hasta dos niveles hacia abajo."""
    sesion = limpio(sesion)
    if not sesion:
        return
    for carpeta in carpetas:
        base = Path(carpeta).resolve()
        candidatas = [base, *base.parents]
        for patron in ("*", "*/*", ".claude/worktrees/*"):
            candidatas += base.glob(patron)
        for c in candidatas:
            marcas = c / CARPETA
            if marcas.is_dir():
                for f in marcas.glob(f"{sesion}__*.json"):
                    f.unlink(missing_ok=True)


def relativa(raiz, archivo):
    return os.path.normcase(os.path.relpath(archivo, raiz)).replace("\\", "/")


def es_documento(rel):
    """True si leer ese archivo cuenta como lectura de la documentación."""
    partes = rel.split("/")
    return partes[0] == "docs" and (rel in ("docs/estado.md", "docs/index.md") or (len(partes) > 2 and partes[1] in CARPETAS_DE_REQUISITOS))


def es_codigo(rel):
    partes = rel.split("/")
    return (Path(rel).suffix.lower() in EXT_CODIGO and not SIN_EXIGENCIA & set(partes[:-1]) and not RE_TEST.search(partes[-1]))


def requisitos_a_leer(raiz):
    """Los documentos que sirven de segunda lectura, en el orden en que se sugieren."""
    docs = raiz / "docs"
    lista = [docs / "INDEX.md"] if (docs / "INDEX.md").is_file() else []
    for nombre in CARPETAS_DE_REQUISITOS:
        primero = next((f for f in sorted((docs / nombre).rglob("*.md")) if f.is_file()), None) if (docs / nombre).is_dir() else None
        if primero:
            lista.append(primero)
    return lista


def faltan(raiz, marcas):
    pendientes = []
    if "docs/estado.md" not in marcas:
        pendientes.append((raiz / "docs" / "ESTADO.md").as_posix())
    opciones = requisitos_a_leer(raiz)
    if opciones and not any(m != "docs/estado.md" and es_documento(m) for m in marcas):
        pendientes.append(opciones[0].as_posix() + (" (o los requisitos o casos de uso que el cambio afecta)" if len(opciones) > 1 or opciones[0].name == "INDEX.md" else ""))
    return pendientes


def main():
    for flujo in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        herramienta = datos.get("tool_name")
        if herramienta not in ("Read", "Write", "Edit", "NotebookEdit"):
            return 0
        entrada = datos.get("tool_input") or {}
        ruta = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
        sesion, agente = limpio(datos.get("session_id")), limpio(datos.get("agent_id"))
        if not ruta or not sesion:
            return 0
        cwd = datos.get("cwd") or os.getcwd()
        archivo = Path(ruta) if Path(ruta).is_absolute() else Path(cwd) / ruta
        archivo = Path(os.path.abspath(archivo))
        raiz = raiz_de(archivo)
        if raiz is None:
            return 0
        rel = relativa(raiz, archivo)
        if herramienta == "Read":
            if es_documento(rel) and archivo.is_file():
                anotar(raiz, sesion, agente, rel)
            return 0
        if not es_codigo(rel):
            return 0
        marcas = leer_marcas(archivo_de_marcas(raiz, sesion, agente))
        pendientes = faltan(raiz, marcas)
        if not pendientes:
            return 0
        import modo_hooks
        lista = "; ".join(pendientes)
        # el modo puede estar puesto en el proyecto del archivo o en la carpeta donde se abrió la sesión (donde guarda lo que el usuario escribe)
        if "aviso" in (modo_hooks.cargar(raiz)["docs_modo"], modo_hooks.cargar(modo_hooks.raiz_del_proyecto(cwd))["docs_modo"]):
            if "avisado" not in marcas:
                anotar(raiz, sesion, agente, "avisado")
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext":
                                  f"senior (lectura previa, en modo aviso): estás editando código sin haber leído {lista}. Conviene leerlo antes de seguir."}}, ensure_ascii=False))
            return 0
        razon = (f"BLOQUEADO por senior (lectura previa): se intentó editar {rel} sin haber leído la documentación del proyecto. Leé con la herramienta Read "
                 f"(un `cat` no cuenta): {lista}. Después repetí la edición. No es una pregunta ni hay que esperar al usuario. Se vuelve a pedir después de compactar o limpiar la conversación.")
        print(modo_hooks.respuesta_fija("deny", razon))
    except Exception:  # noqa: BLE001 motivo: si algo falla, el hook deja pasar y no frena nada (con SENIOR_HOOK_DEPURAR=1 el error se ve)
        if os.environ.get("SENIOR_HOOK_DEPURAR") == "1":
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
