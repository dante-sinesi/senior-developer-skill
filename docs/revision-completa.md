# Revisión completa del paquete senior

Auditoría crítica de todas las partes del paquete: qué tan bien funciona cada una, dónde puede fallar y qué mejora más. Las notas son un juicio (0 a 10) apoyado en mediciones hechas sobre el repositorio, no una métrica automática.

## Cómo se midió

- **Inventario:** 131 archivos versionados, 16 skills, unas 10.900 líneas de Python. La skill `senior` es la más grande (17 scripts, ~4.750 tokens al activarse) y `senior-diseno` la segunda (9 scripts, 12 referencias).
- **Hooks:** 28 formas de escribir fuera del proyecto (y de solo leer) contra el hook real. Al inicio **6 se le escapaban**; ahora se frenan todas y `tests/probar_hook_fuera.py` las vigila. Cada hook tarda unos 180 ms y una llamada de Bash o Write pasa por 3 (~0,55 s).
- **Documentación inferida:** `/documentar-proyecto` se corrió sobre código Python real (este mismo repositorio, copiado a `.temporal/`). Encontró módulos y variables de entorno, pero 2 de las 6 primeras «reglas de negocio» eran falsos positivos (un docstring y una expresión regular); ya no salen.
- **Compatibilidad:** el README prometía Python 3.8, pero 15 scripts usaban `Path.write_text(newline=…)` (3.10+) y un hook usaba `str.removesuffix` (3.9). El CI de GitHub lo mostró en el primer intento. En una versión vieja el hook se rompía y, como un hook que falla no bloquea, **dejaba de proteger sin avisar**. El mínimo documentado pasa a **Python 3.10** (3.8 y 3.9 ya no tienen soporte).

Qué se hizo en la rama `mejora/revision-completa` está en la sección final. «Nota hoy» ya lo incluye.

## Puntaje por parte, con su mejora

| Parte | Nota inicial | Nota hoy | Mejora propuesta | Nota estimada con la mejora |
|---|---|---|---|---|
| `senior` (principios y flujo) | 8 | 8 | Dejar el cuerpo en menos de 3.000 tokens moviendo excusas, puntos de control y duda a `references/`, y que `verificar.py` avise si el cuerpo de una skill pasa un tope. | 9 |
| `senior-tdd` | 7,5 | 7,5 | La guardia de base de datos hoy mira pocos patrones: sumar detección por `.env`, Django, Laravel y Prisma, versionar su prueba y agregar un ejemplo de rojo derivado de una regla. | 8,5 |
| `senior-refactor` | 7 | 7 | Detectar duplicación por estructura (`ast`, nombres normalizados) en lugar de similitud de texto, con umbral configurable y una propuesta de extracción. | 8 |
| `senior-docs` y diagramas | 8 | 8 | Soportar subgrafos en el estimador de ancho, comprobar el render real con Mermaid en una verificación opcional y avisar de enlaces rotos entre documentos. | 8,5 |
| `senior-memoria` | 7,5 | 7,5 | Que `verificar.py estado` detecte un `ESTADO.md` más viejo que los últimos commits y que las fichas viejas se archiven con propuesta. | 8,5 |
| `senior-git` (autoría) | 8,5 | 9 | El hook de Git de este clon ya está instalado. Falta una prueba de punta a punta (rama, commit, PR) y que `asegurar` avise cuando las skills instaladas están desactualizadas. | 9 |
| `senior-seguridad` | 7 | 7 | Cuando haya herramientas instaladas (`bandit`, `semgrep`), usarlas además de las expresiones regulares, y sumar una plantilla de registro de riesgos ISO 27005. | 8 |
| `senior-lenguajes` | 6,5 | 6,5 | Perfiles para Python, Go, Rust, C# y Java (hoy solo PHP, JS/TS, CSS, SQL y HTML) y llevar `probar_perfil.py` a `tests/`. | 8 |
| `senior-relevar` | 8 | 8 | Leer md, txt, csv y json sin depender de `markitdown`, y probarlo con PDF y Word reales de un proyecto del usuario. | 8,5 |
| `senior-diseno` y tarjeta de estilo | 7 | 7 | Probarlo en dos proyectos reales (una web y un juego), recortar sus 12 referencias y validar con la revisión a ciegas del usuario. Su descripción ya bajó de 1.034 a 773 caracteres. | 8 |
| `/documentar-proyecto` | 6,5 | 7 | Probarlo en tres proyectos reales (PHP, JS y Python), mapear las importaciones dentro de un mismo módulo y calibrar qué cuenta como «umbral» (hoy entra el tope de un bucle). | 8 |
| `/adoptar-proyecto` y `/cerrar-sesion` | 7,5 | 7,5 | Pruebas de punta a punta sobre un proyecto vacío y uno existente, con el plan mostrado antes de escribir. | 8,5 |
| `/revisar-cambio` y `/auditar-*` | 7,5 | 7,5 | Ejemplos de informe reales en `references/` y que `auditar-diseno` quede cubierto por una prueba (usa el script de `senior-diseno`, no tiene uno propio). | 8,5 |
| Hooks globales | 6 | 7 | Reunir los tres hooks de Bash y Write en un solo despachador (un proceso en lugar de tres), correr una sesión larga para medir cuántas veces Claude reincide tras un bloqueo y extender el modo de depuración a los demás hooks. | 8,5 |
| `instalar.py` y empaquetado | 6,5 | 7,5 | Agregar `instalar.py --verificar` (compara lo instalado con el repositorio), `--desinstalar`, etiquetas de versión en GitHub y una licencia (la elige el usuario). | 8,5 |
| Pruebas y CI | 4 | 7 | Ver el CI en verde en GitHub (no se pudo verificar desde acá), sumar Linux y macOS tras adaptar las rutas y medir cobertura. | 8,5 |

