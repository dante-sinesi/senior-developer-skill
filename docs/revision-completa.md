# Revisión completa del paquete senior (documento vivo)

Auditoría crítica de todas las partes del paquete: qué tan bien funciona cada una, dónde puede fallar y qué mejora más. Es la **base para seguir creciendo**: de acá salen las próximas tareas y acá se anota lo que se hizo. Las notas son un juicio (0 a 10) apoyado en mediciones hechas sobre el repositorio, no una métrica automática.

## Cómo se mantiene

Cada Pull Request que toque una parte puntuada o un punto ciego actualiza este documento **en el mismo PR**:

1. **Puntaje por parte:** cambia «Nota hoy» solo si hay evidencia (una prueba, una medición o un uso real), y ajusta «Mejora propuesta» (lo hecho se tacha con ~~esto~~ y se deja lo que falta).
2. **Puntos ciegos:** cambia el estado (**Abierto**, **En curso**, **Parcial**, **Resuelto**) y anota la rama o el PR. Un punto ciego nuevo que aparezca se agrega con el número siguiente.
3. **Historial:** una fila por cambio, con fecha, PR y las notas que se movieron.
4. **Promedio global:** se recalcula con las filas de la tabla.

Si una nota baja (algo se rompió o se descubrió un problema), se anota igual: el documento sirve si es honesto.

## Cómo se midió

- **Inventario:** 131 archivos versionados al inicio, 16 skills y unas 10.900 líneas de Python. La skill `senior` es la más grande (18 scripts, ~5.000 tokens al activarse) y `senior-diseno` la segunda (9 scripts, 12 referencias).
- **Hooks:** 28 formas de escribir fuera del proyecto (y de solo leer) contra el hook real. Al inicio **6 se le escapaban**; ahora se frenan todas y `tests/probar_hook_fuera.py` las vigila. Cada hook tarda unos 180 ms y una llamada de Bash o Write pasa por 3 a 5 (de ~0,55 s a ~0,9 s).
- **Documentación inferida:** `/documentar-proyecto` se corrió sobre código Python real (este repositorio, copiado a `.temporal/`). Encontró módulos y variables de entorno, pero 2 de las 6 primeras «reglas de negocio» eran falsos positivos (un docstring y una expresión regular); ya no salen.
- **Compatibilidad:** el README prometía Python 3.8, pero 15 scripts usaban `Path.write_text(newline=…)` (3.10+) y un hook usaba `str.removesuffix` (3.9). El CI de GitHub lo mostró en el primer intento. En una versión vieja el hook se rompía y, como un hook que falla no bloquea, dejaba de proteger sin avisar. El mínimo documentado es **Python 3.10**.
- **Secretos:** la batería `tests/probar_secretos.py` arma claves falsas al vuelo y comprueba el detector, `.env` con y sin permiso, los hooks de git sobre un repositorio y un remoto de prueba y 27 casos del hook de Claude.

## Puntaje por parte, con su mejora

