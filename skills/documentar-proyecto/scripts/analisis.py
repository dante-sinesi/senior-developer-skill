#!/usr/bin/env python3
"""Análisis estático de un proyecto existente (PHP, JavaScript o TypeScript y Python), sin ejecutar nada.

Lo usa documentar.py. Todo lo que devuelve son HECHOS leídos del código con su evidencia (archivo y línea): módulos y
dependencias entre ellos, clases, tablas y relaciones, rutas HTTP, variables de entorno, decisiones del stack y reglas
candidatas. No interpreta intenciones: lo que el código hace no es necesariamente lo que debería hacer. Los patrones son
aproximados (expresiones regulares y, en Python, el módulo ast): una cita siempre apunta al lugar donde se vio algo, y
puede fallar con código muy dinámico. Solo biblioteca estándar.
"""
import ast
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

LENGUAJE = {".php": "php", ".js": "js", ".mjs": "js", ".cjs": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".py": "py"}
IGNORAR = {".git", "node_modules", "vendor", "dist", "build", "__pycache__", ".venv", "venv", "env", ".idea", ".vscode",
           "coverage", ".next", ".nuxt", ".temporal", "docs", "documentos-externos", "storage", "bootstrap", "public",
           ".pytest_cache", ".mypy_cache", "site-packages", "static", "staticfiles"}
PRUEBAS = {"tests", "test", "__tests__", "spec", "specs", "e2e", "cypress"}
RAICES_FUENTE = ("src", "app", "lib", "source", "backend", "server")
MAX_BYTES = 400_000


def es_prueba(rel):
    partes = Path(rel).parts
    nombre = partes[-1].lower()
    return bool(set(p.lower() for p in partes[:-1]) & PRUEBAS) or nombre.startswith("test_") or \
        bool(re.search(r"(_test|\.test|\.spec)\.\w+$", nombre))


class Proyecto:
    """Lee el proyecto una vez y guarda los textos para no repetir lecturas."""

    def __init__(self, raiz):
        self.raiz = Path(raiz).resolve()
        self.textos = {}
        self.codigo = []     # (ruta relativa, lenguaje) de código que no es prueba
        self.pruebas = []
        self.otros = {}      # .sql, manifiestos, .env.example
        for actual, carpetas, nombres in os.walk(self.raiz):
            carpetas[:] = sorted(c for c in carpetas if c not in IGNORAR and not c.startswith("."))
            for n in sorted(nombres):
                p = Path(actual) / n
                rel = p.relative_to(self.raiz).as_posix()
                suf = p.suffix.lower()
                if suf in LENGUAJE and not n.endswith((".min.js", ".d.ts")) and self._tamano_ok(p):
                    (self.pruebas if es_prueba(rel) else self.codigo).append((rel, LENGUAJE[suf]))
                elif suf == ".sql" and self._tamano_ok(p):
                    self.otros.setdefault("sql", []).append(rel)
                elif n in ("composer.json", "package.json", "requirements.txt", "pyproject.toml", "Pipfile", "schema.prisma"):
                    self.otros.setdefault("manifiestos", []).append(rel)
                elif n in (".env.example", ".env.sample", ".env.dist"):
                    self.otros.setdefault("env", []).append(rel)

    @staticmethod
    def _tamano_ok(p):
        try:
            return p.stat().st_size <= MAX_BYTES
        except OSError:
            return False

    def texto(self, rel):
        if rel not in self.textos:
            try:
                self.textos[rel] = (self.raiz / rel).read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                self.textos[rel] = ""
        return self.textos[rel]

    def lenguajes(self):
        return Counter(l for _, l in self.codigo)

    def rutas_codigo(self):
        return {r for r, _ in self.codigo}


def linea_de(texto, posicion):
    return texto.count("\n", 0, posicion) + 1


def sin_comentarios(linea, lenguaje):
    """Quita el comentario de una línea, de forma aproximada (no entiende cadenas con // adentro)."""
    marcador = "#" if lenguaje == "py" else "//"
    return linea.split(marcador, 1)[0] if marcador in linea else linea


