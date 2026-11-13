import io
import json
import re
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


def leer(r):
    return Path(r).read_text(encoding="utf-8")


# ---------------- abrir_en_navegador: una sola pestaña, aunque la ruta tenga espacios
ABRIR = SK / "senior" / "scripts" / "abrir_en_navegador.py"
CON_ESPACIOS = fx.BASE / "Mis Documentos" / "Proyecto Nuevo"
CON_ESPACIOS.mkdir(parents=True, exist_ok=True)
(CON_ESPACIOS / "índice final.html").write_text("<p>x</p>", encoding="utf-8")
rc, s = correr(ABRIR, str(CON_ESPACIOS / "índice final.html"), "--simular")
datos = json.loads(s)
chequear("una ruta con espacios y acentos es UNA pestaña", rc == 0 and len(datos["pestanas"]) == 1, s)
chequear("la dirección va codificada (sin espacios sueltos)", datos["pestanas"][0].startswith("file:///") and " " not in datos["pestanas"][0] and "%20" in datos["pestanas"][0], datos)
rc, s = correr(ABRIR, str(CON_ESPACIOS / "índice final.html"), "https://example.com/a b", "--simular")
chequear("también una dirección web, y cada destino es una pestaña", rc == 0 and len(json.loads(s)["pestanas"]) == 2, s)
rc, s = correr(ABRIR, "a", "b", "c", "d", "--simular")
chequear("más de 3 destinos se rechaza (así se evitan las decenas de pestañas)", rc != 0 and "máximo es 3" in s, s)
rc, s = correr(ABRIR, str(CON_ESPACIOS / "no existe.html"), "--simular")
chequear("un archivo que no existe se rechaza", rc != 0 and "no existe" in s, s)
rc, s = correr(ABRIR, "C:/Mis", "Documentos/Proyecto", "Nuevo/x.html", "--simular")
chequear("los pedazos de una ruta partida (lo que pasaba) se rechazan en lugar de abrir pestañas", rc != 0, s)

# ---------------- estimador de ancho: contra lo que midió Mermaid al dibujar
CICLO_ANTES = '''flowchart LR
    A["Leer el estado y relevar si hace falta"] --> B["Acordar un plan breve"]
    B --> C["Rama por cambio"]
    C --> D["Test rojo desde la regla de negocio"]
    D --> E["Código mínimo en verde"]
    E --> F["Refactor con tests en verde"]
    F --> G["Actualizar docs y README"]
    G --> H["verificar.py"]
    H -->|hallazgos| E
    H --> I["Pull Request con descripción completa"]
    I --> J{"¿Lo aprueba el usuario?"}
    J -->|ajustes| E
    J -->|sí| K["Fusión y estado al día"]'''
CICLO_VERTICAL = '''flowchart TB
    A["Leer estado y relevar"] --> B["Plan breve"]
    B --> C["Rama por cambio"]
    C --> D["Test rojo"]
    D --> E["Código mínimo en verde"]
    E --> F["Refactor"]
    F --> G["Docs y README"]
    G --> H["verificar.py"]
    H -->|hallazgos| E
    H --> I["Pull Request"]
    I --> J{"¿Aprobado?"}
    J -->|ajustes| E
    J -->|sí| K["Fusión y estado al día"]'''
FASES_H = '''flowchart LR
    P["Preparar<br/>estado, plan, rama"] --> C["Construir<br/>test, código, refactor"]
    C --> V["Verificar<br/>docs y verificar.py"]
    V --> R["Revisar y fusionar<br/>PR y aprobación"]
    R -->|ajustes| C'''
PAQUETE_ANTES = '''flowchart LR
    U["Usuario"] --> S["senior: principios, flujo y puntos de control"]
    S --> M["Método: tdd, refactor, docs, memoria, git, seguridad"]
    S --> R["Relevar y documentar un proyecto existente"]
    S --> D["Diseño: tarjeta de estilo, bosquejos y auditoría"]
    S --> C["Comandos: adoptar, cerrar sesión, revisar cambio, auditar consumo"]
    M --> P["Proyecto: docs/, README y código"]
    R --> P
    D --> P
    C --> P
    P --> V["verificar.py: chequeos sin gastar tokens"]
    H["Hooks globales: autoría, fuera del proyecto, protegidos y documentos externos"] -.-> P
    P --> G["GitHub: ramas, commits y Pull Requests"]'''
