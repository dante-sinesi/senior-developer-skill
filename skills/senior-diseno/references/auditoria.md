# Auditoría de un proyecto existente

Para un proyecto que **no usó** la skill desde el principio. El comando `/auditar-diseno` (skill `auditar-diseno`) ejecuta `scripts/auditar_proyecto.py`.

## Qué hace

1. Busca los archivos de interfaz: HTML y CSS, y de forma aproximada plantillas PHP, Vue, Svelte, JSX y TSX. Ignora `docs/diseno/`, `docs/`, `node_modules`, `vendor`, `dist` y `build`.
2. Aplica todos los chequeos de `revisar_diseno.py`: base técnica, tipografía (una familia ideal, dos como máximo), saturación, interacción, estados y contenido real, etiquetas, contraste y sistema de diseño.
3. Escribe `docs/diseno/auditoria/AAAA-MM-DD.md` con un resumen, los hallazgos principales y **propuestas ordenadas por impacto y esfuerzo**.
4. **No modifica nada del proyecto.**

## Cómo leer el informe

- **FALLA:** incumple una política estricta (por ejemplo, un campo sin etiqueta o un contraste bajo). **AVISO:** conviene revisarlo.
- Las propuestas van de lo que más rinde por menos esfuerzo (etiquetas y contraste) a lo más estructural (sistema de diseño).
- Es heurístico: marca qué mirar, no dicta el diseño. Lo subjetivo (identidad, tono, jerarquía) se conversa con el usuario.

## Lectura de diseño (la parte que el script no hace)

Después de leer el informe, quien audita agrega al **mismo archivo** una sección `## Lectura de diseño`, a partir de la página renderizada (capturas de desktop y mobile) y no solo del código. Cuatro partes, cortas:

1. **Especificidad.** Una pregunta con respuesta en una o dos oraciones: *¿otro producto podría usar este diseño sin cambiarle nada?* Si sí, decir qué lo vuelve genérico (la composición, la voz, las imágenes) y qué lo haría propio. Se juzga antes de mirar los avisos del script, para que no sesguen.
2. **Las diez heurísticas** de `ux.md` (sección 7), cada una con puntaje de 0 (grave) a 4 (sin problemas) y una frase de evidencia. Se marca `n/a` la que no aplica; no se fuerza un número.
3. **Carga cognitiva.** Decisiones con más de cuatro opciones visibles a la vez, pasos que piden recordar algo de la pantalla anterior, y términos que la persona no usaría.
4. **Tres fortalezas y de tres a cinco problemas prioritarios**, cada problema con su caso concreto («quien llega desde el celular ve…»). Sin gustos de estilo: el aspecto artístico no se califica.

Es una lectura, no una regla: ningún puntaje bloquea nada y el usuario decide qué se cambia.

## Después de la auditoría

1. Presentar el informe y priorizar con el usuario.
2. Para lo que requiere decisiones de diseño, abrir una ronda (`crear_bosquejos.py`) con la dirección actual como punto de partida y dos alternativas.
3. Los cambios en el código se hacen después, con las reglas de `senior` (tests primero, rama y commits ordenados), y solo con la aprobación del usuario.

## Límites

- Una plantilla con mucha lógica (JSX o Vue complejo) se lee de forma aproximada; si el proyecto corre, conviene revisar la página renderizada, por ejemplo abriéndola en un navegador, y pasar ese HTML por `revisar_diseno.py`.
- Las páginas que se arman por completo con JavaScript no se ven en el código estático.
