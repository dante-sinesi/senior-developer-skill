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
import diagramas as dg  # noqa: E402
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


def leer(r):
    return Path(r).read_text(encoding="utf-8")


# ---------------- proponer, sobre un proyecto de ejemplo
proyectos = fx.crear_todo()
P = proyectos["php"]
(P / "README.md").write_text("# Tienda\n\nTienda de ejemplo.\n\n## Uso\n\nAbrir en el navegador.\n\n## Pruebas\n\nphpunit.\n", encoding="utf-8")
correr(SK / "documentar-proyecto" / "scripts" / "documentar.py", "todo", "--raiz", str(P), "--aplicar")
MM = P / ".s.mmd"
MM.write_text("sequenceDiagram\n    actor U as Cliente\n    participant C as PedidoController\n    U->>C: POST /pedidos\n    C-->>U: respuesta\n", encoding="utf-8")
correr(SK / "documentar-proyecto" / "scripts" / "documentar.py", "secuencia", "--titulo", "Crear un pedido", "--pregunta", "¿Qué pasa cuando un cliente crea un pedido?",
       "--archivo", str(MM), "--evidencia", "app/Http/Controllers/PedidoController.php:14", "--raiz", str(P))
MM.unlink()
antes = leer(P / "README.md")
rc, s = rdg("proponer", "--raiz", str(P))
chequear("proponer lista los candidatos con un texto sugerido y no escribe nada", rc == 0 and "Texto:" in s and leer(P / "README.md") == antes, s)
chequear("propone la arquitectura, la secuencia y el entidad-relación, no las clases", "modulos.md#1" in s and "secuencia-crear-un-pedido.md#1" in s and "entidad-relacion.md#1" in s and "clases-" not in s, s)
chequear("el texto de la arquitectura cuenta los módulos y explica las flechas", re.search(r"Los \d+ módulos del proyecto y qué módulo usa a cuál", s), s)
chequear("el de la secuencia parte de la pregunta del propio diagrama", "¿Qué pasa cuando un cliente crea un pedido?" in s, s)
chequear("el de entidad-relación cuenta las tablas", re.search(r"Las \d+ tablas del sistema", s), s)
chequear("avisa que los provisorios entran con la nota", "provisorio: entra con la nota" in s, s)
chequear("como mucho 3 propuestas", len(re.findall(r"^\s+- docs/", s, re.M)) == 3, s)
rc, s = rdg("proponer", "--aplicar", "docs/diagramas/modulos.md", "--raiz", str(P))
r = leer(P / "README.md")
chequear("--aplicar con una referencia agrega solo esa, con su texto sugerido y la nota de provisorio", rc == 0 and r.count("<!-- diagrama:") == 1 and "modulos.md" in r and "sin confirmar" in r
         and "módulos del proyecto y qué módulo usa a cuál" in r, s + r)
rc, s = rdg("proponer", "--raiz", str(P))
chequear("lo ya agregado deja de proponerse", "modulos.md" not in s, s)
rc, s = rdg("proponer", "--aplicar", "--raiz", str(P))
r = leer(P / "README.md")
chequear("--aplicar sin referencias agrega el resto de las propuestas", rc == 0 and r.count("<!-- diagrama:") == 3, s)
rc, s = rdg("estado", "--raiz", str(P))
chequear("lo agregado con textos sugeridos pasa el estado", rc == 0, s)
rc, s = rdg("proponer", "--aplicar", "docs/diagramas/noexiste.md", "--raiz", str(P))
chequear("una referencia que no está entre las propuestas se rechaza", rc != 0, s)
vacio = fx.BASE / "sin-diagramas"
vacio.mkdir(parents=True)
(vacio / "README.md").write_text("# X\n\nUn proyecto.\n", encoding="utf-8")
rc, s = rdg("proponer", "--raiz", str(vacio))
chequear("sin diagramas lo dice y no falla", rc == 0 and "No hay diagramas para proponer" in s, s)
chequear("la documentación de documentar-proyecto exige el visto bueno antes de aplicar", "solo si dice que sí" in leer(SK / "documentar-proyecto" / "SKILL.md") and "proponer --aplicar" in leer(SK / "documentar-proyecto" / "SKILL.md"))

# ---------------- el propio repositorio de la skill
README = leer(RAIZ / "README.md")
problemas, n = rd.estado(RAIZ)
chequear("el README del repositorio muestra 4 diagramas y todos coinciden con su fuente", n == 4 and problemas == [], problemas)
rc, s = correr(SK / "senior" / "scripts" / "diagramas.py", "--raiz", str(RAIZ))
chequear("los diagramas de docs/diagramas/ del repositorio son legibles", rc == 0 and "4 revisados" in s, s)
fuentes = sorted((RAIZ / "docs" / "diagramas").glob("*.md"))
chequear("hay cuatro diagramas fuente, todos confirmados (sin marca de generado)", len(fuentes) == 4 and not any("generado por documentar.py" in leer(f) for f in fuentes), [f.name for f in fuentes])
chequear("cada diagrama del README tiene su texto breve", all(b["texto_debajo"] and len(b["texto_debajo"]) <= 400 for b in rd.analizar_readme(README)))
chequear("la sección «Cómo funciona» está una sola vez y antes del Verificador", README.count("## Cómo funciona") == 1 and README.index("## Cómo funciona") < README.index("## Verificador"))
chequear("la lista numerada de «Flujo de trabajo» se reemplazó por el diagrama", "### Flujo de trabajo" not in README and "1. Leer el estado del proyecto." not in README)
chequear("la frase sobre el rigor según el tamaño del cambio se conserva", "El rigor se ajusta al tamaño del cambio" in README)
chequear("hay una arquitectura, un flujo y dos secuencias",
         sorted(c["tipo"] for c in rd.candidatos(RAIZ)) == ["flujo", "flujo", "secuencia", "secuencia"], [c["tipo"] for c in rd.candidatos(RAIZ)])
rc, s = correr(SK / "senior" / "scripts" / "verificar.py", "readme", "--raiz", str(RAIZ))
chequear("verificar.py readme del repositorio queda al día", "README: al día" in s or ("no se actualizó en este cambio" in s and "diagrama" not in s.lower()), s)  # con cambios sin commit el aviso de «README sin actualizar» es esperable
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(README) == [])
chequear("el README explica la propuesta con texto sugerido", "readme_diagramas.py proponer" in README)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