def modulos(proyecto):
    """{ruta relativa: nombre de módulo}. El módulo es el primer nivel debajo de la raíz de fuentes (src, app, lib…)."""
    rutas = [r for r, _ in proyecto.codigo]
    existentes = {Path(r).parts[0] for r in rutas if len(Path(r).parts) > 1}
    prefijo = ()
    for raiz_fuente in RAICES_FUENTE:
        if raiz_fuente in existentes:
            prefijo = (raiz_fuente,)
            break

    def nombre(rel, niveles):
        partes = Path(rel).parts
        dentro = bool(prefijo) and partes[:len(prefijo)] == prefijo
        if dentro:
            partes = partes[len(prefijo):]
        if len(partes) <= niveles:
            return f"({'/'.join(prefijo)})" if dentro else "(raíz)"
        return "/".join(partes[:niveles])

    niveles = 1
    while niveles < 3:  # si casi todo cae en un solo módulo, se baja un nivel para que el diagrama diga algo
        cuenta = Counter(nombre(r, niveles) for r in rutas)
        if not cuenta:
            break
        mayor, n = cuenta.most_common(1)[0]
        if not mayor.startswith("(") and n / len(rutas) >= 0.7 and len(cuenta) <= 2:
            niveles += 1
        else:
            break
    return {r: nombre(r, niveles) for r in rutas}


def mapa_psr4(proyecto):
    mapa = {}
    for rel in proyecto.otros.get("manifiestos", []):
        if rel.endswith("composer.json"):
            try:
                datos = json.loads(proyecto.texto(rel))
            except ValueError:
                continue
            base = Path(rel).parent.as_posix()
            for seccion in ("autoload", "autoload-dev"):
                for prefijo, destino in (datos.get(seccion, {}).get("psr-4", {}) or {}).items():
                    destinos = destino if isinstance(destino, list) else [destino]
                    for d in destinos:
                        mapa[prefijo] = (Path(base) / d).as_posix().lstrip("./") if base != "." else d.rstrip("/")
    if not mapa and "app" in {Path(r).parts[0] for r, _ in proyecto.codigo if len(Path(r).parts) > 1}:
        mapa["App\\"] = "app"
    return mapa