**Nota global** (promedio de las 16 filas): 7,1 al inicio, **7,4 hoy** y 8,4 estimada si se hace todo lo propuesto. Las notas «con la mejora» son estimaciones: la mejora real solo se ve al usar la parte en proyectos reales.

## Puntos ciegos y cómo resolverlos

| # | Punto ciego | Por qué importa | Propuesta |
|---|---|---|---|
| 1 | El guardián de «nada fuera del proyecto» es una lista de patrones. | Cualquier forma de escribir que no esté en la lista pasa (un script guardado en un archivo, una ruta armada con código). Es una barrera contra descuidos, no contra una evasión deliberada. | Dejarlo dicho (ya está en el README) y sumar una segunda capa con las reglas `deny` de permisos de Claude Code, que sí cubren cualquier comando. |
| 2 | Todo depende de que el modelo obedezca el mensaje de bloqueo. | Quien deja a Claude horas sin supervisión no puede corregirlo: si insiste, gasta turnos. | Sesión larga de prueba con tareas que provoquen bloqueos y contar la reincidencia en el registro; si un mismo destino se bloquea tres veces, que el mensaje suba de tono y proponga la barrera (principio 17). |
| 3 | Las baterías de pruebas no eran del proyecto. | Un cambio mañana no las corría nadie, y nadie más podía reproducirlas. | **Hecho:** `tests/` y CI. Falta verlo en verde en GitHub y sumar otros sistemas operativos. |
| 4 | `/documentar-proyecto`, la tarjeta de estilo y la propuesta de diagramas no se usaron en un proyecto real. | Todo se validó con ejemplos inventados. Sobre código Python real (este repositorio) el análisis funcionó pero mostró ruido. | Pilotos en tres proyectos reales con una lista de comprobación y anotar qué sobra y qué falta antes de agregar funciones. |
| 5 | El paquete crece más rápido de lo que se usa. | Cada pieza suma contexto (~4.350 tokens fijos por sesión) y superficie de fallos. | Un tope de tokens por skill que `verificar.py` haga cumplir y una regla: no se agrega una skill o script sin un caso de uso anotado. |
| 6 | El estado de los hooks vive en `.git/senior-hooks.json`. | Es difícil entender por qué algo se bloqueó o se dejó pasar, y no se ve entre equipos. | Que `/cerrar-sesion` muestre los bloqueos de la sesión y `/permisos` explique cada regla activa. |
| 7 | Tres procesos de Python por cada llamada de Bash o Write. | ~0,55 s de espera por llamada; en una sesión de miles de llamadas es tiempo real. | Un despachador único que ejecute los tres controles en el mismo proceso. |
| 8 | Todo se probó en Windows. | En Linux y macOS las rutas (`C:/...`, `/c/...`) y varias pruebas pueden comportarse distinto. | Matriz de CI con Ubuntu y macOS, adaptando `a_ruta` y las pruebas que usan rutas de Windows. |
| 9 | Mermaid solo se vio dibujado en la versión 10.9.1 de la comparación. | GitHub puede dibujar distinto (ancho, flechas de retorno). | Mirar el README en GitHub y ajustar los diagramas con lo que se vea. |
| 10 | Un hook que falla **abre en silencio**. | Pasó dos veces: con una versión de Python vieja y con un error de expresión regular durante esta revisión; todo «pasaba» porque el hook no frenaba nada. | **Hecho en el hook de escritura:** con `SENIOR_HOOK_DEPURAR=1` la caída interna se hace visible y las pruebas la usan. Extenderlo a los otros cuatro hooks. |
| 11 | Lo instalado y el repositorio se desalinean. | Los hooks usan las copias de `~/.claude/skills`: si no se reinstala, protege la versión vieja (hoy el hook instalado no tiene las correcciones de esta rama). | `instalar.py --verificar` y un aviso en `asegurar` cuando difieren. |
| 12 | `auditar-consumo` mide lo instalado, no el repositorio. | Tras recortar una skill, la medición no cambia hasta reinstalar. | Un modo `--repo` que mida las skills de la carpeta actual. |
| 13 | Las heurísticas son aproximadas (reglas candidatas, estimador de ancho ±15 %, análisis por patrones). | Pueden proponer reglas que no son o no ver relaciones dinámicas. | Mantener todo como provisorio con evidencia, medir la precisión en los pilotos del punto 4 y ajustar. |
| 14 | `markitdown` y `Pillow` son obligatorias y no se instalan solas. | En una máquina nueva el primer documento externo se frena hasta que el usuario las instale. | `instalar.py` ya las comprueba; sumar un mensaje con el comando exacto al primer bloqueo. |

