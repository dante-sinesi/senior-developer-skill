#!/usr/bin/env python3
"""Orden de las fuentes: un caso de uso o una secuencia cita un requisito o una decisión que existe, o dice que salió del código."""
import io
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
VERIFICAR = RAIZ / "skills" / "senior" / "scripts" / "verificar.py"
P = RAIZ / ".temporal" / "proy-fuentes"
SEQ = "```mermaid\nsequenceDiagram\n  A->>B: pedir\n```\n"
mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def _forzar(f, ruta, _):
    os.chmod(ruta, stat.S_IWRITE)
    f(ruta)


def escribir(ruta, texto):
    f = P / ruta
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(texto, encoding="utf-8", newline="\n")


def git(*args):
    subprocess.run(["git", "-c", "user.name=x", "-c", "user.email=x@example.com", "-c", "core.hooksPath=/dev/null", *args], cwd=P, check=True, capture_output=True)


def fuentes(*args):
    r = subprocess.run([sys.executable, str(VERIFICAR), "fuentes", "--raiz", str(P), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


shutil.rmtree(P, onerror=_forzar) if P.exists() else None
P.mkdir(parents=True)
git("init", "-q", "-b", "main")
rc, s = fuentes()
chequear("sin casos de uso ni secuencias no dice nada", rc == 0 and not s.strip(), (rc, s))

escribir("docs/requisitos/funcional/RF-001.md", "---\nid: RF-001\n---\n# RF-001: cobrar\n")
escribir("docs/requisitos/sistema/agenda.md", "# Agenda\n\n## RF-018 Agendar\n\n| RF-019 | reprogramar |\n")
escribir("docs/requisitos/funcional/RF-050.md", "# RF-050\n\nOrigen: inferido del código\n\n## Estado\n\nprovisorio\n")
escribir("docs/decisiones/ADR-001-base.md", "# ADR-001\n")
escribir("docs/diseno/notas/decisiones.md", "# Decisiones\n\n- **D-068** la superposición se calcula con todo el turno\n")
escribir("docs/casos-de-uso/viejo.md", "# Casos de uso viejos\n\nSin respaldo: `app/X.php:3`.\n")
escribir("docs/casos-de-uso/README.md", "# Índice\n")
git("add", "-A")
git("commit", "-qm", "chore: base")
rc, s = fuentes()
chequear("lo que ya estaba solo avisa", rc == 0 and "AVISO" in s and "docs/casos-de-uso/viejo.md" in s and "README" not in s, (rc, s))

git("checkout", "-q", "-b", "rama")
escribir("docs/casos-de-uso/nuevo.md", "# Caso nuevo\n\nSale del código: `app/Y.php:1`.\n")
rc, s = fuentes()
chequear("uno nuevo sin fuente falla, aun sin commitear", rc == 1 and "docs/casos-de-uso/nuevo.md" in s and "inferido del código, por confirmar" in s, (rc, s))
git("add", "-A")
git("commit", "-qm", "docs: caso")
rc, s = fuentes()
chequear("y sigue fallando ya commiteado en la rama", rc == 1 and "docs/casos-de-uso/nuevo.md" in s, (rc, s))

for nombre, texto, ok in (("un requisito por archivo", "Ver [[RF-001]].", True), ("un requisito definido en un título", "Cumple RF-018.", True),
                          ("uno definido en una tabla", "Cumple RF-019.", True), ("una ADR", "Por ADR-001.", True), ("una decisión D-", "Por D-068.", True),
                          ("la marca de inferido", "inferido del código, por confirmar", True), ("un requisito que no existe", "Ver RF-999.", False),
                          ("un requisito provisorio sacado del código", "Ver RF-050.", False)):
    escribir("docs/casos-de-uso/nuevo.md", f"# Caso nuevo\n\n{texto}\n")
    rc, s = fuentes()
    chequear(f"con {nombre}: {'pasa' if ok else 'falla'}", (rc == 0) == ok and (ok != ("nuevo.md" in s)), (rc, s))

escribir("docs/casos-de-uso/nuevo.md", "# Caso nuevo\n\nVer RF-001.\n")
for ruta in ("docs/secuencias/caja/cobro.md", "docs/diagramas/secuencia-cobro.md"):
    escribir(ruta, "# Cobro\n\n" + SEQ)
    rc, s = fuentes()
    chequear(f"una secuencia en {ruta.rsplit('/', 1)[0]} también se mira", rc == 1 and ruta in s, (rc, s))
    escribir(ruta, "# Cobro\n\nFlujo inferido leyendo el código; no está confirmado.\n\n" + SEQ)
    chequear("la que genera documentar-proyecto ya viene marcada", fuentes()[0] == 0, fuentes())
escribir("docs/diagramas/clases.md", "# Clases\n\n```mermaid\nclassDiagram\n  class A\n```\n")
chequear("un diagrama que no es de secuencia no se exige", fuentes()[0] == 0, fuentes())

docs = (RAIZ / "skills" / "senior-docs" / "SKILL.md").read_text(encoding="utf-8")
chequear("la regla está escrita en senior-docs, el núcleo y el brief",
         "inferido del código, por confirmar" in docs
         and all("evidencia, no fuente" in (RAIZ / "skills" / "senior" / r).read_text(encoding="utf-8") for r in ("SKILL.md", "references/brief-delegacion.md")))
shutil.rmtree(P, onerror=_forzar)
print("\nfallos:", mal)
sys.exit(1 if mal else 0)