def resolver_js(origen, especificador, existentes):
    if especificador.startswith("@/") or especificador.startswith("~/"):
        base = Path("src") / especificador[2:]
    elif especificador.startswith("."):
        base = Path(os.path.normpath((Path(origen).parent / especificador).as_posix()))
    else:
        return None
    base = base.as_posix()
    for sufijo in ("", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", "/index.js", "/index.ts", "/index.tsx", "/index.jsx"):
        if (base + sufijo) in existentes:
            return base + sufijo
    return None


def resolver_py(origen, modulo, nivel, existentes):
    partes = [p for p in modulo.split(".") if p] if modulo else []
    if nivel:
        base = list(Path(origen).parent.parts)
        if nivel > 1:
            base = base[:len(base) - (nivel - 1)]
        partes = base + partes
    candidatos = []
    for i in range(len(partes), 0, -1):
        ruta = "/".join(partes[:i])
        candidatos += [ruta + ".py", ruta + "/__init__.py"]
    for c in candidatos:
        if c in existentes:
            return c
        for raiz_fuente in RAICES_FUENTE:
            if f"{raiz_fuente}/{c}" in existentes:
                return f"{raiz_fuente}/{c}"
    return None


def importaciones(proyecto, rel, lenguaje, psr4, existentes):
    """Archivos del propio proyecto que `rel` importa."""
    texto = proyecto.texto(rel)
    destinos = set()
    if lenguaje == "js":
        for m in re.finditer(r"""(?:import\s[^'"]*?from\s*|import\s*|require\(\s*|import\(\s*)['"]([^'"]+)['"]""", texto):
            d = resolver_js(rel, m.group(1), existentes)
            if d:
                destinos.add(d)
    elif lenguaje == "py":
        try:
            arbol = ast.parse(texto)
        except (SyntaxError, ValueError):
            return destinos
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for a in nodo.names:
                    d = resolver_py(rel, a.name, 0, existentes)
                    if d:
                        destinos.add(d)
            elif isinstance(nodo, ast.ImportFrom):
                base = nodo.module or ""
                d = resolver_py(rel, base, nodo.level, existentes)
                if d:
                    destinos.add(d)
                for a in nodo.names:
                    sub = resolver_py(rel, (base + "." if base else "") + a.name, nodo.level, existentes)
                    if sub:
                        destinos.add(sub)
    elif lenguaje == "php":
        for m in re.finditer(r"^\s*use\s+(?:function\s+|const\s+)?([A-Za-z_\\][\w\\]*)", texto, re.M):
            nombre = m.group(1).lstrip("\\")
            for prefijo in sorted(psr4, key=len, reverse=True):
                p = prefijo.rstrip("\\")
                if nombre == p or nombre.startswith(p + "\\"):
                    ruta = psr4[prefijo].rstrip("/") + "/" + nombre[len(p):].lstrip("\\").replace("\\", "/") + ".php"
                    if ruta in existentes:
                        destinos.add(ruta)
                    break
        for m in re.finditer(r"""(?:require|include)(?:_once)?\s*\(?\s*(?:__DIR__\s*\.\s*)?['"]([^'"]+\.php)['"]""", texto):
            ruta = os.path.normpath((Path(rel).parent / m.group(1).lstrip("/")).as_posix()).replace("\\", "/")
            if ruta in existentes:
                destinos.add(ruta)
    destinos.discard(rel)
    return destinos


def dependencias(proyecto):
    """({módulo: cantidad de archivos}, {(desde, hasta): cantidad de importaciones})."""
    modulo_de = modulos(proyecto)
    existentes = proyecto.rutas_codigo()
    psr4 = mapa_psr4(proyecto)
    tamano = Counter(modulo_de.values())
    aristas = Counter()
    for rel, leng in proyecto.codigo:
        for d in importaciones(proyecto, rel, leng, psr4, existentes):
            a, b = modulo_de.get(rel), modulo_de.get(d)
            if a and b and a != b:
                aristas[(a, b)] += 1
    return tamano, aristas


VISIBILIDAD = {"public": "+", "protected": "#", "private": "-"}


def clases_php(rel, texto):
    out = []
    marcas = list(re.finditer(
        r"^\s*(?:abstract\s+|final\s+)*(class|interface|trait|enum)\s+(\w+)(?:\s+extends\s+([\w\\,\s]+?))?(?:\s+implements\s+([\w\\,\s]+?))?\s*\{?\s*$", texto, re.M))
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        cuerpo = texto[m.end():fin]
        metodos = [(VISIBILIDAD.get((mm.group(1) or "public").lower(), "+"), mm.group(2))
                   for mm in re.finditer(r"^\s*(?:(public|protected|private)\s+)?(?:static\s+)?function\s+(\w+)\s*\(", cuerpo, re.M)]
        bases = [b.strip().split("\\")[-1] for b in (m.group(3) or "").split(",") if b.strip()]
        interfaces = [b.strip().split("\\")[-1] for b in (m.group(4) or "").split(",") if b.strip()]
        out.append({"nombre": m.group(2), "clase": m.group(1), "bases": bases, "interfaces": interfaces, "metodos": metodos,
                    "rel": rel, "linea": linea_de(texto, m.start())})
    return out


def clases_js(rel, texto):
    out = []
    for m in re.finditer(r"^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w\s,.]+?))?\s*\{", texto, re.M):
        inicio, profundidad, i = m.end(), 1, m.end()
        while i < len(texto) and profundidad:
            profundidad += {"{": 1, "}": -1}.get(texto[i], 0)
            i += 1
        cuerpo = texto[inicio:i]
        metodos = []
        for mm in re.finditer(r"^\s{1,8}(?:(public|protected|private)\s+)?(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?([A-Za-z_#]\w*)\s*\([^)]*\)\s*(?::\s*[^{]+)?\{", cuerpo, re.M):
            if mm.group(2) not in {"if", "for", "while", "switch", "catch", "function", "return", "constructor"}:
                metodos.append((VISIBILIDAD.get(mm.group(1) or "public", "+"), mm.group(2)))
        out.append({"nombre": m.group(1), "clase": "class", "bases": [m.group(2).split(".")[-1]] if m.group(2) else [],
                    "interfaces": [x.strip() for x in (m.group(3) or "").split(",") if x.strip()], "metodos": metodos,
                    "rel": rel, "linea": linea_de(texto, m.start())})
    return out


def clases_py(rel, texto):
    try:
        arbol = ast.parse(texto)
    except (SyntaxError, ValueError):
        return []
    out = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ClassDef):
            bases = []
            for b in nodo.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            metodos = [("-" if f.name.startswith("_") and not f.name.startswith("__") else "+", f.name)
                       for f in nodo.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and (not f.name.startswith("__") or f.name == "__init__")]
            out.append({"nombre": nodo.name, "clase": "class", "bases": bases, "interfaces": [], "metodos": metodos, "rel": rel, "linea": nodo.lineno})
    return out


