#!/usr/bin/env python3
"""Plan de adopción de la metodología senior en un proyecto.

Uso:
    python plan_adopcion.py [--raiz .]             # muestra el plan; no escribe nada
    python plan_adopcion.py [--raiz .] --aplicar   # aplica la parte automática del plan

Detecta si el proyecto es NUEVO (casi sin código ni documentación) o EXISTENTE,
y qué le falta. Con --aplicar crea, sin pisar nada existente:
  - docs/ con ESTADO, pendientes, deuda técnica y carpetas de requisitos
  - README.md desde la plantilla (si no existe)
  - docs/relevamiento.md (solo en proyectos existentes)
  - el índice de documentación
Lo que requiere decisiones (stack, reglas de negocio, hook de apertura, plantilla
de PR, git init) solo se propone: nunca lo hace este script.
Solo biblioteca estándar.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", ".idea",
           ".vscode", "coverage", ".next"}
EXT_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".java", ".kt", ".cs", ".go", ".rs", ".rb", ".c",
              ".cc", ".cpp", ".h", ".hpp", ".swift", ".lua", ".sql", ".html", ".css", ".vue", ".sh", ".ps1"}


def correr(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=300)
    return (p.stdout + p.stderr).strip()


def inspeccionar(raiz):
    codigo, tests = 0, False
    for actual, carpetas, nombres in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR]
        for n in nombres:
            if Path(n).suffix.lower() in EXT_CODIGO:
                codigo += 1
                if "test" in n.lower() or "spec" in n.lower() or "test" in Path(actual).name.lower():
                    tests = True
    readme = next((n for n in ("README.md", "readme.md", "Readme.md") if (raiz / n).exists()), None)
    return {
        "codigo": codigo, "tests": tests, "readme": readme,
        "git": (raiz / ".git").exists(),
        "docs": (raiz / "docs").is_dir(),
        "estado": (raiz / "docs" / "ESTADO.md").exists(),
    }


def clasificar(info):
    return "nuevo" if info["codigo"] <= 3 and not info["docs"] else "existente"


def construir_plan(info, tipo):
    plan = []
    if not info["estado"]:
        plan.append(("auto", "Crear la estructura docs/ (ESTADO, pendientes, deuda técnica, requisitos, decisiones, diagramas, historial)"))
    if not info["readme"]:
        plan.append(("auto", "Crear README.md desde la plantilla (con secciones marcadas '(completar)')"))
    else:
        plan.append(("revisar", f"{info['readme']} existe y no se sobrescribe; se revisa con verificar.py readme"))
    if tipo == "existente":
        plan.append(("auto", "Relevamiento automático -> docs/relevamiento.md"))
        plan.append(("manual", "Lectura dirigida, convenciones y riesgos (senior-relevar)"))
        plan.append(("manual", "Presentar reglas de negocio hipotéticas para que el usuario las confirme"))
        plan.append(("manual", "Proponer tests de caracterización prioritarios" if not info["tests"]
                     else "Revisar la cobertura de tests existente y los de caracterización que falten"))
        plan.append(("manual", "Revisión inicial de seguridad (verificar.py seguridad)"))
    else:
        plan.append(("manual", "Preguntar el stack y la herramienta de tests; registrar el primer ADR"))
    plan.append(("auto", "Generar el índice de documentación (docs/INDEX.md)"))
    plan.append(("propuesta", "Hook de apertura que carga ESTADO.md (requiere aprobación aparte)"))
    plan.append(("propuesta", "Plantilla de Pull Request de GitHub (.github/pull_request_template.md)"))
    if not info["git"]:
        plan.append(("propuesta", "Inicializar git (la carpeta no es un repositorio)"))
    return plan


def aplicar(raiz, info, tipo):
    salidas = []
    iniciar = SKILLS / "senior-docs" / "scripts" / "iniciar_docs.py"
    if not info["estado"] and iniciar.exists():
        salidas.append(correr([sys.executable, "-I", str(iniciar), "--raiz", str(raiz)], raiz))
    if not info["readme"]:
        plantilla = SKILLS / "senior-docs" / "plantillas" / "readme.md"
        texto = plantilla.read_text(encoding="utf-8").replace("{{nombre}}", raiz.name) if plantilla.exists() \
            else f"# {raiz.name}\n\n(completar)\n"
        (raiz / "README.md").write_text(texto, encoding="utf-8", newline="\n")
        salidas.append("README.md creado desde la plantilla.")
    if tipo == "existente":
        relevar = SKILLS / "senior-relevar" / "scripts" / "relevar.py"
        destino = raiz / "docs" / "relevamiento.md"
        if relevar.exists() and not destino.exists():
            salidas.append(correr([sys.executable, "-I", str(relevar), "--raiz", str(raiz),
                                   "--salida", "docs/relevamiento.md"], raiz))
    indexador = SKILLS / "senior-memoria" / "scripts" / "indexar_docs.py"
    if indexador.exists() and (raiz / "docs").is_dir():
        salidas.append(correr([sys.executable, "-I", str(indexador), "indexar", "--raiz", str(raiz)], raiz))
    return salidas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    raiz = Path(args.raiz).resolve()
    info = inspeccionar(raiz)
    tipo = clasificar(info)
    if not args.aplicar:
        print(f"Proyecto {tipo}: {info['codigo']} archivos de código, "
              f"{'con' if info['tests'] else 'sin'} tests, {'con' if info['git'] else 'sin'} git, "
              f"{'con' if info['docs'] else 'sin'} docs/, README: {info['readme'] or 'no existe'}.")
        etiquetas = {"auto": "AUTOMÁTICO", "manual": "MANUAL", "revisar": "REVISAR", "propuesta": "PROPUESTA"}
        for tipo_accion, texto in construir_plan(info, tipo):
            print(f"  [{etiquetas[tipo_accion]}] {texto}")
        print("Nada se escribió. Con la aprobación del usuario: --aplicar (solo ejecuta lo AUTOMÁTICO).")
        return
    for linea in aplicar(raiz, info, tipo):
        if linea:
            print(linea)
    print("Parte automática aplicada. Quedan las acciones MANUAL y PROPUESTA del plan.")


if __name__ == "__main__":
    main()
