# Guía del paquete `senior`, punto por punto

Qué abarca el paquete y cómo ataca cada una de sus habilidades. Es una guía de lectura: el detalle de cada regla vive en el `SKILL.md` y en las `references/` de cada skill, y el estado de mejora del paquete, en [`revision-completa.md`](revision-completa.md).

## 1. Qué es y qué problema ataca

`senior` es un paquete de 17 skills para Claude Code que hace que el trabajo de programar se parezca al de una persona senior: entiende antes de tocar, cambia lo mínimo, prueba antes de construir, deja todo documentado y no sorprende a nadie. No es una herramienta que programa por sí sola: es un **método**, más **guardias automáticos** que impiden lo que no debe pasar aunque nadie se acuerde de la regla.

Los problemas concretos que ataca, y con qué:

| Problema | Cómo se ataca | Dónde |
|---|---|---|
| Tests que certifican los errores del código | El test sale de la regla de negocio, nunca de lo que el código devuelve hoy | `senior-tdd` |
| Cambios que se desbordan («ya que estoy…») | Cambio mínimo, refactor acordado y en paso aparte | `senior`, `senior-refactor` |
| Contexto que se pierde entre sesiones | Estado, fichas y pendientes dentro del repositorio | `senior-memoria` |
| Documentación vieja o que no se entiende | Documentación viva, con IDs, diagramas con tope de tamaño y chequeos por script | `senior-docs` |
| Claves o datos personales en GitHub | Cuatro capas de barrera (`.gitignore`, hook de Claude, hooks de git, protección de GitHub) | `senior` (secretos) |
| Claude figurando como autor en GitHub | Hooks que lo bloquean antes de que exista el commit | `senior-git` |
| Archivos creados fuera del proyecto | Hook global que bloquea y redirige a `.temporal/` | `senior` (hooks) |
| Sistemas heredados que nadie entiende | Relevamiento de lo barato a lo caro y tests de caracterización | `senior-relevar` |
| Interfaces genéricas o saturadas | Método de tres alternativas más reglas objetivas verificadas por script | `senior-diseno` |
| Revisiones que opinan sin casos | Hallazgos numerados, cada uno con un caso concreto | `revisar-cambio` |

## 2. Cómo está armado: cinco capas

1. **El método** (las skills): texto que Claude lee al activarse. Dice qué hacer y por qué.
2. **Los guardias** (hooks): programas que se ejecutan solos antes de cada acción y la bloquean si viola una regla. No dependen de que Claude «se acuerde».
3. **Las herramientas** (scripts): hacen en Python lo que no necesita criterio (medir, buscar, comparar) y devuelven pocas líneas, para que el modelo gaste su atención solo donde hace falta pensar.
4. **Los comandos** (`/adoptar-proyecto`, `/cerrar-sesion`, etc.): puertas de entrada para tareas completas.
5. **La memoria** (`docs/` del proyecto): lo que sobrevive a la conversación.

Principio de diseño: **lo que se puede verificar con un script no se le pide al modelo**, y **lo que importa de verdad se hace cumplir con una barrera, no con más texto**. Una regla que falló dos veces recibe una barrera, y la decide el usuario.

### Cómo se activa y cuánto pesa