def clases(proyecto):
    """{módulo: [clase, …]} con las clases del código que no es prueba ni migración."""
    modulo_de = modulos(proyecto)
    por_modulo = defaultdict(list)
    for rel, leng in proyecto.codigo:
        if "migrations" in Path(rel).parts or "database" in Path(rel).parts and "seeders" in Path(rel).parts:
            continue
        funcion = {"php": clases_php, "js": clases_js, "py": clases_py}[leng]
        por_modulo[modulo_de.get(rel, "(raíz)")] += funcion(rel, proyecto.texto(rel))
    return dict(por_modulo)


def _partes_de_nivel_cero(cuerpo):
    partes, actual, nivel = [], "", 0
    for c in cuerpo:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
        if c == "," and nivel == 0:
            partes.append(actual.strip())
            actual = ""
        else:
            actual += c
    if actual.strip():
        partes.append(actual.strip())
    return partes


def tablas_sql(rel, texto):
    out = {}
    for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?(\w+)[`\"\]]?\s*\(", texto, re.I):
        i, nivel = m.end(), 1
        while i < len(texto) and nivel:
            nivel += {"(": 1, ")": -1}.get(texto[i], 0)
            i += 1
        cuerpo = texto[m.end():i - 1]
        tabla = {"columnas": [], "fks": [], "rel": rel, "linea": linea_de(texto, m.start())}
        pks = set()
        for parte in _partes_de_nivel_cero(cuerpo):
            p = re.sub(r"\s+", " ", parte)
            if re.match(r"(CONSTRAINT\s+\w+\s+)?FOREIGN KEY", p, re.I):
                f = re.search(r"FOREIGN KEY\s*\(([^)]*)\)\s*REFERENCES\s+[`\"]?(\w+)", p, re.I)
                if f:
                    tabla["fks"].append((f.group(1).strip(" `\""), f.group(2)))
            elif re.match(r"(CONSTRAINT\s+\w+\s+)?PRIMARY KEY", p, re.I):
                pks |= {c.strip(" `\"") for c in re.search(r"\(([^)]*)\)", p).group(1).split(",")} if re.search(r"\(([^)]*)\)", p) else set()
            elif re.match(r"(UNIQUE|KEY|INDEX|CHECK|FULLTEXT)\b", p, re.I):
                continue
            else:
                tokens = p.split(" ")
                nombre = tokens[0].strip("`\"[]")
                tipo = tokens[1].split("(")[0].lower() if len(tokens) > 1 else ""
                if re.search(r"PRIMARY KEY", p, re.I):
                    pks.add(nombre)
                r = re.search(r"REFERENCES\s+[`\"]?(\w+)", p, re.I)
                if r:
                    tabla["fks"].append((nombre, r.group(1)))
                tabla["columnas"].append([nombre, tipo, False])
        for c in tabla["columnas"]:
            c[2] = c[0] in pks
        out[m.group(1)] = tabla
    return out