MEDIDOS = [("ciclo horizontal de 11 pasos", CICLO_ANTES, 2874), ("ciclo vertical de 11 pasos", CICLO_VERTICAL, 269), ("ciclo en 4 fases horizontales", FASES_H, 773),
           ("paquete horizontal", PAQUETE_ANTES, 1756)]
for nombre, cod, real in MEDIDOS:
    e = dg.ancho_estimado("flujo", cod)
    chequear(f"estimación de «{nombre}»: {e} px contra {real} medidos (±20 %)", e and abs(e - real) / real <= 0.20, e)
for nombre in ("confirmar-proyecto-existente", "hooks", "paquete"):
    pass
real = {"paquete": 979, "confirmar-proyecto-existente": 949, "hooks": 1065}
for nombre, medido in real.items():
    cod = re.search(r"```mermaid\n(.*?)```", leer(RAIZ / "docs" / "diagramas" / f"{nombre}.md"), re.S).group(1)
    e = dg.ancho_estimado(dg.tipo_diagrama(cod), cod)
    chequear(f"estimación del diagrama del repositorio «{nombre}»: {e} px contra {medido} medidos (±20 %)", e and abs(e - medido) / medido <= 0.20, e)
chequear("un flujo con ciclos no cuenta todos sus pasos como una sola fila (el defecto que tuvo el estimador)", dg.ancho_estimado("flujo", CICLO_VERTICAL) < 400)
chequear("las clases y el entidad-relación no se estiman", dg.ancho_estimado("clases", "classDiagram\n class A") is None and dg.ancho_estimado("er", "erDiagram\n A ||--o{ B : x") is None)

# ---------------- avisos
a = dg.aviso_de_ancho("flujo", CICLO_ANTES)
chequear("el flujo horizontal largo avisa que queda ilegible y propone vertical y fases", a and "ilegible" in a and "vertical" in a and "fases" in a, a)
chequear("el flujo vertical corto y el de fases no avisan", dg.aviso_de_ancho("flujo", CICLO_VERTICAL) is None and dg.aviso_de_ancho("flujo", FASES_H) is None)
SEC_ANCHA = "sequenceDiagram\n    participant A\n    participant B\n    A->>B: " + "un mensaje larguísimo que no entra en ningún lado " * 3 + "\n"
a = dg.aviso_de_ancho("secuencia", SEC_ANCHA)
chequear("una secuencia con un mensaje larguísimo avisa y propone acortar los mensajes", a and "mensajes" in a, a)
SEC_CHICA = "sequenceDiagram\n    actor U\n    participant S\n    U->>S: pedido\n    S-->>U: listo\n"
chequear("una secuencia corta no avisa", dg.aviso_de_ancho("secuencia", SEC_CHICA) is None)

# ---------------- README: lo muy ancho no entra
P = fx.crear_todo()["php"]
(P / "README.md").write_text("# T\n\nUna tienda.\n\n## Uso\n\nAbrir.\n\n## Pruebas\n\nphpunit.\n", encoding="utf-8")
carpeta = P / "docs" / "diagramas"
carpeta.mkdir(parents=True)
(carpeta / "ancho.md").write_text(f"# Ancho\n\n### Un flujo ancho\n\n¿Cómo es el ciclo?\n\n```mermaid\n{CICLO_ANTES.replace('flowchart LR', 'flowchart LR')}\n```\n", encoding="utf-8")
(carpeta / "vertical.md").write_text(f"# Vertical\n\n### Un flujo vertical\n\n¿Cómo es el ciclo?\n\n```mermaid\n{CICLO_VERTICAL}\n```\n", encoding="utf-8")
rc, s = correr(SK / "senior-docs" / "scripts" / "readme_diagramas.py", "agregar", "docs/diagramas/ancho.md", "--texto", "El ciclo.", "--raiz", str(P))
chequear("el README rechaza un flujo cuyo ancho lo achicaría a menos del 60 %", rc != 0 and "ancho estimado" in s, s)
rc, s = correr(SK / "senior-docs" / "scripts" / "readme_diagramas.py", "agregar", "docs/diagramas/vertical.md", "--texto", "El ciclo.", "--raiz", str(P))
chequear("el README acepta el mismo flujo en vertical", rc == 0, s)
rc, s = correr(SK / "senior-docs" / "scripts" / "readme_diagramas.py", "proponer", "--raiz", str(P))
chequear("proponer no sugiere el que no cabe", "ancho.md" not in s, s)
rc, s = correr(SK / "senior-docs" / "scripts" / "readme_diagramas.py", "listar", "--raiz", str(P))
chequear("listar dice que el ancho no cabe", re.search(r"ancho\.md#1.*no cabe: ancho estimado", s), s)