| Parte | Nota inicial | Nota hoy | Mejora propuesta | Nota estimada con la mejora |
|---|---|---|---|---|
| `senior` (principios y flujo) | 8 | 8 | Dejar el cuerpo en menos de 3.000 tokens moviendo excusas, puntos de control y duda a `references/`, y que `verificar.py` avise si el cuerpo de una skill pasa un tope. | 9 |
| `senior-tdd` | 7,5 | 7,5 | La guardia de base de datos hoy mira pocos patrones: sumar detección por `.env`, Django, Laravel y Prisma, versionar su prueba y agregar un ejemplo de rojo derivado de una regla. | 8,5 |
| `senior-refactor` | 7 | 7 | Detectar duplicación por estructura (`ast`, nombres normalizados) en lugar de similitud de texto, con umbral configurable y una propuesta de extracción. | 8 |
| `senior-docs` y diagramas | 8 | 8 | Soportar subgrafos en el estimador de ancho, comprobar el render real con Mermaid en una verificación opcional y avisar de enlaces rotos entre documentos. | 8,5 |
| `senior-memoria` | 7,5 | 7,5 | Que `verificar.py estado` detecte un `ESTADO.md` más viejo que los últimos commits y que las fichas viejas se archiven con propuesta. | 8,5 |
| `senior-git` (autoría) | 8,5 | 9 | Falta una prueba de punta a punta (rama, commit, PR) y que `asegurar` avise cuando las skills instaladas están desactualizadas (punto ciego 11). | 9 |
| `senior-seguridad` | 7 | 7,5 | Cuando haya herramientas instaladas (`bandit`, `semgrep`), usarlas además de las expresiones regulares, y sumar una plantilla de registro de riesgos ISO 27005. | 8,5 |
| Secretos y datos personales (`secretos.py`) | — (no existía) | 7,5 | Activar la protección de subida de GitHub (la activa el usuario), ampliar formatos (Azure, Twilio, Mailgun, JSON de cuentas de servicio) y medir la precisión con falsos positivos de proyectos reales. | 8,5 |
| `senior-lenguajes` | 6,5 | 6,5 | Perfiles para Python, Go, Rust, C# y Java (hoy solo PHP, JS/TS, CSS, SQL y HTML) y llevar `probar_perfil.py` a `tests/`. | 8 |
| `senior-relevar` | 8 | 8 | Leer md, txt, csv y json sin depender de `markitdown`, y probarlo con PDF y Word reales de un proyecto del usuario. | 8,5 |
| `senior-diseno` y tarjeta de estilo | 7 | 7 | Probarlo en dos proyectos reales (una web y un juego), recortar sus 12 referencias y validar con la revisión a ciegas del usuario. Su descripción ya bajó de 1.034 a 773 caracteres. | 8 |
| `/documentar-proyecto` | 6,5 | 7 | Probarlo en tres proyectos reales (PHP, JS y Python), mapear las importaciones dentro de un mismo módulo y calibrar qué cuenta como «umbral» (hoy entra el tope de un bucle). | 8 |
| `/adoptar-proyecto` y `/cerrar-sesion` | 7,5 | 7,5 | Pruebas de punta a punta sobre un proyecto vacío y uno existente, con el plan mostrado antes de escribir. | 8,5 |
| `/revisar-cambio` y `/auditar-*` | 7,5 | 7,5 | Ejemplos de informe reales en `references/` y que `auditar-diseno` quede cubierto por una prueba (usa el script de `senior-diseno`, no tiene uno propio). | 8,5 |
| Hooks globales | 6 | 7 | Despachador único, modo de depuración en todos, escalada ante la reincidencia, resumen de bloqueos y una segunda capa para las escrituras desde Bash (puntos ciegos 1, 2, 6, 7 y 10). | 8,5 |
| `instalar.py` y empaquetado | 6,5 | 7,5 | Agregar `instalar.py --verificar` (compara lo instalado con el repositorio), `--desinstalar`, etiquetas de versión en GitHub y una licencia (la elige el usuario). | 8,5 |
| Pruebas y CI | 4 | 7 | Ver el CI en verde en GitHub con Linux y macOS tras adaptar las rutas, y medir cobertura. | 8,5 |

**Nota global** (promedio de las filas): 7,1 al inicio (16 partes; secretos no existía), **7,5 hoy** (17 partes) y 8,4 estimada si se hace todo lo propuesto. Las notas «con la mejora» son estimaciones: la mejora real solo se ve al usar la parte en proyectos reales.

## Puntos ciegos y cómo resolverlos