def tablas_laravel(rel, texto):
    out = {}
    for m in re.finditer(r"Schema::create\(\s*['\"](\w+)['\"]", texto):
        resto = texto[m.end():]
        fin = re.search(r"Schema::|\n\s*\}\s*(?:public|\Z)", resto)
        cuerpo = resto[:fin.start()] if fin else resto
        tabla = {"columnas": [], "fks": [], "rel": rel, "linea": linea_de(texto, m.start())}
        if re.search(r"\$table->(id|increments|bigIncrements)\(", cuerpo):
            tabla["columnas"].append(["id", "bigint", True])
        for c in re.finditer(r"\$table->(\w+)\(\s*['\"](\w+)['\"]([^;]*);", cuerpo):
            tipo, nombre, resto_linea = c.group(1), c.group(2), c.group(3)
            if tipo in ("foreign", "index", "unique", "primary"):
                if tipo == "foreign":
                    f = re.search(r"->on\(\s*['\"](\w+)['\"]", resto_linea) or re.search(r"->constrained\(\s*['\"](\w+)['\"]", resto_linea)
                    if f:
                        tabla["fks"].append((nombre, f.group(1)))
                continue
            tabla["columnas"].append([nombre, tipo.lower(), False])
            if tipo in ("foreignId", "foreignUuid", "foreignIdFor") or "->constrained(" in resto_linea:
                f = re.search(r"->constrained\(\s*['\"](\w+)['\"]", resto_linea)
                destino = f.group(1) if f else re.sub(r"_id$", "", nombre) + "s"
                tabla["fks"].append((nombre, destino))
        out[m.group(1)] = tabla
    return out


def tablas_modelos_py(rel, texto):
    out = {}
    for m in re.finditer(r"^class\s+(\w+)\(([^)]*)\):\s*\n", texto, re.M):
        fin = re.search(r"^\S", texto[m.end():], re.M)
        cuerpo = texto[m.end():m.end() + fin.start()] if fin else texto[m.end():]
        django = re.search(r"\bmodels\.Model\b|\bModel\b", m.group(2)) and "models." in cuerpo
        sqla = "__tablename__" in cuerpo or re.search(r"=\s*(?:db\.)?Column\(", cuerpo)
        if not (django or sqla):
            continue
        tn = re.search(r"__tablename__\s*=\s*['\"](\w+)['\"]", cuerpo)
        nombre = tn.group(1) if tn else m.group(1)
        tabla = {"columnas": [], "fks": [], "rel": rel, "linea": linea_de(texto, m.start()), "clase": m.group(1)}
        for c in re.finditer(r"^\s+(\w+)\s*=\s*(?:models\.|(?:db\.)?)(\w+)\(([^\n]*)", cuerpo, re.M):
            campo, tipo, args = c.groups()
            if tipo in ("ForeignKey", "OneToOneField"):
                d = re.match(r"\s*['\"]?([\w.]+)", args)
                tabla["fks"].append((campo, d.group(1).split(".")[-1] if d else "?"))
                tabla["columnas"].append([campo, "fk", False])
            elif tipo == "Column" or (django and tipo.endswith("Field")):
                tipo_real = re.match(r"\s*(?:db\.)?(\w+)", args).group(1) if tipo == "Column" and re.match(r"\s*(?:db\.)?(\w+)", args) else tipo
                fk = re.search(r"ForeignKey\(\s*['\"](\w+)\.", args)
                if fk:
                    tabla["fks"].append((campo, fk.group(1)))
                tabla["columnas"].append([campo, tipo_real.lower(), "primary_key=True" in args])
        if tabla["columnas"]:
            out[nombre] = tabla
    return out