# ---------------- verificar.py: avisa sin bloquear
class A:
    base = "HEAD"


lin, ok = verificar.chequeo_diagramas(P, A())
chequear("verificar.py diagramas avisa de los anchos pero no falla", ok and any("AVISO ancho" in l for l in lin) and any("ancho.md" in l for l in lin), lin)

# ---------------- lo que genera la skill
correr(SK / "documentar-proyecto" / "scripts" / "documentar.py", "estructura", "--raiz", str(fx.BASE / "php"), "--aplicar")
modulos = leer(fx.BASE / "php" / "docs" / "diagramas" / "modulos.md") if (fx.BASE / "php" / "docs" / "diagramas" / "modulos.md").exists() else ""
Q = fx.BASE / "py"
correr(SK / "documentar-proyecto" / "scripts" / "documentar.py", "estructura", "--raiz", str(Q), "--aplicar")
modulos_py = leer(Q / "docs" / "diagramas" / "modulos.md")
chequear("el mapa de módulos que genera la skill es vertical", "flowchart TB" in modulos_py and "flowchart LR" not in modulos_py, modulos_py[-300:])
mm = Q / ".largo.mmd"
mm.write_text(SEC_ANCHA, encoding="utf-8")
rc, s = correr(SK / "documentar-proyecto" / "scripts" / "documentar.py", "secuencia", "--titulo", "Ancho", "--pregunta", "¿Qué pasa?", "--archivo", str(mm),
               "--evidencia", "app/routes.py:7", "--raiz", str(Q))
chequear("guardar una secuencia ancha avisa pero la guarda", rc == 0 and "AVISO" in s and "mensajes" in s and (Q / "docs/diagramas/secuencia-ancho.md").exists(), s)
mm.unlink()

# ---------------- los diagramas del propio repositorio
problemas, n = rd.estado(RAIZ)
chequear("el README del repositorio sigue en orden con el chequeo de ancho", problemas == [] and n == 4, problemas)
for f in sorted((RAIZ / "docs" / "diagramas").glob("*.md")):
    cod = re.search(r"```mermaid\n(.*?)```", leer(f), re.S).group(1)
    e = dg.ancho_estimado(dg.tipo_diagrama(cod), cod)
    if "subgraph" in cod:
        chequear(f"{f.name}: con fases agrupadas (subgraph) el ancho no se estima, y los pasos cuentan sin las fases", e is None and dg.medir("flujo", cod)["nodos"] == 11, (e, dg.medir("flujo", cod)))
    else:
        chequear(f"{f.name}: estimado {e} px, se lee al {round(dg.escala_en_readme(e) * 100)} % o más (mínimo 75 %)", e and dg.escala_en_readme(e) >= 0.75, e)

# ---------------- documentación y reglas
d7 = leer(SK / "senior-docs" / "references" / "diagramas.md")
chequear("la referencia de diagramas fija la forma y el ancho con los datos medidos", "## 7. Forma y ancho de la página" in d7 and "2.875 px" in d7 and "773 × 123" in d7 and "815 × 665" in d7 and "flowchart TB" in d7)
chequear("senior-docs enlaza la regla", "references/diagramas.md" in leer(SK / "senior-docs" / "SKILL.md") and "ancho de la página" in leer(SK / "senior-docs" / "SKILL.md"))
sk = leer(SK / "senior" / "SKILL.md") + leer(SK / "senior" / "references" / "metodo-completo.md")
chequear("senior manda a abrir con abrir_en_navegador.py y explica por qué", "abrir_en_navegador.py" in sk and "una pestaña por cada uno" in sk and "Start-Process" in sk)
rm = leer(RAIZ / "README.md")
chequear("el README lo explica", "abrir_en_navegador.py" in rm and "Pensados para el ancho de la página" in rm)
chequear("el protocolo de secuencias limita el largo de los mensajes", "mensajes de hasta unos 40 caracteres" in leer(SK / "documentar-proyecto" / "references" / "protocolo.md"))
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(rm) == [])

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