| # | Punto ciego | Por qué importa | Propuesta | Estado |
|---|---|---|---|---|
| 1 | El guardián de «nada fuera del proyecto» es una lista de patrones. | Cualquier forma de escribir que no esté en la lista pasa (un script guardado en un archivo, una ruta armada con código). Es una barrera contra descuidos, no contra una evasión deliberada. | Dejarlo dicho (ya está en el README) y sumar una segunda capa. Ojo: las reglas `deny` de Bash **no** cubren cualquier comando (la documentación de Claude Code lo desmiente); la segunda capa real es el sandbox (no existe en Windows nativo) y, para las herramientas de archivos, `permissions.blockWritesOutsideWorkingDirectories`. | Abierto |
| 2 | Todo depende de que el modelo obedezca el mensaje de bloqueo. | Quien deja a Claude horas sin supervisión no puede corregirlo: si insiste, gasta turnos. | ~~Contar la reincidencia en el registro y, a la tercera vez, que el mensaje pase a ser un alto y proponga la barrera (principio 17).~~ Hecho en todos los hooks que bloquean. Falta la sesión larga real de varias horas, que solo puede hacer el usuario, para ver si el alto alcanza. | Parcial (rama `mejora/ciego-02-reincidencia`) |
| 3 | Las baterías de pruebas no eran del proyecto. | Un cambio mañana no las corría nadie, y nadie más podía reproducirlas. | `tests/` y CI en verde con Python 3.10 y 3.12 sobre Windows. Falta sumar otros sistemas operativos (punto 8). | Resuelto |
| 4 | `/documentar-proyecto`, la tarjeta de estilo y la propuesta de diagramas no se usaron en un proyecto real. | Todo se validó con ejemplos inventados. Sobre código Python real (este repositorio) el análisis funcionó pero mostró ruido. | Pilotos en tres proyectos reales con una lista de comprobación y anotar qué sobra y qué falta antes de agregar funciones. | Abierto |
| 5 | El paquete crece más rápido de lo que se usa. | Cada pieza suma contexto (~4.350 tokens fijos por sesión) y superficie de fallos. | Un tope de tokens por skill que `verificar.py` haga cumplir y una regla: no se agrega una skill o script sin un caso de uso anotado. | Abierto |
| 6 | El estado de los hooks vive en `.git/senior-hooks.json`. | Es difícil entender por qué algo se bloqueó o se dejó pasar, y no se ve entre equipos. | ~~Que `/cerrar-sesion` muestre los bloqueos de la sesión y `/permisos` explique cada regla activa.~~ Hecho: `/permisos` y `permisos_hooks.py estado` explican qué frena cada hook y cómo se autoriza; `permisos_hooks.py resumen` lo usa `/cerrar-sesion`. Lo que no resuelve: el archivo sigue siendo local de cada clon. | Resuelto (rama `mejora/ciego-06-resumen-bloqueos`) |
| 7 | Hasta cinco procesos de Python por cada llamada de Bash o Write. | De ~0,55 s a ~0,9 s de espera por llamada; en una sesión de miles de llamadas es tiempo real. | Un despachador único que ejecute los controles en el mismo proceso. | Abierto |
| 8 | Todo se probó en Windows. | En Linux y macOS las rutas (`C:/...`, `/c/...`) y varias pruebas pueden comportarse distinto. | Matriz de CI con Ubuntu y macOS, adaptando `a_ruta` y las pruebas que usan rutas de Windows. | Abierto |
| 9 | Mermaid solo se vio dibujado en la versión 10.9.1 de la comparación. | GitHub puede dibujar distinto (ancho, flechas de retorno). | Mirar el README en GitHub y ajustar los diagramas con lo que se vea. | Abierto |
| 10 | Un hook que falla **abre en silencio**. | Pasó dos veces: con una versión de Python vieja y con un error de expresión regular; todo «pasaba» porque el hook no frenaba nada. | `SENIOR_HOOK_DEPURAR=1` hace visible la caída. Está en el hook de escritura y en el de secretos; falta extenderlo a los demás y vigilarlo con una prueba. | Parcial |
| 11 | Lo instalado y el repositorio se desalinean. | Los hooks usan las copias de `~/.claude/skills`: si no se reinstala, protege la versión vieja. | `instalar.py --verificar` y un aviso en `asegurar` cuando difieren. | Abierto |
| 12 | `auditar-consumo` mide lo instalado, no el repositorio. | Tras recortar una skill, la medición no cambia hasta reinstalar. | Un modo `--repo` que mida las skills de la carpeta actual. | Abierto |
| 13 | Las heurísticas son aproximadas (reglas candidatas, estimador de ancho ±15 %, análisis por patrones). | Pueden proponer reglas que no son o no ver relaciones dinámicas. | Mantener todo como provisorio con evidencia, medir la precisión en los pilotos del punto 4 y ajustar. | Abierto |
| 14 | `markitdown` y `Pillow` son obligatorias y no se instalan solas. | En una máquina nueva el primer documento externo se frena hasta que el usuario las instale. | `instalar.py` ya las comprueba; sumar un mensaje con el comando exacto al primer bloqueo. | Abierto |
| 15 | La protección de subida de GitHub no está activada y los secretos se detectan por patrones. | Es la única barrera que no se saltea con `--no-verify`; una clave partida, codificada o con un formato desconocido puede pasar los hooks locales. | Activarla en Settings → Code security (acción del usuario; `secretos.py github` comprueba el estado) y ampliar los formatos con lo que aparezca. | Abierto |