def tablas(proyecto):
    """{nombre de tabla: {columnas, fks, rel, linea}} de SQL, migraciones de Laravel y modelos de Django o SQLAlchemy."""
    out = {}
    for rel in proyecto.otros.get("sql", []):
        out.update(tablas_sql(rel, proyecto.texto(rel)))
    for rel, leng in proyecto.codigo:
        texto = proyecto.texto(rel)
        if leng == "php" and "Schema::create" in texto:
            out.update(tablas_laravel(rel, texto))
        elif leng == "py" and ("models." in texto or "Column(" in texto):
            out.update(tablas_modelos_py(rel, texto))
    conocidas = {n.lower(): n for n in out}
    for t in out.values():  # las relaciones apuntan a tablas que existen; las demás se descartan
        t["fks"] = [(c, conocidas[d.lower()]) for c, d in t["fks"] if d.lower() in conocidas]
    return out


def rutas_http(proyecto):
    out = []
    for rel, leng in proyecto.codigo:
        texto = proyecto.texto(rel)
        if leng == "php":
            for m in re.finditer(r"Route::(get|post|put|patch|delete|any|resource|apiResource)\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*([^\n]*))?", texto):
                destino = (m.group(3) or "").strip()
                par = re.match(r"\[\s*([\w\\]+)::class\s*,\s*['\"](\w+)['\"]", destino)
                if par:
                    manej = f"{par.group(1).split(chr(92))[-1]}@{par.group(2)}"
                elif re.match(r"['\"][\w\\@]+['\"]", destino):
                    manej = destino.split(",")[0].strip("'\"").split(chr(92))[-1]
                elif "::class" in destino:
                    manej = destino.split("::")[0].lstrip("[ ").split(chr(92))[-1] + " (recurso)"
                else:
                    manej = "función anónima"
                out.append({"metodo": m.group(1).upper(), "ruta": "/" + m.group(2).lstrip("/"), "manejador": manej, "rel": rel,
                            "linea": linea_de(texto, m.start())})
        elif leng == "js":
            for m in re.finditer(r"""\b(app|router|\w*[Rr]outer|server)\.(get|post|put|patch|delete|all)\(\s*['"`]([^'"`]+)['"`]\s*(?:,\s*([^\n]*))?""", texto):
                args = (m.group(4) or "").strip()
                nombres = re.findall(r"[A-Za-z_][\w.]*", args.split("=>")[0].rstrip(");"))
                manej = nombres[-1] if nombres and "=>" not in args and "function" not in args else "función anónima"
                out.append({"metodo": m.group(2).upper(), "ruta": m.group(3), "manejador": manej, "rel": rel, "linea": linea_de(texto, m.start())})
        elif leng == "py":
            lineas = texto.splitlines()
            for i, l in enumerate(lineas):
                m = re.match(r"\s*@(\w+)\.(route|get|post|put|patch|delete)\(\s*['\"]([^'\"]*)['\"](?:\s*,\s*methods\s*=\s*\[([^\]]*)\])?", l)
                if m:
                    metodo = m.group(2).upper() if m.group(2) != "route" else ", ".join(re.findall(r"[A-Za-z]+", m.group(4) or "GET")).upper()
                    nombre = next((re.match(r"\s*(?:async\s+)?def\s+(\w+)", x).group(1) for x in lineas[i + 1:i + 6]
                                   if re.match(r"\s*(?:async\s+)?def\s+(\w+)", x)), "?")
                    out.append({"metodo": metodo, "ruta": m.group(3), "manejador": nombre, "rel": rel, "linea": i + 1})
                d = re.search(r"\b(?:re_)?path\(\s*['\"]([^'\"]*)['\"]\s*,\s*([\w.]+)", l)
                if d and "urls" in rel:
                    out.append({"metodo": "(cualquiera)", "ruta": "/" + d.group(1).lstrip("/"), "manejador": d.group(2), "rel": rel, "linea": i + 1})
    return out


