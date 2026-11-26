import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[1]
SK = RAIZ / "skills"
sys.path.insert(0, str(SK / "documentar-proyecto" / "scripts"))
sys.path.insert(0, str(SK / "senior" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analisis as an  # noqa: E402
import documentar as dc  # noqa: E402
import fixtures_documentar as fx  # noqa: E402
import verificar  # noqa: E402

mal = 0


def chequear(nombre, cond, extra=""):
    global mal
    mal += 0 if cond else 1
    print(("ok   " if cond else "MAL  ") + nombre + ("" if cond else "  " + str(extra)[:400]))


def cli(*a):
    p = subprocess.run([sys.executable, "-X", "utf8", str(SK / "documentar-proyecto" / "scripts" / "documentar.py"), *a], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def script(nombre, *a):
    p = subprocess.run([sys.executable, "-X", "utf8", str(nombre), *a], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def leer(r):
    return Path(r).read_text(encoding="utf-8")


proyectos = fx.crear_todo()
PHP, JS, PY = (proyectos[k] for k in ("php", "js", "py"))

# ---------------- análisis por lenguaje
for nombre, ruta in (("PHP", PHP), ("JavaScript", JS), ("Python", PY)):
    p = an.Proyecto(ruta)
    chequear(f"{nombre}: detecta el lenguaje y deja afuera las pruebas", len(p.lenguajes()) == 1 and len(p.pruebas) == 1 and not any("test" in r.lower() for r, _ in p.codigo), (p.lenguajes(), p.pruebas))

p = an.Proyecto(PHP)
tam, aristas = an.dependencias(p)
chequear("PHP: módulos Http, Models, Services, routes y database", {"Http", "Models", "Services", "routes", "database"} <= set(tam), dict(tam))
chequear("PHP: dependencias por `use` con PSR-4 (rutas→Http, Http→Models y Services, Services→Models)",
         ("routes", "Http") in aristas and ("Http", "Models") in aristas and ("Http", "Services") in aristas and ("Services", "Models") in aristas, dict(aristas))
cl = {c["nombre"]: c for lista in an.clases(p).values() for c in lista}
chequear("PHP: clases con herencia, visibilidad y métodos", cl["PedidoController"]["bases"] == ["Controller"] and ("-", "normalizar") in cl["User"]["metodos"], cl.get("User"))
ts = an.tablas(p)
chequear("PHP: tablas de las migraciones con sus relaciones", set(ts) == {"users", "pedidos", "productos", "pedido_producto"} and ("user_id", "users") in ts["pedidos"]["fks"]
         and {d for _, d in ts["pedido_producto"]["fks"]} == {"pedidos", "productos"}, {k: v["fks"] for k, v in ts.items()})
rutas = an.rutas_http(p)
chequear("PHP: rutas con controlador y con función anónima", [(r["metodo"], r["ruta"], r["manejador"]) for r in rutas] ==
         [("GET", "/pedidos", "PedidoController@index"), ("POST", "/pedidos", "PedidoController@store"), ("GET", "/salud", "función anónima")], rutas)
chequear("PHP: variables de entorno del archivo de ejemplo", set(an.variables_entorno(p)) == {"APP_NAME", "DB_HOST", "DB_DATABASE", "MAIL_FROM"})
stack = {d["categoria"]: [c[0] for c in d["componentes"]] for d in an.decisiones_stack(p)}
chequear("PHP: decisiones del stack (Laravel, Sanctum, PHPUnit)", stack == {"framework web": ["Laravel"], "autenticación": ["Laravel Sanctum"], "pruebas": ["PHPUnit"]}, stack)
tipos = {r["tipo"] for r in an.reglas_candidatas(p)}
chequear("PHP: reglas candidatas de umbral, constante, validación, permiso y estados", {"umbral", "constante", "validación", "permiso", "estados"} <= tipos, tipos)

p = an.Proyecto(JS)
tam, aristas = an.dependencias(p)
chequear("JS: dependencias por require relativo", ("routes", "services") in aristas and ("routes", "utils") in aristas and ("services", "models") in aristas, dict(aristas))
cl = {c["nombre"]: c for lista in an.clases(p).values() for c in lista}
chequear("JS: clases, herencia y métodos", cl["ClienteVip"]["bases"] == ["Cliente"] and ("+", "descuento") in cl["ClienteVip"]["metodos"] and ("+", "enviar") in cl["Facturador"]["metodos"], cl)
ts = an.tablas(p)
chequear("JS: tablas de SQL con REFERENCES en línea y FOREIGN KEY", set(ts) == {"clientes", "pedidos", "items"} and ("cliente_id", "clientes") in ts["pedidos"]["fks"] and ("pedido_id", "pedidos") in ts["items"]["fks"], {k: v["fks"] for k, v in ts.items()})
chequear("JS: la clave primaria se reconoce", any(c[2] for c in ts["clientes"]["columnas"]))
rutas = an.rutas_http(p)
chequear("JS: rutas con función con nombre y con función anónima", [(r["metodo"], r["manejador"]) for r in rutas] == [("GET", "listar"), ("POST", "función anónima")], rutas)
chequear("JS: variables de entorno", set(an.variables_entorno(p)) == {"PORT", "DATABASE_URL", "JWT_SECRET"})
chequear("JS: decisiones del stack", {d["categoria"] for d in an.decisiones_stack(p)} == {"framework web", "base de datos y acceso a datos", "autenticación", "pruebas", "empaquetado"})

p = an.Proyecto(PY)
ts = an.tablas(p)
chequear("Python: modelos de SQLAlchemy con su clave foránea", set(ts) == {"clientes", "pedidos"} and ts["pedidos"]["fks"] == [("cliente_id", "clientes")], {k: v["fks"] for k, v in ts.items()})
cl = {c["nombre"]: c for lista in an.clases(p).values() for c in lista}
chequear("Python: clases por ast, con herencia y métodos privados", cl["FacturadorExento"]["bases"] == ["Facturador"] and ("-", "_redondear") in cl["Facturador"]["metodos"], cl)
rutas = an.rutas_http(p)
chequear("Python: rutas de Flask con varios métodos y con @bp.get", [(r["metodo"], r["ruta"], r["manejador"]) for r in rutas] == [("GET, POST", "/pedidos", "pedidos"), ("GET", "/salud", "salud")], rutas)
chequear("Python: importaciones relativas entre módulos", any(a == "(app)" and b == "services" for (a, b) in an.dependencias(p)[1]), dict(an.dependencias(p)[1]))
chequear("Python: variables de entorno del código y del ejemplo", set(an.variables_entorno(p)) == {"SECRET_KEY", "DATABASE_URL"})
chequear("Python: decisiones del stack", {d["categoria"] for d in an.decisiones_stack(p)} == {"framework web", "base de datos y acceso a datos", "tareas en segundo plano", "pruebas"})
chequear("Python: reglas candidatas (umbral y constante)", {"umbral", "constante"} <= {r["tipo"] for r in an.reglas_candidatas(p)})

# ---------------- generación: seco, aplicado, límites y compatibilidad con los chequeos del paquete
rc, s = cli("todo", "--raiz", str(PHP))
chequear("sin --aplicar no escribe nada y lo dice", not (PHP / "docs").exists() and "No se escribió nada" in s, s)
rc, s = cli("todo", "--raiz", str(PHP), "--aplicar")
generados = sorted(p.relative_to(PHP).as_posix() for p in (PHP / "docs").rglob("*.md"))
chequear("con --aplicar crea diagramas, RI, RD, ADR y una consulta", rc == 0 and len(generados) == 14 and "docs/consultas/01-reglas-candidatas.md" in generados, generados)
ids = sorted(re.findall(r"RI-\d+|RD-\d+|ADR-\d+", " ".join(generados)))
chequear("los IDs son correlativos por tipo", ids == ["ADR-001", "ADR-002", "ADR-003", "RD-001", "RD-002", "RD-003", "RD-004", "RI-001", "RI-002"], ids)
rc, s = script(SK / "senior-docs" / "scripts" / "revisar_requisitos.py", "--raiz", str(PHP))
chequear("los requisitos generados pasan el revisor sin fallas ni avisos", "0 fallas, 0 avisos" in s and "provisorios" in s, s)
rc, s = script(SK / "senior" / "scripts" / "diagramas.py", "--raiz", str(PHP))
chequear("los diagramas generados son legibles", rc == 0 and "todos legibles" in s, s)
rc, s = cli("evidencia", "--raiz", str(PHP))
chequear("todas las citas de evidencia existen", rc == 0, s)
script(SK / "senior-docs" / "scripts" / "indexar_docs.py", "indexar", "--raiz", str(PHP))
rc, s = script(SK / "senior" / "scripts" / "verificar.py", "docs", "--raiz", str(PHP))
chequear("los provisorios no cuentan como «sin test»", "todos los requisitos tienen test" in s, s)
rc, s = script(SK / "senior-docs" / "scripts" / "consultas.py", "estado", "--raiz", str(PHP))
chequear("la consulta de reglas se lee con consultas.py (8 preguntas sin responder)", "8 preguntas" in s and "0 respondidas" in s, s)
indice = leer(PHP / "docs" / "INDEX.md")
chequear("el índice muestra cuántos provisorios esperan confirmación", "Requisitos provisorios sin test: 6" in indice, indice[-300:])
todos = " ".join(leer(f) for f in (PHP / "docs").rglob("*.md"))
chequear("nada se presenta como confirmado: sin «vigente» y con evidencia en cada requisito", "vigente" not in todos and all(
    "Evidencia:" in leer(f) for f in (PHP / "docs" / "requisitos").rglob("*.md")))
chequear("el diagrama de módulos lleva la marca de generado en la primera línea del cuerpo", "generado por documentar.py" in leer(PHP / "docs/diagramas/modulos.md")[:400])

# ---------------- idempotencia y protección de lo editado o confirmado
rc, s = cli("todo", "--raiz", str(PHP), "--aplicar")
chequear("repetir no crea ni duplica nada", len([f for f in (PHP / "docs").rglob("*.md") if f.name != "INDEX.md"]) == 14 and "Se crearon" not in s, s)
mod = PHP / "docs/diagramas/modulos.md"
mod.write_text(leer(mod).replace("<!-- generado por documentar.py", "<!-- editado: generado por otra cosa") + "\nNota a mano.\n", encoding="utf-8", newline="\n")
mod.write_text(re.sub(r"<!-- editado:[^\n]*\n", "", leer(mod)), encoding="utf-8", newline="\n")
rc, s = cli("estructura", "--raiz", str(PHP), "--aplicar")
chequear("un diagrama editado a mano (sin la marca) no se pisa", "Nota a mano." in leer(mod) and "docs/diagramas/modulos.md" in s and "editados a mano" in s, s)
rd = PHP / "docs/requisitos/dominio/RD-002.md"
rd.write_text(leer(rd).replace("provisorio", "vigente"), encoding="utf-8", newline="\n")
with open(PHP / "routes/web.php", "a", encoding="utf-8") as f:
    f.write("Route::delete('/pedidos', [PedidoController::class, 'destroy']);\n")
ri = PHP / "docs/requisitos/interfaces/RI-001.md"
rc, s = cli("todo", "--raiz", str(PHP), "--aplicar", "--refrescar")
chequear("--refrescar actualiza un requisito provisorio con el mismo ID cuando el código cambió", "DELETE" in leer(ri) and leer(ri).count("id: RI-001") == 1, leer(ri)[-500:])
chequear("--refrescar no toca un requisito que el usuario confirmó", "vigente" in leer(rd) and "docs/requisitos/dominio/RD-002.md" in s, s)

# ---------------- requisitos con el modelo: las ayudas rechazan lo que no tiene evidencia
rc, s = cli("requisito", "--tipo", "RF", "--titulo", "Facturar un pedido", "--modulo", "Services", "--evidencia", "app/Services/Facturador.php:10",
            "--descripcion", "El sistema calcula el total facturado de un pedido aplicando el IVA y un descuento si el total supera un umbral.", "--raiz", str(PHP))
chequear("crea un RF provisorio con módulo y evidencia", rc == 0 and "RF-001" in s and "modulo: Services" in leer(PHP / "docs/requisitos/funcional/RF-001.md"), s)
rc, s = script(SK / "senior-docs" / "scripts" / "revisar_requisitos.py", "--raiz", str(PHP))
chequear("un RF provisorio sin ejemplos no es una falla", "0 fallas" in s, s)
(PHP / "docs/requisitos/funcional/RF-009.md").write_text(leer(PHP / "docs/requisitos/funcional/RF-001.md").replace("RF-001", "RF-009").replace("provisorio", "vigente"), encoding="utf-8", newline="\n")
rc, s = script(SK / "senior-docs" / "scripts" / "revisar_requisitos.py", "--raiz", str(PHP))
chequear("un RF vigente sin ejemplos sigue siendo una falla", "sin ejemplos verificables" in s and "1 fallas" in s, s)
(PHP / "docs/requisitos/funcional/RF-009.md").unlink()
rc, s = cli("requisito", "--tipo", "RF", "--titulo", "Inventado", "--evidencia", "app/Services/NoExiste.php:3", "--descripcion", "algo", "--raiz", str(PHP))
chequear("rechaza una evidencia con un archivo que no existe", rc != 0 and "no existe" in s, s)
rc, s = cli("requisito", "--tipo", "RF", "--titulo", "Inventado", "--evidencia", "app/Services/Facturador.php:999", "--descripcion", "algo", "--raiz", str(PHP))
chequear("rechaza una evidencia con una línea fuera del archivo", rc != 0 and "líneas" in s, s)
rc, s = cli("requisito", "--tipo", "RF", "--titulo", "Sin pruebas", "--descripcion", "algo", "--raiz", str(PHP))
chequear("rechaza un requisito sin evidencia", rc != 0 and "evidencia" in s.lower(), s)
rc, s = cli("requisito", "--tipo", "RN", "--titulo", "Regla", "--evidencia", "app/Services/Facturador.php:10", "--descripcion", "algo", "--raiz", str(PHP))
chequear("no se infieren reglas de negocio (RN)", rc != 0 and "RN" in s, s)
rc, s = cli("progreso", "--raiz", str(PHP))
chequear("progreso marca los módulos sin documentar", "Services | 1 | 1" in s and "Models | 3 | 0  ← sin documentar" in s, s)

# ---------------- secuencias
rc, s = cli("secuencias", "--raiz", str(PHP))
chequear("lista los puntos de entrada con su evidencia", "POST /pedidos → PedidoController@store" in s and "routes/web.php" in s, s)
mm = PHP / ".temporal-seq.mmd"
mm.write_text("sequenceDiagram\n    actor U as Cliente\n    participant C as PedidoController\n    participant F as Facturador\n    U->>C: POST /pedidos\n    C->>F: facturar(pedido)\n    F-->>C: total\n    C-->>U: respuesta\n", encoding="utf-8")
rc, s = cli("secuencia", "--titulo", "Crear un pedido", "--pregunta", "¿Qué pasa cuando un cliente crea un pedido?", "--archivo", str(mm), "--evidencia", "app/Http/Controllers/PedidoController.php:14", "--raiz", str(PHP))
chequear("guarda una secuencia legible", rc == 0 and (PHP / "docs/diagramas/secuencia-crear-un-pedido.md").exists(), s)
grande = "sequenceDiagram\n" + "".join(f"    A->>B: mensaje {i}\n" for i in range(30))
mm.write_text(grande, encoding="utf-8")
rc, s = cli("secuencia", "--titulo", "Demasiado grande", "--pregunta", "¿Todo?", "--archivo", str(mm), "--evidencia", "app/Http/Controllers/PedidoController.php:14", "--raiz", str(PHP))
chequear("rechaza una secuencia que no es legible y no deja archivo", rc != 0 and not (PHP / "docs/diagramas/secuencia-demasiado-grande.md").exists(), s)
mm.write_text("flowchart LR\n A-->B\n", encoding="utf-8")
rc, s = cli("secuencia", "--titulo", "Otro tipo", "--pregunta", "¿?", "--archivo", str(mm), "--evidencia", "app/Http/Controllers/PedidoController.php:14", "--raiz", str(PHP))
chequear("rechaza un diagrama que no es de secuencia", rc != 0 and "sequenceDiagram" in s, s)
mm.unlink()

# ---------------- límites de legibilidad en proyectos grandes
G = fx.BASE / "grande"
G.mkdir(parents=True)
sql = "".join(f"CREATE TABLE t{i:02d} (id INTEGER PRIMARY KEY, nombre VARCHAR(20), padre_id INTEGER REFERENCES t{max(i - 1, 0):02d}(id));\n" for i in range(25))
(G / "schema.sql").write_text(sql, encoding="utf-8")
clases = "\n".join(f"class C{i:02d}:\n    def metodo_{i}(self):\n        pass\n" for i in range(35))
(G / "app").mkdir()
(G / "app" / "modelos.py").write_text(clases, encoding="utf-8")
(G / "app" / "otro.py").write_text("x = 1\n", encoding="utf-8")
rc, s = cli("estructura", "--raiz", str(G), "--aplicar")
er = leer(G / "docs/diagramas/entidad-relacion.md")
bloques = re.findall(r"```mermaid\nerDiagram(.*?)```", er, re.S)
chequear("25 tablas se dividen en diagramas de hasta 10 entidades", len(bloques) == 3 and all(len(re.findall(r"^\s{4}\w+ \{", b, re.M)) <= 10 for b in bloques), [len(re.findall(r"^\s{4}\w+ \{", b, re.M)) for b in bloques])
rc, s = script(SK / "senior" / "scripts" / "diagramas.py", "--raiz", str(G))
chequear("y siguen pasando el verificador de legibilidad", rc == 0, s)
cls = leer(G / "docs/diagramas/clases-app.md")
chequear("35 clases se dividen en partes de hasta 10 y avisan las que no se dibujan", cls.count("```mermaid") == 3 and "Quedan 5 clases sin dibujar" in cls, cls.count("```mermaid"))

# ---------------- integración con el verificador del paquete
rc, s = script(SK / "senior" / "scripts" / "verificar.py", "evidencia", "--raiz", str(PHP))
chequear("verificar.py evidencia: al día cuando las citas existen", rc == 0 and "todas sus citas existen" in s, s)
(PHP / "app/Services/Facturador.php").unlink()
rc, s = script(SK / "senior" / "scripts" / "verificar.py", "evidencia", "--raiz", str(PHP))
chequear("verificar.py evidencia: falla cuando un archivo citado desaparece", rc != 0 and "no existe" in s, s)
chequear("el chequeo está registrado", "evidencia" in verificar.CHEQUEOS)
vacio = fx.BASE / "vacio"
vacio.mkdir()
(vacio / "docs").mkdir()
chequear("un proyecto sin documentos inferidos no recibe mensajes", verificar.chequeo_evidencia(vacio, None) == ([], True))

# ---------------- plan, proyecto sin código y documentación
rc, s = cli("plan", "--raiz", str(JS))
chequear("el plan cuenta lo detectado y el costo de las etapas del modelo", "3 tablas" in s and "2 rutas HTTP" in s and "tokens" in s and "requisitos  requisitos funcionales" in s, s)
(fx.BASE / "css").mkdir()
(fx.BASE / "css" / "a.css").write_text("a{}", encoding="utf-8")
rc, s = cli("plan", "--raiz", str(fx.BASE / "css"))
chequear("sin código de los lenguajes admitidos lo dice y no genera nada", "No hay nada que analizar" in s, s)
skill = (SK / "documentar-proyecto" / "SKILL.md").read_text(encoding="utf-8")
descr = re.search(r"^description:\s*(.*)$", skill, re.M).group(1)
chequear("la skill tiene nombre, descripción corta y las reglas", skill.startswith("---\nname: documentar-proyecto") and len(descr) <= 800 and "No se infieren reglas de negocio" in skill and "Nunca se pisa lo confirmado" in skill, len(descr))
chequear("el protocolo de las etapas con el modelo existe", (SK / "documentar-proyecto" / "references" / "protocolo.md").exists())
plan = (SK / "adoptar-proyecto" / "scripts" / "plan_adopcion.py").read_text(encoding="utf-8")
chequear("/adoptar-proyecto propone documentar un proyecto existente", "/documentar-proyecto" in plan and "/documentar-proyecto" in (SK / "adoptar-proyecto" / "SKILL.md").read_text(encoding="utf-8"))
readme = ((RAIZ / "README.md").read_text(encoding="utf-8") + (RAIZ / "docs" / "referencia.md").read_text(encoding="utf-8"))
chequear("el README lo explica", "## Documentar un proyecto existente" in readme and "`documentar-proyecto`" in readme and "`evidencia`" in readme)
chequear("el README no tiene texto ajeno al proyecto", verificar.contenido_ajeno(readme) == [])
chequear("senior-docs y senior-relevar lo mencionan", "provisorio" in (SK / "senior-docs" / "SKILL.md").read_text(encoding="utf-8") and "documentar.py reglas" in (SK / "senior-relevar" / "SKILL.md").read_text(encoding="utf-8"))

# una regla que solo aparece en un docstring o en una expresión regular no es una regla de negocio
FALSO = PY.parent / "falsos-positivos"
FALSO.mkdir(exist_ok=True)
comillas = chr(34) * 3
lineas_py = [comillas + "Calcula totales.", "", "Si MAX_PRECIO = 100 se rechaza el pedido.", comillas, "import re", "",
             'ES_PERMISO = re.compile("(?:can|authorize)")', "LIMITE_DESCUENTO = 30", ""]
(FALSO / "modulo.py").write_text(chr(10).join(lineas_py), encoding="utf-8")
textos = [r["texto"] for r in an.reglas_candidatas(an.Proyecto(FALSO))]
chequear("Python: un docstring y una definición de expresión regular no salen como reglas candidatas",
         not any("MAX_PRECIO" in x or "re.compile" in x for x in textos) and any("LIMITE_DESCUENTO" in x for x in textos), textos)

print("Todo bien." if not mal else f"{mal} casos mal.")
sys.exit(1 if mal else 0)
