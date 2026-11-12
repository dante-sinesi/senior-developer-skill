import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SK = RAIZ / "skills"
sys.path.insert(0, str(SK / "senior" / "scripts"))
sys.path.insert(0, str(SK / "senior-docs" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixtures_documentar as fx  # noqa: E402
import readme_diagramas as rd  # noqa: E402
import verificar  # noqa: E402

mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:500]))


def correr(script, *a):
    p = subprocess.run([sys.executable, "-X", "utf8", str(script), *a], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def rdg(*a):
    return correr(SK / "senior-docs" / "scripts" / "readme_diagramas.py", *a)


def doc(*a):
    return correr(SK / "documentar-proyecto" / "scripts" / "documentar.py", *a)


def leer(r):
    return Path(r).read_text(encoding="utf-8")


proyectos = fx.crear_todo()
P = proyectos["php"]
README = "# Tienda\n\nTienda de ejemplo.\n\n## Requisitos\n\nPHP 8.\n\n## Uso\n\nAbrir en el navegador.\n\n## Pruebas\n\nphpunit.\n\n## Documentación\n\nVer docs.\n"
(P / "README.md").write_text(README, encoding="utf-8")
doc("todo", "--raiz", str(P), "--aplicar")
MM = P / ".secuencia.mmd"
MM.write_text("sequenceDiagram\n    actor U as Cliente\n    participant C as PedidoController\n    participant F as Facturador\n    U->>C: POST /pedidos\n    C->>F: facturar(pedido)\n    F-->>C: total\n    C-->>U: respuesta\n", encoding="utf-8")
doc("secuencia", "--titulo", "Crear un pedido", "--pregunta", "¿Qué pasa cuando un cliente crea un pedido?", "--archivo", str(MM), "--evidencia", "app/Http/Controllers/PedidoController.php:14", "--raiz", str(P))
MM.unlink()

# ---------------- listar
rc, s = rdg("listar", "--raiz", str(P))
chequear("lista los diagramas con tipo, tamaño y estado", "docs/diagramas/modulos.md#1 · flujo" in s and "docs/diagramas/secuencia-crear-un-pedido.md#1 · secuencia" in s and "provisorio" in s, s)
chequear("recomienda la arquitectura y la secuencia, no las clases", re.search(r"modulos\.md#1.*recomendado", s) and re.search(r"secuencia-crear.*recomendado", s) and not re.search(r"clases-models\.md#1.*recomendado", s), s)
chequear("sin README en el proyecto no hay nada que revisar", rd.estado(fx.BASE / "vacio_sin_readme") == ([], 0))

# ---------------- agregar
rc, s = rdg("agregar", "docs/diagramas/modulos.md", "--raiz", str(P))
chequear("exige el texto breve", rc != 0 and "--texto" in s, s)
rc, s = rdg("agregar", "docs/diagramas/modulos.md", "--texto", "x" * 500, "--raiz", str(P))
chequear("rechaza un texto de más de 400 caracteres", rc != 0 and "500" in s, s)
rc, s = rdg("agregar", "docs/diagramas/noexiste.md", "--texto", "algo", "--raiz", str(P))
chequear("rechaza una fuente que no existe", rc != 0 and "no existe" in s, s)
rc, s = rdg("agregar", "docs/diagramas/modulos.md#4", "--texto", "algo", "--raiz", str(P))
chequear("rechaza un número de diagrama que no existe en el archivo", rc != 0 and "tiene 1 diagramas" in s, s)
rc, s = rdg("agregar", "docs/diagramas/modulos.md", "--texto", "Los módulos del sistema y cuál usa a cuál: las rutas llaman a los controladores, y estos a los servicios y a los modelos.", "--raiz", str(P))
r = leer(P / "README.md")
chequear("agrega el diagrama con marcas, título, nota de provisorio y mermaid", rc == 0 and "<!-- diagrama: docs/diagramas/modulos.md#1 -->" in r and "### Dependencias entre módulos" in r
         and "inferido del código y sin confirmar" in r and "```mermaid" in r and "<!-- /diagrama -->" in r, s + r)
chequear("crea la sección «Cómo funciona» antes de Pruebas, después de Uso", r.index("## Uso") < r.index("## Cómo funciona") < r.index("## Pruebas"), r)
chequear("el texto queda debajo del diagrama, fuera de las marcas", r.index("<!-- /diagrama -->") < r.index("Los módulos del sistema") < r.index("## Pruebas"))
chequear("no toca el resto del README", "# Tienda\n\nTienda de ejemplo." in r and "## Documentación\n\nVer docs." in r)
rc, s = rdg("agregar", "docs/diagramas/modulos.md", "--texto", "otra vez", "--raiz", str(P))
chequear("no agrega dos veces el mismo diagrama", rc != 0 and "ya está" in s, s)
rc, s = rdg("agregar", "docs/diagramas/secuencia-crear-un-pedido.md", "--texto", "Qué pasa al crear un pedido: el controlador pide al servicio que facture y responde con el total.", "--raiz", str(P))
r = leer(P / "README.md")
chequear("un segundo diagrama va dentro de la misma sección, sin duplicarla", rc == 0 and r.count("## Cómo funciona") == 1 and r.count("<!-- diagrama:") == 2 and r.index("<!-- diagrama: docs/diagramas/secuencia") < r.index("## Pruebas"), r)
rc, s = rdg("estado", "--raiz", str(P))
chequear("estado: todo coincide y tiene su texto", rc == 0 and "2, todos coinciden" in s, s)

# ---------------- límites
rc, s = rdg("agregar", "docs/diagramas/entidad-relacion.md", "--texto", "Las tablas y cómo se relacionan.", "--raiz", str(P))
chequear("un diagrama que cabe se agrega (4 tablas)", rc == 0, s)
grande = P / "docs/diagramas/grande.md"
nodos = "\n".join(f"    n{i} --> n{i + 1}" for i in range(14))
grande.write_text(f"# Grande\n\n### Un flujo grande\n\n¿Qué pasa en todo el sistema?\n\n```mermaid\nflowchart LR\n{nodos}\n```\n", encoding="utf-8")
rc, s = rdg("agregar", "docs/diagramas/grande.md", "--texto", "Muy grande.", "--raiz", str(P))
chequear("rechaza un diagrama que cabe en docs/ pero no en el README (15 nodos, máximo 12)", rc != 0 and "No cabe en el README" in s and "nodos" in s, s)
rc, s = rdg("listar", "--raiz", str(P))
chequear("listar avisa cuáles no caben", "grande.md#1" in s and "no cabe" in s, s)
extra = []
for i in range(3):
    f = P / "docs/diagramas" / f"secuencia-extra-{i}.md"
    f.write_text(f"# Extra {i}\n\n### Flujo extra {i}\n\n¿Qué pasa en el flujo {i}?\n\n```mermaid\nsequenceDiagram\n    A->>B: hola {i}\n    B-->>A: chau\n```\n", encoding="utf-8")
    extra.append(f)
rc1, _ = rdg("agregar", "docs/diagramas/secuencia-extra-0.md", "--texto", "Uno más.", "--raiz", str(P))
rc2, s2 = rdg("agregar", "docs/diagramas/secuencia-extra-1.md", "--texto", "Otro más.", "--raiz", str(P))
chequear("hasta 4 diagramas y el quinto se rechaza", rc1 == 0 and rc2 != 0 and "máximo 4" in s2, s2)

# ---------------- sincronización y estado
fuente = P / "docs/diagramas/modulos.md"
fuente.write_text(leer(fuente).replace("m4 -->|1| m0", "m4 -->|2| m0"), encoding="utf-8", newline="\n")
rc, s = rdg("estado", "--raiz", str(P))
chequear("estado detecta una copia desfasada de su fuente", rc != 0 and "difiere de su fuente" in s and "modulos.md#1" in s, s)
rc, s = rdg("sync", "--raiz", str(P))
r = leer(P / "README.md")
chequear("sync vuelve a copiar y conserva el texto de debajo", rc == 0 and "m4 -->|2| m0" in r and "Los módulos del sistema y cuál usa a cuál" in r, s)
rc, s = rdg("estado", "--raiz", str(P))
chequear("después de sync, el estado vuelve a estar en orden", rc == 0, s)
rc, s = rdg("sync", "--raiz", str(P))
chequear("sync repetido no cambia nada", "ya coinciden" in s, s)

# a mano en el README
r = leer(P / "README.md")
(P / "README.md").write_text(r.replace("m4 -->|2| m0", "m4 -->|9| m0", 1), encoding="utf-8", newline="\n")
rc, s = rdg("estado", "--raiz", str(P))
chequear("editar a mano la copia del README se detecta", rc != 0 and "difiere" in s, s)
rdg("sync", "--raiz", str(P))
(P / "README.md").write_text(leer(P / "README.md") + "\n```mermaid\nflowchart LR\n  a --> b\n```\n", encoding="utf-8", newline="\n")
rc, s = rdg("estado", "--raiz", str(P))
chequear("un diagrama escrito a mano fuera de las marcas se señala", rc != 0 and "escrito a mano" in s, s)
(P / "README.md").write_text(leer(P / "README.md").replace("\n```mermaid\nflowchart LR\n  a --> b\n```\n", ""), encoding="utf-8", newline="\n")
r = leer(P / "README.md")
(P / "README.md").write_text(re.sub(r"(<!-- /diagrama -->\n\n)Qué pasa al crear un pedido[^\n]*\n", r"\1", r, count=1), encoding="utf-8", newline="\n")
rc, s = rdg("estado", "--raiz", str(P))
chequear("un diagrama sin su texto se señala", rc != 0 and "sin el texto breve" in s, s)
(P / "README.md").write_text(r, encoding="utf-8", newline="\n")
rc, s = rdg("estado", "--raiz", str(P))
chequear("restaurado el texto vuelve a estar en orden", rc == 0, s)
fuente.unlink()
rc, s = rdg("estado", "--raiz", str(P))
chequear("si la fuente desaparece, se señala", rc != 0 and "no existe" in s, s)
rc, s = rdg("sync", "--raiz", str(P))
chequear("sync informa el error y sale con 1", rc == 1 and "ERROR" in s, s)

# ---------------- confirmar: la nota de «sin confirmar» desaparece
Q = proyectos["py"]
(Q / "README.md").write_text("# App\n\nUna app.\n\n## Pruebas\n\npytest sobre la carpeta tests.\n\n## Documentación\n\nVer [docs/INDEX.md](docs/INDEX.md).\n", encoding="utf-8")
doc("todo", "--raiz", str(Q), "--aplicar")
rdg("agregar", "docs/diagramas/entidad-relacion.md", "--texto", "Las dos tablas y su relación.", "--raiz", str(Q))
chequear("un diagrama provisorio entra con la nota visible", "sin confirmar" in leer(Q / "README.md"))
rc, s = doc("confirmar-diagrama", "docs/diagramas/entidad-relacion.md", "--raiz", str(Q))
er = leer(Q / "docs/diagramas/entidad-relacion.md")
chequear("confirmar quita la marca de generado y el tag inferido", rc == 0 and "generado por documentar.py" not in er and "confirmado por el usuario" in er and "tags: [diagrama]" in er, er[:400])
rc, s = rdg("estado", "--raiz", str(Q))
chequear("confirmado en docs, el README queda desfasado hasta el sync (la nota debe salir)", rc != 0 and "difiere" in s, s)
rdg("sync", "--raiz", str(Q))
chequear("después del sync el README ya no dice «sin confirmar»", "sin confirmar" not in leer(Q / "README.md"))
rc, s = doc("estructura", "--raiz", str(Q), "--aplicar")
chequear("un diagrama confirmado no se regenera", "confirmado por el usuario" in leer(Q / "docs/diagramas/entidad-relacion.md") and "Ya existían" in s, s)
rc, s = doc("confirmar-diagrama", "docs/diagramas/entidad-relacion.md", "--raiz", str(Q))
chequear("confirmar algo ya confirmado se rechaza", rc != 0 and "no es provisorio" in s, s)

# ---------------- quitar
rc, s = rdg("quitar", "docs/diagramas/entidad-relacion.md", "--raiz", str(Q))
r = leer(Q / "README.md")
chequear("quitar saca el diagrama y su texto, y deja el resto", rc == 0 and "<!-- diagrama" not in r and "Las dos tablas" not in r and "## Pruebas" in r and (Q / "docs/diagramas/entidad-relacion.md").exists(), r)

# ---------------- integración con verificar.py readme
class A:
    base = "HEAD"


import subprocess  # noqa: E402  (el proyecto de prueba tiene su propio git para no depender del árbol del repositorio)
for _c in (["init", "-q"], ["add", "."], ["-c", "user.name=prueba", "-c", "user.email=p@x.test", "commit", "-q", "-m", "base"]):
    subprocess.run(["git", *_c], cwd=Q, capture_output=True)
lin, ok = verificar.chequeo_readme(Q, A())
chequear("verificar.py readme sugiere mostrar diagramas cuando hay y el README no tiene ninguno", any("readme_diagramas.py listar" in l for l in lin), lin)
rdg("agregar", "docs/diagramas/modulos.md", "--texto", "Los módulos.", "--raiz", str(Q))
(Q / "docs/diagramas/modulos.md").write_text(leer(Q / "docs/diagramas/modulos.md").replace('"services (2)"', '"servicios (2)"'), encoding="utf-8", newline="\n")
import subprocess  # noqa: E402  (el proyecto de prueba tiene su propio git para no depender del árbol del repositorio)
for _c in (["init", "-q"], ["add", "."], ["-c", "user.name=prueba", "-c", "user.email=p@x.test", "commit", "-q", "-m", "base"]):
    subprocess.run(["git", *_c], cwd=Q, capture_output=True)
lin, ok = verificar.chequeo_readme(Q, A())
chequear("verificar.py readme falla con una copia desfasada", (not ok) and "diagramas:" in lin[0] and "difiere de su fuente" in lin[0], lin)
rdg("sync", "--raiz", str(Q))
import subprocess  # noqa: E402  (el proyecto de prueba tiene su propio git para no depender del árbol del repositorio)
for _c in (["init", "-q"], ["add", "."], ["-c", "user.name=prueba", "-c", "user.email=p@x.test", "commit", "-q", "-m", "base"]):
    subprocess.run(["git", *_c], cwd=Q, capture_output=True)
lin, ok = verificar.chequeo_readme(Q, A())
chequear("y vuelve a estar al día después del sync", "diagramas:" not in lin[0], lin)

# ---------------- documentación
sd = (SK / "senior-docs" / "SKILL.md").read_text(encoding="utf-8")
dg_md = (SK / "senior-docs" / "references" / "diagramas.md").read_text(encoding="utf-8")
rm = (RAIZ / "README.md").read_text(encoding="utf-8")
chequear("senior-docs explica los diagramas en el README", "readme_diagramas.py" in sd and "Diagramas en el README" in sd)
chequear("la referencia de diagramas fija los límites del README", "En el README" in dg_md and "hasta 4" in dg_md)
chequear("el README del paquete lo explica", "readme_diagramas.py" in rm and "Diagramas en el README" in rm)
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(rm) == [])
chequear("documentar-proyecto propone mostrarlos y confirmar", "readme_diagramas.py" in (SK / "documentar-proyecto" / "SKILL.md").read_text(encoding="utf-8")
         and "confirmar-diagrama" in (SK / "documentar-proyecto" / "SKILL.md").read_text(encoding="utf-8"))

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