def variables_entorno(proyecto):
    """{NOMBRE: (archivo, línea)} de .env.example y del uso en el código."""
    out = {}
    for rel in proyecto.otros.get("env", []):
        for n, l in enumerate(proyecto.texto(rel).splitlines(), 1):
            m = re.match(r"\s*([A-Z][A-Z0-9_]*)\s*=", l)
            if m:
                out.setdefault(m.group(1), (rel, n))
    patrones = {"php": r"(?:getenv|env)\(\s*['\"]([A-Z][A-Z0-9_]*)|\$_ENV\[\s*['\"]([A-Z][A-Z0-9_]*)",
                "js": r"process\.env\.([A-Z][A-Z0-9_]*)|process\.env\[\s*['\"]([A-Z][A-Z0-9_]*)",
                "py": r"os\.environ(?:\.get)?\(\s*['\"]([A-Z][A-Z0-9_]*)|os\.environ\[\s*['\"]([A-Z][A-Z0-9_]*)|os\.getenv\(\s*['\"]([A-Z][A-Z0-9_]*)"}
    for rel, leng in proyecto.codigo:
        texto = proyecto.texto(rel)
        for m in re.finditer(patrones[leng], texto):
            nombre = next(g for g in m.groups() if g)
            out.setdefault(nombre, (rel, linea_de(texto, m.start())))
    return dict(sorted(out.items()))


STACK = {
    "framework web": {"laravel/framework": "Laravel", "symfony/framework-bundle": "Symfony", "slim/slim": "Slim", "cakephp/cakephp": "CakePHP",
                      "express": "Express", "fastify": "Fastify", "koa": "Koa", "next": "Next.js", "nuxt": "Nuxt", "@nestjs/core": "NestJS",
                      "django": "Django", "flask": "Flask", "fastapi": "FastAPI"},
    "interfaz": {"react": "React", "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular", "jquery": "jQuery",
                 "bootstrap": "Bootstrap", "tailwindcss": "Tailwind CSS", "livewire/livewire": "Livewire", "inertiajs/inertia-laravel": "Inertia"},
    "base de datos y acceso a datos": {"doctrine/orm": "Doctrine", "prisma": "Prisma", "@prisma/client": "Prisma", "sequelize": "Sequelize",
                                       "typeorm": "TypeORM", "mongoose": "Mongoose", "sqlalchemy": "SQLAlchemy", "flask-sqlalchemy": "SQLAlchemy",
                                       "psycopg2": "PostgreSQL", "psycopg2-binary": "PostgreSQL", "pg": "PostgreSQL", "mysql2": "MySQL",
                                       "pymysql": "MySQL", "mysqlclient": "MySQL", "redis": "Redis", "predis/predis": "Redis"},
    "autenticación": {"laravel/sanctum": "Laravel Sanctum", "laravel/passport": "Laravel Passport", "passport": "Passport",
                      "jsonwebtoken": "JSON Web Tokens", "firebase/php-jwt": "JSON Web Tokens", "pyjwt": "JSON Web Tokens",
                      "django-allauth": "django-allauth", "flask-login": "Flask-Login", "bcrypt": "bcrypt"},
    "tareas en segundo plano": {"celery": "Celery", "laravel/horizon": "Laravel Horizon", "bull": "Bull", "bullmq": "BullMQ"},
    "pruebas": {"phpunit/phpunit": "PHPUnit", "pestphp/pest": "Pest", "jest": "Jest", "vitest": "Vitest", "mocha": "Mocha", "pytest": "pytest"},
    "empaquetado": {"vite": "Vite", "webpack": "webpack", "typescript": "TypeScript", "laravel-mix": "Laravel Mix"},
}


def decisiones_stack(proyecto):
    """[{categoria, componentes:[(nombre, archivo, línea)]}] según los manifiestos de dependencias."""
    encontrados = defaultdict(dict)
    for rel in proyecto.otros.get("manifiestos", []):
        texto = proyecto.texto(rel)
        lineas = texto.splitlines()
        for categoria, paquetes in STACK.items():
            for paquete, etiqueta in paquetes.items():
                if rel.endswith(("composer.json", "package.json")):
                    patron = r'"' + re.escape(paquete) + r'"\s*:'
                else:
                    patron = r"(?im)^\s*[\"']?" + re.escape(paquete) + r"[\"']?\s*(?:[=<>~!\[;]|$|\s)"
                for n, l in enumerate(lineas, 1):
                    if re.search(patron, l):
                        encontrados[categoria].setdefault(etiqueta, (rel, n))
                        break
    return [{"categoria": c, "componentes": [(e, *ev) for e, ev in sorted(comp.items())]} for c, comp in encontrados.items()]