## Historial

| Fecha | Cambio | Partes y puntos que se movieron |
|---|---|---|
| 2026-11-12 | PR #28, revisión completa: hook de escritura sin fugas, 19 baterías en `tests/`, CI y mínimo de Python 3.10. | Hooks 6→7, pruebas y CI 4→7, instalación 6,5→7,5, `/documentar-proyecto` 6,5→7, `senior-git` 8,5→9; puntos 3 resuelto y 10 parcial. |
| 2026-11-12 | PR #29, secretos y datos personales: detector, hooks de git y de Claude, `.env` con permiso del usuario. | Parte nueva «Secretos» (7,5), `senior-seguridad` 7→7,5; punto 15 nuevo. |
| 2026-11-12 | Este documento pasa a ser un documento vivo, con estado por punto ciego, historial y reglas de mantenimiento. | Ninguna nota. |
| 2026-11-12 | Punto 2: los bloqueos repetidos se cuentan y, a la tercera vez, el mensaje se vuelve un alto que manda a avisar al usuario y proponer una autorización o una barrera. | Punto 2 parcial; ninguna nota (falta verlo en una sesión larga real). |
| 2026-11-12 | Punto 6: `/permisos` y `estado` explican cada regla y cómo se autoriza; `/cerrar-sesion` resume los bloqueos de la sesión y marca los que reinciden. | Punto 6 resuelto; ninguna nota. |

### Detalle del PR #28 (revisión completa)

Qué se hizo en esa rama:

1. **Hook de escritura:** reemplazado `removesuffix`, cerradas las 6 fugas (`python -c` y heredocs, `node -e`, `sed -i`, `dd of=`, rutas armadas con variables encadenadas), rutas de red sin consulta a la red y modo de depuración. Pasó de 6 fallos en 28 casos a 0.
2. **Pruebas versionadas:** 19 baterías en `tests/`, un corredor (`tests/correr_todo.py`), pruebas nuevas de hook, compatibilidad con la versión mínima y consistencia de carpetas ignoradas, y CI en `.github/workflows/pruebas.yml`. Tres pruebas dependían del estado del árbol de trabajo o escribían fuera del proyecto, y se arreglaron. El mínimo de Python sube a 3.10 (README, `instalar.py` y CI con 3.10 y 3.12).
3. **Hook de Git de este clon** instalado (`guardia_autoria.py instalar`) y carpetas ignoradas alineadas (dos scripts no ignoraban `dist`, `build` ni los entornos virtuales).
4. **`/documentar-proyecto` sobre código real:** las líneas de docstrings y las definiciones de expresiones regulares ya no se proponen como reglas, con su prueba.
5. **Peso:** la descripción de `senior-diseno` baja de 1.034 a 773 caracteres y el cuerpo de `senior` de ~5.300 a ~4.750 tokens (el detalle del hook pasó a `references/hooks.md`). Es una mejora parcial: el tope de 3.000 sigue pendiente.

Promedio en ese momento: (promedio de las 16 filas): 7,1 al inicio, **7,4 hoy** y 8,4 estimada si se hace todo lo propuesto. Las notas «con la mejora» son estimaciones: la mejora real solo se ve al usar la parte en proyectos reales.

**No se verificó entonces:** el CI en GitHub, Linux y macOS, ni el comportamiento de los hooks nuevos en una sesión viva (hay que reinstalar con `python instalar.py` y abrir una sesión nueva).

## Cómo seguir creciendo

El orden sugerido sale de lo que más pesa en las notas y de lo que desbloquea evidencia real:

1. **Cerrar los puntos ciegos abiertos de los hooks** (1, 2, 6, 7, 10), que son la barrera de la regla máxima y la de secretos.
2. **Instalación al día** (11, 12, 14): que lo instalado no se desalinee sin que nadie lo note.
3. **Pilotos en proyectos reales** (4 y 13): es lo que más sube las notas de `/documentar-proyecto`, diseño y secretos, y lo que ninguna prueba reemplaza.
4. **Otros sistemas operativos** (8) y la capa de GitHub (15).
5. **Peso** (5 y la fila de `senior`): un tope por skill que se haga cumplir.

Un hallazgo nuevo (de un uso real, una prueba que falla o una medición) se agrega como punto ciego con su estado y entra en este orden según lo que rompa.
