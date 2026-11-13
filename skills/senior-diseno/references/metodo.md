# El método de trabajo

Cómo se trabaja con el usuario. El método es fijo; **el aspecto de lo que se diseña es libre**.

## Contenido
1. Los pasos
2. Qué se entrega en cada paso
3. Tres alternativas que difieren en estructura
4. El feedback y cómo se evoluciona
5. La revisión final: reglas y render
6. Interfaces de juego y de aplicación
7. Ejemplo

## 1. Los pasos

| Paso | Qué se hace | Quién decide |
|---|---|---|
| 0 | Leer `docs/diseno/notas/preferencias.md` (no volver a proponer lo rechazado) | — |
| 1 | **Briefing**: para quién, qué tarea, qué tono, qué referencias | usuario |
| 2 | **UX**: tareas, flujo, jerarquía, desktop y mobile; **inventario de campos** de cada formulario | diseño, con el usuario |
| 2b | **Estilo** (medianos y grandes con interfaz): tres tarjetas de estilo A, B y C, feedback y ajuste; la elegida queda como tarjeta viva (`estilo.md`) | diseño y usuario |
| 3 | **Tres alternativas** que difieren en estructura | diseño |
| 4 | **Feedback**: qué le gustó, qué cambiar; pide otras tres o ya una | usuario |
| 5 | **Evolución o corrección** de la elegida, en una versión nueva | diseño |
| 6 | **Revisión final**: reglas con script y mirada al render | diseño |
| 7 | **Cierre**: decisiones y preferencias al día; luego, si el usuario aprueba, se implementa con las reglas de `senior` | diseño y usuario |

Los pasos 4 y 5 se repiten tantas veces como haga falta. **Nunca se avanza sin feedback** del usuario entre la primera entrega y las siguientes.

## 2. Qué se entrega en cada paso

- **Paso 2b:** tres archivos `estilo-a.html`, `-b` y `-c` en `docs/diseno/estilo/` (`scripts/tarjeta_estilo.py nueva`) y, al elegir, la tarjeta viva `estilo/tarjeta.html` con sus variables en `sistema/tokens.css`. Con la tarjeta creada, las tres direcciones del paso 3 usan ese estilo y difieren solo en estructura. Detalle en `estilo.md`.
- **Pasos 1 y 2:** en un trabajo chico, la hoja `NOTAS.md` de la ronda (briefing mínimo, campos, supuestos, decisiones, preguntas); en uno grande, `--completo` agrega `briefing.md` e `inventario-campos.md` (`plantillas/`). Lo supuesto va marcado como provisorio. No se hacen preguntas innecesarias: se asume lo razonable y se anota.
- **Paso 3:** tres archivos HTML, uno por alternativa, creados con `scripts/crear_bosquejos.py`. Cada uno trae solo la barra para ver desktop, mobile o ambas, y **ningún estilo**: se diseña con el aspecto que cada alternativa merezca.
- **Paso 5:** una versión nueva del archivo elegido (`direccion-b-v2.html`, creada con `crear_bosquejos.py --evolucionar`), sin pisar la anterior.
- **Paso 7:** en un trabajo chico, un resumen corto en el chat (archivos, supuestos, qué falta) y las notas al día; en uno grande, `docs/diseno/notas/decisiones.md` con las decisiones (D-001…) y las preferencias actualizadas.

## 3. Tres alternativas que difieren en estructura

La divergencia es de **estructura**: cómo se dispone el contenido, qué jerarquía tiene, cómo se navega, cuál es el recorrido. Tres alternativas que solo cambian de color no exploran nada. Ver `direcciones.md`.

**El estilo no se prescribe.** No hay que hacer la alternativa "neutra" ni "sin arte", ni hay que hacerla "artística" con una receta. Cada alternativa tiene el aspecto que el diseño crea más fuerte para esa estructura, con la ambición que el proyecto pida: ilustración, imágenes, íconos, tipografía de carácter, movimiento con propósito. Lo único que se pide es lo objetivo de `SKILL.md` (por ejemplo, una familia tipográfica ideal y dos como máximo).

## 4. El feedback y cómo se evoluciona

El usuario responde de formas como:
- "Me gustó la B": se evoluciona la B.
- "El menú de la A con la distribución de la B": se combinan bloques (`data-bloque`, mismos nombres en las tres).
- "Pasame otras tres, más densas": se hace una ronda nueva.
- "Ya con el estilo del proyecto y estos ajustes": una sola alternativa, evolucionada.

Cada cambio se hace en una versión nueva (`-v2`, `-v3`), se anota la decisión con su ID y se actualizan las preferencias (qué aprobó, qué rechazó y por qué).

## 5. La revisión final: reglas y render

Antes de entregar cualquier versión:

1. **Reglas y capturas en un solo paso:** `python scripts/revisar_diseno.py todo <archivos> --capturas`. Sin FALLA, o con excepciones justificadas por escrito.
2. **Corregir con el cambio mínimo.** Si falta una etiqueta, se agrega la etiqueta; si el contraste de un botón es bajo, se ajusta ese par de colores. **No se rediseña para pasar un chequeo.** Si la regla choca con una idea artística fuerte, se justifica la excepción.
3. **Mirar el render:** leer las capturas de desktop y mobile que dejó el paso anterior (o `python scripts/capturar.py <archivo>`). Revisar que nada se rompa (desbordes, texto cortado, imágenes que no cargan, encoding). Si no hay navegador disponible, **decirlo** en la entrega: "no se vio renderizado".

## 6. Interfaces de juego y de aplicación

El método es el mismo.
- **Juego:** la superficie de juego (tablero, mesa, mapa) suele ocupar la mayor parte de la pantalla. La información útil a la vez puede ser mayor que en un sitio, con jerarquía fuerte; la no saturación sigue valiendo para las **acciones que se deciden a la vez**. Si un límite se supera con motivo, se justifica con `<!-- excepcion-saturacion: … -->`.
- **Aplicación de trabajo:** prima la densidad útil, los estados y la consistencia; ver `ux.md`.

## 7. Ejemplo

Pedido: "una pantalla de juego, tres alternativas."
1. Tres estructuras: tablero a pantalla completa con panel lateral; tablero arriba y mano de recursos abajo; tablero central con paneles flotantes retráctiles. Cada una con el aspecto que su idea pide.
2. Feedback: "Me gustó la B, con los recursos más grandes y la acción principal siempre a mano."
3. Se crea `direccion-b-v2.html` con esos cambios, se pasan las reglas, se capturan desktop y mobile y se entrega.