PALABRAS_DOMINIO = re.compile(r"(precio|price|total|descuento|discount|iva|tax|impuesto|recargo|interes|interest|comision|fee|stock|saldo|balance|"
                              r"edad|age|limite|limit|plazo|dias|days|vencimiento|expir|maximo|minimo|cuota|monto|amount|tarifa|rate|estado|status|rol|role|permiso)", re.I)
ES_COMPARACION = re.compile(r"(?:\bif\b|\belif\b|\belseif\b|\bwhile\b|\bwhen\b|\?|&&|\|\||\band\b|\bor\b)[^\n]*?(?:[<>]=?|===?|!==?)\s*-?\d+(?:[.,]\d+)?")
ES_CONSTANTE = re.compile(r"\b(?:const\s+|define\(\s*['\"])?([A-Z][A-Z0-9_]{2,})\b['\"]?\s*(?:=|,)\s*-?\d+(?:\.\d+)?")
ES_VALIDACION = re.compile(r"['\"](?:required|nullable|sometimes)[^'\"]*\|[^'\"]+['\"]|['\"](?:min|max|between|size|in|unique|exists|regex)\s*:[^'\"]+['\"]|"
                           r"\.(?:min|max|length|email|regex)\(\s*\d|max_length\s*=\s*\d+|min_length\s*=\s*\d+|validators\s*=|Length\(\s*min")
ES_PERMISO = re.compile(r"\b(?:hasRole|hasPermission|can|authorize|is_admin|isAdmin|permission_required|login_required|role_required|@Roles)\b")
ES_ESTADO = re.compile(r"\bconst\s+[A-Z_]*(?:ESTADO|STATUS|ROL|ROLE|TIPO|TYPE)\w*\s*=|^\s*class\s+\w+\([^)]*Enum\)|^\s*enum\s+\w+")


def lineas_de_docstrings(texto):
    """Líneas de Python que son documentación (cadenas sueltas como docstrings): no son reglas aunque nombren valores."""
    import ast
    try:
        arbol = ast.parse(texto)
    except (SyntaxError, ValueError):
        return set()
    res = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, str):
            res.update(range(nodo.lineno, (nodo.end_lineno or nodo.lineno) + 1))
    return res


def reglas_candidatas(proyecto):
    out = []
    for rel, leng in proyecto.codigo:
        if "migrations" in Path(rel).parts:
            continue
        texto = proyecto.texto(rel)
        documentacion = lineas_de_docstrings(texto) if leng == "py" else set()
        for n, linea in enumerate(texto.splitlines(), 1):
            codigo = sin_comentarios(linea, leng).strip()
            if len(codigo) < 6 or len(codigo) > 220 or n in documentacion or "re.compile(" in codigo:
                continue
            tipo, puntaje = None, 0
            if ES_VALIDACION.search(codigo):
                tipo, puntaje = "validación", 2
            elif ES_PERMISO.search(codigo):
                tipo, puntaje = "permiso", 2
            elif ES_ESTADO.search(codigo):
                tipo, puntaje = "estados", 2
            elif ES_COMPARACION.search(codigo):
                numeros = [float(x.replace(",", ".")) for x in re.findall(r"(?:[<>]=?|[!=]==?)\s*(-?\d+(?:[.,]\d+)?)", codigo)]
                if numeros and not all(x in (0.0, 1.0, -1.0) for x in numeros):
                    tipo, puntaje = "umbral", 2
                elif PALABRAS_DOMINIO.search(codigo):
                    tipo, puntaje = "umbral", 1
            elif ES_CONSTANTE.search(codigo) and PALABRAS_DOMINIO.search(codigo):
                tipo, puntaje = "constante", 2
            if tipo:
                if PALABRAS_DOMINIO.search(codigo):
                    puntaje += 1
                out.append({"tipo": tipo, "rel": rel, "linea": n, "texto": codigo[:140], "puntaje": puntaje})
    return out
