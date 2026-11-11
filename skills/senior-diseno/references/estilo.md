# La tarjeta de estilo

La definición gráfica del proyecto, antes de diseñar pantallas. Separa dos decisiones que de otro modo se mezclan: **cómo se ve** el proyecto (su carácter) y **cómo se organiza** (la estructura de las pantallas). Primero se decide la primera, con ambición y sin tener que resolver pantallas al mismo tiempo; después las tres alternativas de estructura se diseñan ya con ese estilo y difieren solo en estructura.

## Contenido
1. Qué es y qué no es
2. Cuándo se hace
3. El proceso: A, B y C, con ajuste
4. Qué muestra
5. Cómo se mantiene viva
6. Fuera de la web

## 1. Qué es y qué no es

- **Es la primera porción del sistema de diseño**, no un documento aparte. Usa las variables reales de `docs/diseno/sistema/tokens.css` y los componentes del inventario, así que hay un solo lugar donde cambiar cada cosa. Si cambia un color, cambia la tarjeta.
- **Es una página que se mira**, no una especificación que se lee: colores, tipografía y piezas en todos sus estados, hechos con el propio estilo.
- **No es una plantilla de aspecto.** La plantilla (`plantillas/estilo.html`) no trae ningún estilo, ni secciones, ni disposición: cada tarjeta se diseña con el estilo que muestra. Solo trae las marcas que permiten mantenerla al día.
- **No es un catálogo completo por adelantado.** Los componentes salen de las pantallas, así que arranca con las piezas firma y crece a medida que las pantallas piden componentes nuevos.

## 2. Cuándo se hace

Según la escala del proyecto (`senior/scripts/escala.py`):
- **Pequeño:** no hace falta; alcanza con la hoja de notas de la ronda.
- **Mediano:** recomendada, si el proyecto tiene interfaz.
- **Grande:** obligatoria si hay interfaz, y siempre al día.

Siempre se puede pedir en un proyecto chico si el usuario quiere explorar el estilo por separado.

## 3. El proceso: A, B y C, con ajuste

1. **Insumos.** El briefing y el tono (`briefing.md`), las referencias del usuario y las preferencias (`notas/preferencias.md`). Si hay imágenes, se leen reducidas y se extraen principios, no se copian.
2. **Tres estilos.** `python scripts/tarjeta_estilo.py nueva --nombre <proyecto>` crea `docs/diseno/estilo/AAAA-MM-DD-<proyecto>/estilo-a.html`, `-b` y `-c`. Los tres proponen estilos distintos, cada uno con la ambición que merezca (ilustración, imágenes, íconos, tipografía de carácter, movimiento con propósito). La divergencia es de **carácter**, no de matiz: tres variaciones del mismo gris no exploran nada. Cada uno lleva su carta en un `<aside class="nota">`: idea, referencias, qué evita, qué riesgo asume.
3. **Revisión previa.** `python scripts/tarjeta_estilo.py revisar estilo-a.html` comprueba que defina variables y muestre piezas firma con sus estados; `revisar_diseno.py todo <archivos> --capturas` pasa las reglas objetivas y deja capturas de desktop y mobile, que se miran.
4. **Feedback del usuario**, como en el resto del método: «me gustó la B», «la paleta de la A con la tipografía de la B», «otras tres, más sobrias». Cada ajuste va en una versión nueva (`crear_bosquejos.py --evolucionar estilo-b.html`), sin pisar la anterior. **No se avanza sin su feedback.**
5. **Elección.** `python scripts/tarjeta_estilo.py elegir estilo-b-v2.html` convierte la elegida en la tarjeta viva `docs/diseno/estilo/tarjeta.html`: sus variables pasan a `sistema/tokens.css`, sus piezas al inventario de componentes y la decisión a `notas/decisiones.md`. Si `tokens.css` ya tenía variables propias, pide `--pisar`.
6. **Las estructuras.** Con la tarjeta creada, `crear_bosquejos.py` enlaza `tokens.css` en las tres direcciones y avisa que solo cambian la estructura.

## 4. Qué muestra

Lo que define el carácter del proyecto, en el orden y con la forma que el estilo pida:
- la **paleta** con su porqué, y la **tipografía** (cada variable `--c-…` y `--f-…` de `tokens.css` se nombra en algún lugar de la tarjeta);
- el **tono**, la textura o imaginería y el **movimiento**, si los tiene;
- unas pocas **piezas firma** (por ejemplo el botón principal y un campo) en **todos sus estados**: reposo, hover, foco, presionado, deshabilitado, cargando, error. Los estados se muestran lado a lado, no se imaginan;
- lo que el estilo evita, en la carta.

La tarjeta es un **catálogo de componentes en todos sus estados**, no una pantalla: `revisar_diseno.py` no le aplica la no saturación (cantidad de acciones, de campos y acción principal única), que mide lo que una persona decide a la vez, pero sí el contraste, las etiquetas, los estados, la tipografía y el sistema. Todo lo que está dentro del elemento con `data-tarjeta` queda fuera de ese chequeo.

Cada pieza se marca con `data-componente="Nombre"` (el mismo nombre que en el inventario) y cada variante y estado con `data-variante="…"` y `data-estado="…"`. Son marcas, no estilo: permiten comprobar la tarjeta sin leerla.

## 5. Cómo se mantiene viva

Regla: **cada vez que se agrega un componente, se actualiza la tarjeta, en el mismo cambio.**

1. Antes de diseñar algo, se busca en el inventario (`sistema-de-diseno.md`): si sirve uno existente o una variante, no hay componente nuevo.
2. Si es otra cosa, `python scripts/tarjeta_estilo.py componente "Nombre" --variantes a,b --estados x,y --motivo "por qué no servía ninguno"` lo registra en el inventario y deja en la tarjeta un hueco marcado `completar`.
3. Se diseña el componente en la tarjeta, con el estilo del proyecto, mostrando cada variante y cada estado, y se borran las marcas `completar`.
4. `tarjeta_estilo.py estado` (que corre también `verificar.py diseno`) falla mientras la tarjeta no muestre un componente, una variante o un estado del inventario, una variable de color o de tipografía, o tenga huecos sin completar.

Lo mismo vale al agregar una variable: cada variable de color o de tipografía nueva aparece en la tarjeta.

## 6. Fuera de la web

Para un juego o un programa que no es una página, la tarjeta es **una muestra dentro del propio programa**: una escena, una pantalla o una ventana que muestra únicamente lo propio del estilo, con los recursos reales del proyecto (el tema, la hoja de estilo, las fuentes, la paleta) para que siga habiendo un solo lugar donde cambiar cada cosa.
- En Godot, por ejemplo, una escena de muestra que usa el recurso `Theme` del proyecto y enseña colores, fuentes y los controles firma en todos sus estados.
- Las tres alternativas son tres muestras (o tres temas sobre la misma muestra); el usuario elige y se ajusta con su feedback.
- Se registra con `python scripts/tarjeta_estilo.py no-web --plataforma <nombre> --artefacto <ruta> --recurso <ruta>`, que crea `docs/diseno/estilo/tarjeta.md` con una tabla de componentes y dónde se muestra cada uno. `tarjeta_estilo.py estado` comprueba que todo componente del inventario esté en esa tabla.

**Límite honesto:** el paquete no puede construir ni ejecutar el motor, así que la muestra de un programa no se genera ni se verifica por script: la construye quien implementa, y el usuario la mira. Lo que el script sí comprueba es la tabla.