## Qué se hizo en esta rama

1. **Hook de escritura:** reemplazado `removesuffix`, cerradas las 6 fugas (`python -c` y heredocs, `node -e`, `sed -i`, `dd of=`, rutas armadas con variables encadenadas), rutas de red sin consulta a la red y modo de depuración. Pasó de 6 fallos en 28 casos a 0.
2. **Pruebas versionadas:** 19 baterías en `tests/`, un corredor (`tests/correr_todo.py`), pruebas nuevas de hook, compatibilidad con la versión mínima y consistencia de carpetas ignoradas, y CI en `.github/workflows/pruebas.yml`. Tres pruebas dependían del estado del árbol de trabajo o escribían fuera del proyecto, y se arreglaron. El mínimo de Python sube a 3.10 (README, `instalar.py` y CI con 3.10 y 3.12).
3. **Hook de Git de este clon** instalado (`guardia_autoria.py instalar`) y carpetas ignoradas alineadas (dos scripts no ignoraban `dist`, `build` ni los entornos virtuales).
4. **`/documentar-proyecto` sobre código real:** las líneas de docstrings y las definiciones de expresiones regulares ya no se proponen como reglas, con su prueba.
5. **Peso:** la descripción de `senior-diseno` baja de 1.034 a 773 caracteres y el cuerpo de `senior` de ~5.300 a ~4.750 tokens (el detalle del hook pasó a `references/hooks.md`). Es una mejora parcial: el tope de 3.000 sigue pendiente.

**No se verificó:** el CI en GitHub, Linux y macOS, ni el comportamiento de los hooks nuevos en una sesión viva (hay que reinstalar con `python instalar.py` y abrir una sesión nueva).
