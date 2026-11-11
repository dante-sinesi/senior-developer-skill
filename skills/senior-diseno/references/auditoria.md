# Auditoría de un proyecto existente

Para un proyecto que **no usó** la skill desde el principio. El comando `/auditar-diseno` (skill `auditar-diseno`) ejecuta `scripts/auditar_proyecto.py`.

## Qué hace

1. Busca los archivos de interfaz: HTML y CSS, y de forma aproximada plantillas PHP, Vue, Svelte, JSX y TSX. Ignora `docs/diseno/`, `docs/`, `node_modules`, `vendor`, `dist` y `build`.
2. Aplica todos los chequeos de `revisar_diseno.py`: base técnica, tipografía (una familia ideal, dos como máximo), saturación, interacción, etiquetas, contraste y sistema de diseño.
3. Escribe `docs/diseno/auditoria/AAAA-MM-DD.md` con un resumen, los hallazgos principales y **propuestas ordenadas por impacto y esfuerzo**.
4. **No modifica nada del proyecto.**

## Cómo leer el informe

- **FALLA:** incumple una política estricta (por ejemplo, un campo sin etiqueta o un contraste bajo). **AVISO:** conviene revisarlo.
- Las propuestas van de lo que más rinde por menos esfuerzo (etiquetas y contraste) a lo más estructural (sistema de diseño).
- Es heurístico: marca qué mirar, no dicta el diseño. Lo subjetivo (identidad, tono, jerarquía) se conversa con el usuario.

## Después de la auditoría

1. Presentar el informe y priorizar con el usuario.
2. Para lo que requiere decisiones de diseño, abrir una ronda (`crear_bosquejos.py`) con la dirección actual como punto de partida y dos alternativas.
3. Los cambios en el código se hacen después, con las reglas de `senior` (tests primero, rama y commits ordenados), y solo con la aprobación del usuario.

## Límites

- Una plantilla con mucha lógica (JSX o Vue complejo) se lee de forma aproximada; si el proyecto corre, conviene revisar la página renderizada, por ejemplo abriéndola en un navegador, y pasar ese HTML por `revisar_diseno.py`.
- Las páginas que se arman por completo con JavaScript no se ven en el código estático.