- **Se activa sola** cuando se pide escribir, corregir o mantener código; el usuario no tiene que mencionarla. Se midió con agentes reales y se decidió dejarla así (ver el punto 6).
- **Núcleo corto y capa completa.** `senior/SKILL.md` es el núcleo (unas 570 palabras: lo que no se negocia y una tabla de tamaño). El método completo está en `senior/references/metodo-completo.md` y se lee solo en cambios medianos o grandes. El peso de todas las skills lo vigila `verificar.py peso` (descripciones de hasta 800 caracteres y 10.000 en total, cuerpos de hasta 3.500 tokens y 150 líneas).
- **Dependencia opcional:** [Token Diet](https://github.com/dante-sinesi/token-diet-skill), una skill independiente de ahorro de tokens. Con ella instalada, el PDF se lee con su conversor; sin ella, todo funciona igual y el paquete lo avisa una vez por proyecto.

## 3. Las habilidades, una por una

### 3.1 `senior`: la puerta de entrada y el método

- **Problema que ataca:** que cada tarea de código dependa del humor del día. Fija un comportamiento común.
- **Cómo lo ataca**
  - **Nueve reglas que no se negocian** (en el núcleo): test primero desde la regla de negocio; cambios mínimos; autoría solo del usuario; commit, push, PR y fusión solo con pedido; nada fuera del proyecto; ninguna clave ni dato personal en git; README al día; español neutro; una regla que falló dos veces recibe una barrera.
  - **Proporcionalidad:** un cambio trivial o chico (hasta unos 3 archivos y 50 líneas) se hace directo; uno mediano o grande lee el método completo y lleva ficha de cambio, plan y revisión de seguridad.
  - **La escalera antes de escribir:** ¿hace falta?, ¿ya existe en el proyecto?, ¿lo da la biblioteca estándar?, ¿lo resuelve una dependencia ya instalada?, y recién entonces lo mínimo que funciona. Nunca recorta tests, documentación ni seguridad.
  - **Dudar antes de dar por buena una decisión no trivial:** un subagente sin el hilo de la conversación intenta romperla con solo el artefacto y el contrato (`duda.py`).
  - **Puntos de control:** lista de cosas que siempre se consultan (arquitectura, borrar datos, agentes en paralelo, `.env`, salir del proyecto, resolver una discrepancia entre regla y código).
  - **Excusas frecuentes:** una tabla que anticipa los atajos típicos («es chico, no hace falta test») y la respuesta.
- **Herramientas:** `verificar.py` (el verificador, ver el punto 5), `escala.py`, `impacto.py`, `atajos.py`, `duda.py`, `env_gestion.py`, `abrir_en_navegador.py`, `temporal.py`, `peso.py` y los hooks (punto 4).
- **No hace:** no programa solo ni reemplaza la decisión del usuario sobre arquitectura o cambios de riesgo.
- **Medido:** con las tres tareas de prueba, el método sube los tests agregados de 6 a 9 de 9 y la documentación de 3 a 6 de 9; el usuario lo prefirió a ciegas en 6 de 6 pedidos. Cuesta unas 1,8 veces más (ver el punto 6).

### 3.2 `senior-tdd`: tests primero

- **Problema:** un test escrito mirando el código solo certifica sus errores.
- **Cómo lo ataca**
  - **Ciclo rojo, verde, refactor:** (1) se identifica la regla de negocio y, si no existe o es ambigua, se pregunta; (2) rojo: el test falla **por la razón correcta** (la aserción, no un import faltante); (3) verde: el mínimo código; (4) refactor con los tests en verde; (5) el test cita el ID del requisito.
  - **Regla y código discrepan:** el test debe fallar y se le consulta al usuario cuál manda.
  - **Un test en rojo no se afloja:** no se borra, no se saltea, no se baja el umbral; `verificar.py listones` lo detecta en el diff.
  - **Código heredado sin tests:** tests de caracterización («sacarle una foto») priorizados por riesgo, que se retiran cuando una regla confirmada los contradice.
  - **Sin infraestructura de tests:** el primer paso es crearla con la herramienta estándar del lenguaje (perfil de `senior-lenguajes`).
  - **Pruebas de interfaz:** como código, sin ventana, pocos recorridos críticos.
  - **Bases de datos:** los tests solo corren contra una base de prueba; `guardia_bd_prueba.py` se niega (código 2) si el nombre no parece de prueba.
  - **Agente verificador:** solo con autorización explícita, cada vez, porque cuesta entre 8.000 y 25.000 tokens.
- **Herramienta:** `guardia_bd_prueba.py`.
- **No hace:** no escribe tests desde lo que el código devuelve ni acepta «lo probé a mano».

### 3.3 `senior-refactor`: limpiar sin romper

- **Problema:** el código repetido falla el día que se cambia una copia y se olvida otra; pero un refactor sin red es una apuesta.
- **Cómo lo ataca:** tests en verde antes de empezar; un paso, un commit (`refactor:`); nunca mezclado con funcionalidad; acordado con el usuario; **regla de tres** (dos copias se toleran, a la tercera se extrae; la lógica de negocio crítica se unifica a la segunda); solo se abstrae lo que cambia por la misma razón.
- **Herramientas:** `duplicados.py` (bloques de N o más líneas idénticas, solo repetición literal), `impacto.py` y `comentarios.py` para la limpieza de comentarios.
- **No hace:** no refactoriza «de paso» y no detecta repetición con nombres cambiados (eso lo lee quien refactoriza).

### 3.4 `senior-git`: ramas, commits, PR y autoría

- **Problema:** historiales ilegibles y, sobre todo, Claude figurando como autor en GitHub.
- **Cómo lo ataca**
  - **Autoría (inviolable):** solo el usuario figura. Ningún `Co-Authored-By`, pie «Generated with…» ni colaborador de Claude. La identidad se toma del repositorio o de la sesión de `gh`; si no hay ninguna, se pregunta en nombre de quién se trabaja. Nunca se toca la configuración global de git.
  - **Tres tipos de barrera:** hooks de git (`commit-msg`, `pre-commit`, `pre-push`) que viven en `.git/hooks/` de cada clon; el hook global de Claude (`hook_autoria_claude.py`) que bloquea `git commit`, `git tag` y `gh pr|issue|release|api` con atribuciones; y `verificar.py autoria`.
  - **Una rama por cambio**, nunca directo en `main`; Conventional Commits en español neutro (hasta 72 caracteres); commits atómicos.
  - **Nada de reescribir historia compartida** (`push --force`, `reset --hard`) sin permiso; y **`--no-verify` bloqueado** para Claude (también `commit -n` y `core.hooksPath`).
  - **Commit, push, PR y fusión solo con pedido o aprobación**, por acción: la aprobación de una no se extiende a la siguiente.
  - **Descripción y Topics de GitHub** al día (`repo_meta.py`), con autorización permanente solo para eso; nunca se tocan visibilidad ni otros ajustes.
  - **Plantilla de PR** con «Qué cambia», «Por qué», «Cómo se probó» y «Seguridad», y un tope de unas 30 líneas.
- **Herramientas:** `guardia_autoria.py` (`comprobar`, `mensaje`, `instalar`, `asegurar`, `identidad`), `hook_autoria_claude.py`, `repo_meta.py`, `validar_commits.py`.
- **No hace:** no puede comprobar el idioma de un commit ni impide que el usuario, desde su terminal, se salte los hooks.

### 3.5 `senior-docs`: documentación viva

- **Problema:** documentos que envejecen, se repiten o no se entienden.
- **Cómo lo ataca**
  - **Un dato, un lugar:** regla → requisito, decisión → ADR, estado → `ESTADO.md`, pasos → ficha; el resto enlaza con `[[ID]]`. Lo que desborda su límite se divide o se mueve, **nunca se recorta**.
  - **Siete tipos de requisitos** con prefijo (RN negocio, RU usuario, RD dominio, RF funcional, RNF no funcional, RT transición, RI interfaces externas), un archivo por requisito y ejemplos con valores concretos de los que salen los tests.
  - **Las reglas de negocio nunca se infieren del código:** se preguntan. Cuando no existen requisitos, se elicitan por lotes en un archivo `docs/consultas/NN-tema.md` que el usuario responde cuando puede (con `ok` alcanza).
  - **Diagramas Mermaid con tope de tamaño** (clases hasta 10, secuencia hasta 8 participantes y 20 mensajes, flujo o estados hasta 15 nodos, entidad-relación hasta 10 entidades); si no entra, se divide. Los cambios a diagramas de arquitectura esperan aprobación.
  - **ADR** para decisiones difíciles de revertir.
  - **README con diagramas** copiados desde `docs/diagramas/` entre marcas (un dato, un lugar) y **tarjetas SVG opcionales** (motor neutro: exige pie de foto, sello MEDIDO o ESPERADO en las cifras, contraste y decoración segura; el estilo lo inventa el diseñador).
  - **Trazabilidad:** cada test cita el ID del requisito; el índice arma la matriz requisito → test → código y marca lo que falta.
- **Herramientas:** `iniciar_docs.py`, `consultas.py`, `revisar_requisitos.py`, `readme_diagramas.py`, `readme_tarjetas.py` y, desde `senior`, `diagramas.py` y `texto.py`.
- **No hace:** `revisar_requisitos.py` controla la forma, no si el requisito es correcto ni si hay contradicciones.

### 3.6 `senior-memoria`: que una sesión nueva continúe sin repetir nada

- **Problema:** las conversaciones se pierden; el repositorio no.
- **Cómo lo ataca**
  - **Seis piezas:** `docs/ESTADO.md` (la foto del presente, hasta 60 líneas), fichas de cambio, bandeja de pendientes, deuda técnica (siempre con `motivo:`), ADR e índice con mapa de conceptos.
  - **Protocolo de inicio:** leer el estado, mirar los pasos abiertos de la ficha en curso, consultar el índice en lugar de leer documentos enteros (cada resultado dice cuántos tokens cuesta abrirlo) y resumir en dos o tres líneas dónde quedó el trabajo.
  - **Guardado continuo:** el estado se actualiza en cada hito (test que pasa a verde, commit, paso de la ficha, bloqueo), no al cierre, porque un cierre brusco no ejecuta ningún hook.
  - **Qué entra en el estado:** lo costoso de redescubrir (una decisión y su motivo, un callejón sin salida, el comando exacto que funciona), no lo que se ve en el código.
  - **Fuera de alcance va a la bandeja,** no al olvido ni al arreglo de paso.
  - **Hook de apertura opcional** (`cargar_estado.py`, evento `SessionStart`): se propone y solo se instala con aprobación.
- **Herramientas:** `cargar_estado.py` e `indexar_docs.py` (`indexar`, `consultar`, `vecinos`).
- **No hace:** `verificar.py docs` solo revisa y nunca modifica archivos.

### 3.7 `senior-relevar`: entender un sistema antes de tocarlo

- **Problema:** cambiar lo que no se entiende es la causa más común de roturas.
- **Cómo lo ataca:** de **lo barato a lo caro**. (1) Memoria previa; (2) inventario automático sin tokens (`relevar.py`: lenguajes, manifiestos, tests, integración continua, documentación, historial, archivos grandes y muy modificados, marcas TODO); (3) mapa de conceptos; (4) lectura dirigida solo de lo central, anotando **hipótesis, no verdades**; (5) convenciones del proyecto (se respetan por sobre cualquier preferencia); (6) reglas de negocio por confirmar con el usuario; (7) riesgos; (8) plan de tests de caracterización; (9) entregable `docs/relevamiento.md`.
- **PDF y documentos externos:** los resuelve Token Diet si está instalada; este paquete no trae conversor.
- **No hace:** no propone rediseños (describe, no corrige) y no relee todo el código «para tener el panorama».

### 3.8 `senior-seguridad`: seguridad como lente permanente

- **Problema:** la seguridad dejada para el final.
- **Cómo lo ataca**
  - **Modo liviano por defecto:** una lista de revisión de unas diez preguntas por cambio (entradas, autenticación, secretos, datos, registros, dependencias, entornos), chequeos automáticos sin tokens (`verificar.py seguridad`) y requisitos de seguridad como RNF con etiqueta `iso:`.
  - **Marco:** familia ISO/IEC 27000 (27002:2022, 27005, 27034). Las normas son de pago: se cita número y tema parafraseados, nunca el texto. Los controles de políticas, personas o seguridad física no se resuelven programando y se registran como RNF o RT.
  - **Cinco alertas centrales:** SQL armado con concatenación, datos sin escapar (XSS), secretos que viajan al cliente, acciones sin chequeo de sesión o CSRF y ejecución dinámica sin lista blanca; además de secretos en el código, datos sensibles en logs y dependencias vulnerables (`--auditar`, usa la red).
  - **Modo formal con registro de riesgos:** no se usa por defecto; la skill lo **propone** y el usuario decide (datos personales o sensibles reales, exigencias legales, impacto grave).
- **Herramientas:** `seguridad.py` (vía `verificar.py seguridad`), perfiles de `senior-lenguajes`, plantilla de riesgos.
- **No hace:** las alertas son heurísticas por patrón: se leen como «revisar». Un falso positivo se descarta con `senior-ignore: ID motivo`.

### 3.9 `senior-lenguajes`: perfiles de lenguaje

- **Problema:** soportar un lenguaje nuevo no debería exigir tocar código.
- **Cómo lo ataca:** cada lenguaje es un **archivo de datos** (`perfiles/<lenguaje>.json`) con extensiones, símbolos (expresiones regulares), herramienta de tests, convenciones estándar de la comunidad (nunca estilo personal) y alertas de seguridad con su control ISO. Perfiles incluidos: PHP, JavaScript (con TypeScript), CSS, SQL y HTML.
- **Alta de un lenguaje:** investigar en la documentación oficial, redactar el borrador, probarlo con `probar_perfil.py`, mostrarlo al usuario y **solo con su aprobación** guardarlo (un perfil incorrecto produciría falsas alarmas o ceguera en todos los proyectos).
- **No hace:** nunca guarda un perfil sin aprobación.

### 3.10 `revisar-cambio` (`/revisar-cambio`): revisión rigurosa, solo informa

- **Problema:** revisiones de gusto, sin casos y que se pierden.
- **Cómo lo ataca**
  - **Orden de importancia:** correcto, seguro, aguanta la carga, probado, rápido, sin sobrantes.
  - **Se arma el expediente con script** (archivos tocados, símbolos modificados y quién los usa, tests, documentación, señales de riesgo), después se lee el diff y el código que toca, y se traza el flujo real.
  - **Qué busca:** errores, riesgos de seguridad y de pérdida de datos, escala (condiciones de carrera, una consulta por elemento, O(n²)), tests que faltan, contradicción con requisitos, lentitudes grandes, **sobrante** (código muerto, reusar, estándar, abstracciones de una sola implementación), documentación desactualizada y controles aflojados.
  - **Sin caso concreto no hay hallazgo.** La salida es en lenguaje simple, con hallazgos **numerados de corrido** en tres grupos (corregir antes de subir, conviene corregir, opcional), cada uno con *qué es*, *problema*, *arreglo* y *si se omite*, y cierra con un veredicto.
- **Herramientas:** `contexto.py`, `impacto.py`, `guardia_listones.py`.
- **No hace:** no cambia código; commits y PR siguen necesitando aprobación.

### 3.11 `adoptar-proyecto` (`/adoptar-proyecto`): arranque ordenado

- **Problema:** imponer toda la metodología de golpe.
- **Cómo lo ataca:** (1) plan en solo lectura (`plan_adopcion.py`: si el proyecto es nuevo o existente y qué le falta); (2) el usuario lo aprueba o quita acciones; (3) con aprobación, crea `docs/`, el README desde la plantilla y, si ya existe, el relevamiento; completa el `.gitignore` de secretos y activa los hooks; (4) pregunta **una sola vez** la escala del proyecto (pequeño, mediano o grande); (5) completa a mano lo que el script no puede inferir; (6) propone aparte la guardia de autoría, el hook de apertura y la plantilla de PR.
- **No hace:** nunca pisa archivos existentes y nada se escribe sin aprobación.
- **Costo orientativo:** un proyecto nuevo, unos 2.000 a 4.000 tokens; uno existente, de 10.000 a 50.000.

### 3.12 `inicializar-repositorio` (`/inicializar-repositorio`): de una carpeta a GitHub

- **Problema:** armar a mano identidad, `.gitignore`, hooks, repositorio remoto, descripción, topics y primer push.
- **Cómo lo ataca:** un script hace lo mecánico y el modelo solo redacta la descripción y los topics. Se le da un enlace, `dueño/nombre` o un nombre. **Plan sin escribir** que muestra qué existe y qué **bloquea** (falta la visibilidad, la descripción o los topics; claves a la vista; un `origin` distinto; un remoto con contenido). Con `--aplicar`: identidad local, `git init` en `main`, `.gitignore`, hooks, repositorio remoto, descripción y topics, README (**simple o con tarjetas SVG**, que se pregunta siempre), protección de subida de GitHub en repositorios públicos, commits y push.
- **README con tarjetas:** el diseñador crea **tres estilos** distintos a partir de la descripción, se muestran lado a lado y el usuario elige.
- **No hace:** nunca fuerza un push, no mezcla historias distintas, no pisa una descripción ajena ni sube una carpeta con claves a la vista. No cubre Pull Requests ni cambiar la visibilidad.

### 3.13 `documentar-proyecto` (`/documentar-proyecto`): reconstruir la documentación desde el código

- **Problema:** proyectos existentes sin documentación.
- **Cómo lo ataca:** requiere el proyecto adoptado. Siete etapas: cinco **por script, sin tokens** (`estructura`: módulos, clases y entidad-relación; `interfaces`: rutas HTTP y variables de entorno; `dominio`: una entidad por tabla; `adr`: decisiones visibles en el stack; `reglas`: consulta por lotes con reglas de negocio candidatas) y dos **con el modelo, por módulo y por flujo** (`requisitos` funcionales y `secuencias`), siempre con aprobación y costo declarado.
- **Todo es provisorio y con evidencia** (`archivo:línea` que `documentar.py evidencia` comprueba); un requisito sin evidencia se rechaza. **Las reglas de negocio no se infieren:** van a la consulta y recién confirmadas se convierten en requisito.
- **Heurísticas medidas:** las reglas candidatas tienen precisión de 95 % y recall de 87 % en un corpus de reserva etiquetado; cada candidata muestra su confianza (alta, media o baja).
- **No hace:** no ejecuta nada ni ve código dinámico o rutas generadas; dice lo que no cubre.

### 3.14 `cerrar-sesion` (`/cerrar-sesion`): control de calidad final

- **Problema:** irse sin dejar el estado ni los pendientes al día.
- **Cómo lo ataca:** corre `verificar.py`; actualiza `ESTADO.md` (dónde quedó, próximo paso, bloqueos); confirma el README; actualiza la portada de GitHub si el proyecto cambió; sube la escala si el proyecto creció; avisa de reglas que fallaron dos veces y de bloqueos de hooks que reinciden; menciona pendientes; regenera el índice; **propone** el commit (no lo hace); y cierra con un resumen de cinco líneas.
- **No hace:** es opcional (el estado ya se guarda en cada hito) y no commitea ni empuja sin aprobación.

### 3.15 `senior-diseno`: diseño de interfaces

- **Problema:** interfaces genéricas, saturadas o «hechas por IA».
- **Cómo lo ataca:** dos partes separadas a propósito. **Un método:** briefing y UX; estilo (tarjeta de estilo viva, con tres alternativas A, B y C); **tres alternativas que difieren en estructura** (disposición, jerarquía, navegación, recorrido) en bosquejos HTML desktop y mobile; el usuario da feedback y la elegida evoluciona; revisión final con script y capturas. **Reglas objetivas verificadas por script que no tocan el aspecto:** una familia tipográfica ideal y dos como máximo, etiqueta visible y específica en cada campo, un máximo de cuatro campos visibles y una sola acción principal, contraste y accesibilidad, estados de hover y foco, sistema de diseño sin duplicados.
- **El aspecto es libre:** estilo, paleta, ilustración, movimiento y tono se deciden por proyecto. No hay plantillas con estilo ni límites de expresión.
- **Liviano por defecto:** un trabajo chico lleva tres esqueletos y una sola hoja de notas; uno grande, la ronda completa.
- **Herramientas:** `crear_bosquejos.py`, `tarjeta_estilo.py`, `revisar_diseno.py`, `capturar.py`, `colores.py`, `paquete_interfaz.py`, `importar_preferencias.py`, `htmlmin.py`.
- **No hace:** los bosquejos no llevan tests (el TDD empieza al implementar). Las capturas dependen de que haya un navegador utilizable.

### 3.16 `auditar-diseno` (`/auditar-diseno`)

- **Problema:** un proyecto que no usó `senior-diseno` desde el principio.
- **Cómo lo ataca:** `auditar_proyecto.py` (solo lectura) escribe `docs/diseno/auditoria/AAAA-MM-DD.md` con hallazgos y propuestas **ordenadas por impacto y esfuerzo**; después una lectura de diseño (especificidad, diez heurísticas de 0 a 4, carga cognitiva) que el script no ve. Lo mecánico va a `docs/pendientes.md`; lo que exige decisiones abre una ronda de bosquejos.
- **No hace:** no modifica el proyecto.

### 3.17 `auditar-consumo` (`/auditar-consumo`)

- **Problema:** sesiones que se llenan sin saber por qué.
- **Cómo lo ataca:** `consumo.py` mide, sin gastar tokens del modelo, lo que se paga en cada sesión (descripciones de skills, `CLAUDE.md`, índice de la memoria), lo que se paga al activar una skill y lo que se lee solo si hace falta; propone recortes ordenados por rendimiento. Con `--repo` mide las skills del repositorio en lugar de las instaladas, para ver un recorte antes de reinstalar. Si Token Diet está instalada, su auditoría es la de referencia.
- **No hace:** solo mide y propone; los números son estimaciones (caracteres / 4, margen de ±30 %).

## 4. Los guardias: qué se bloquea solo

Todos son hooks de Claude Code o de git, instalados y verificados por `guardia_autoria.py asegurar` (la primera acción del flujo). Un despachador (`hook_senior.py`) los corre en un solo proceso por llamada (de ~400 ms a ~150 ms).

| Guardia | Qué frena | Cómo responde |
|---|---|---|
| **Autoría** | Commits, tags, PR, issues o releases con `Co-Authored-By`, pies de generación o autores de Claude | Bloquea; no hay vía de autorización |
| **Fuera del proyecto** | Crear o escribir archivos fuera de la raíz del proyecto: `Write`, `Edit`, redirecciones, `mkdir`, `cp`, descargas, código en línea (`python -c`) **y scripts guardados en archivos**, antes de guardarlos y de ejecutarlos | Bloquea, indica la ruta equivalente en `.temporal/` y Claude sigue; el usuario autoriza con `/permitir <ruta>` |
| **Archivos protegidos** | Editar `.env`, claves, certificados, el interior de `.git/` y archivos de bloqueo de dependencias | Bloquea o pregunta, según el modo |
| **Secretos y datos personales** | Escribir claves o datos personales en archivos que van a git, leer `.env`, `git add -f`, claves en mensajes de commit, y **saltear los hooks de git** (`--no-verify`, `commit -n`, `core.hooksPath`) | Bloquea y da la alternativa |
| **Permisos desde el chat** | Un hook de entrada del usuario (`UserPromptSubmit`) que recoge `/permitir`, `/quitar-permiso`, `/hooks-modo`, `/hooks-hermanos` y `/permisos`; Claude no puede usarlo | Configura sin terminal ni reiniciar |
| **Hooks de git** | `commit-msg`, `pre-commit` y `pre-push` en cada clon: autoría y secretos; el `pre-push` revisa **todo el historial que se sube**, commit por commit | Cortan el commit o el push |

**Reglas comunes de diseño**
- **Nunca interrumpen una sesión sin supervisión:** por defecto bloquean y le dicen a Claude qué hacer; lo pendiente va a `docs/pendientes.md`. Un modo opcional (`/hooks-modo preguntar`) vuelve a preguntar en la interfaz.
- **Registro de bloqueos** en `.git/senior-hooks.json` (que git no sube); un bloqueo que se repite tres veces cambia el mensaje y pone la alternativa primero.
- **Un hook que falla no frena nada** (falla hacia abierto), pero con `SENIOR_HOOK_DEPURAR=1` el error se ve.
- **Los proyectos hermanos** (otros repositorios de la misma carpeta) cuentan como «dentro».
- **Alcance honesto:** son una barrera contra descuidos, no contra una evasión deliberada. No ven una ruta armada con código dentro de un script; para eso Claude Code trae `permissions.blockWritesOutsideWorkingDirectories`, que `capas_extra.py` informa sin cambiar nada.

### Secretos: cuatro capas

1. `.gitignore` (el paquete lo completa con `.env`, claves, certificados y bases locales).
2. Hook de Claude antes de escribir.
3. Hooks de git: lo que se commitea y todo lo que se sube.
4. Protección de subida y escaneo de secretos de GitHub (`secretos.py github`, con `--activar`). En un repositorio **privado** GitHub solo la ofrece con un servicio de pago.

Qué detecta `secretos.py`: claves de proveedores conocidos (AWS, GitHub, Anthropic, OpenAI, Stripe, Slack, Google, SendGrid, npm), JWT, claves privadas, direcciones con credenciales, asignaciones literales, tarjetas (con validación Luhn), números de documento, nombres de archivo de secretos y volcados SQL o CSV. Muestra los valores enmascarados.

**`.env`:** se lee o modifica solo con permiso del usuario (`/permitir .env`) y Claude lo propone. Mientras tanto usa `env_gestion.py`: `estructura` muestra los nombres sin los valores y `declarar` agrega variables a `.env.example`. Una clave que ya se subió se rota; borrarla no alcanza.

## 5. `verificar.py`: el verificador de pocas líneas

Sin argumento corre todos los chequeos y devuelve un resumen corto. Se corre antes de cada PR y al cerrar la sesión.

| Chequeo | Qué comprueba |
|---|---|
| `tamano` | Tamaño del cambio y nivel de ceremonia recomendado |
| `alcance` | Archivos tocados que no figuran en el «Alcance» de la ficha |
| `deuda` | TODO, FIXME, HACK y atajos sin disparador; formato de la deuda técnica |
| `estado` | `ESTADO.md` al día, cambios sin guardar, pasos abiertos |
| `escala` | La escala declarada y lo que exige su nivel |
| `evidencia` | Que las citas `archivo:línea` de la documentación inferida existan |
| `docs` | Requisitos sin test e IDs sin documento |
| `requisitos` | Forma de los requisitos: encabezado, IDs, enlaces, ejemplos, palabras ambiguas |
| `readme` | Que exista, esté completo, enlace a `docs/`, se actualice con el cambio y no tenga texto ajeno al proyecto |
| `texto` | Límites de extensión, repeticiones, secciones vacías e información perdida |
| `diagramas` | Legibilidad de los Mermaid y estimación de su ancho al tamaño del README |
| `comentarios` | Calidad de los comentarios del código modificado («solo el porqué») |
| `diseno` | Variables de diseño y etiquetas del contrato de campos (si hay `docs/diseno/`) |
| `listones` | Que el cambio no afloje un umbral, saltee o borre un test ni silencie un chequeo para pasar |
| `autoria` | Que en los commits nuevos solo figure el usuario |
| `seguridad` | Alertas por lenguaje, secretos y logs sensibles (con `--auditar`, dependencias) |
| `secretos` | Claves y datos personales en lo versionado |
| `tarjetas` | Tarjetas SVG al día respecto de sus JSON (solo si el proyecto las usa) |
| `peso` | Topes de peso de las skills (solo en un paquete de skills) |

## 6. Qué está medido y qué no

Medido con agentes reales (Claude Code, tres tareas de código chicas en Python, tres repeticiones, pruebas ocultas para el éxito):

| Rama | Éxito | Tests agregados | Documentación tocada | Costo estimado (9 corridas) |
|---|---|---|---|---|
| Sin skills | 9 de 9 | 6 de 9 | 3 de 9 | 0,69 USD |
| `senior` completo | 9 de 9 | 9 de 9 | 6 de 9 | 1,31 USD |
| `senior` con núcleo corto | 9 de 9 | 9 de 9 | 6 de 9 | 1,26 USD |

- En dos revisiones a ciegas del usuario, la versión con `senior` ganó **6 de 6 pedidos**.
- Achicar el cuerpo de la skill de ~4.800 a ~800 tokens ahorró solo ~4 %: lo que cuesta son las **vueltas** del método (tests, documentación), no el tamaño del texto.
- Las heurísticas de reglas candidatas: precisión de 71 % a 95 % en un corpus de reserva (recall de 87 %).

Sin medir todavía: el efecto en tareas medianas o grandes, con otros modelos o en otros lenguajes; y varias mecánicas de ahorro (inventario, duplicados, índice, nota de continuidad, ceremonia), que dependen de la medición de Token Diet. Los puntos abiertos y su estado: [`revision-completa.md`](revision-completa.md).

## 7. Qué NO hace el paquete

- No programa solo ni decide arquitectura, reglas de negocio o cambios de riesgo: **propone y espera el visto bueno**.
- No sube nada a GitHub sin que el usuario lo pida o lo apruebe, y nunca con Claude como autor.
- No garantiza seguridad: las alertas son heurísticas y los guardias, barreras contra descuidos.
- No infiere reglas de negocio mirando el código.
- No cubre otros sistemas operativos que Windows (decisión del usuario).
- No instala nada por su cuenta: ni dependencias, ni hooks, salvo la guardia de autoría, que el usuario autorizó de forma permanente.
