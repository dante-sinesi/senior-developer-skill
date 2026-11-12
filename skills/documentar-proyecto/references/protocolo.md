# Protocolo de las etapas con el modelo

Cómo se escriben los requisitos funcionales y los diagramas de secuencia de un proyecto existente sin inventar nada.

## Requisitos funcionales (RF) por módulo

1. **Elegir el módulo** de `documentar.py progreso` (primero los más grandes y los más centrales en `docs/diagramas/modulos.md`).
2. **Leer con foco**, no todo: los puntos de entrada del módulo, sus clases públicas y los archivos que el índice (`indexar_docs.py consultar`) o el relevamiento marcan como centrales. Ver `senior/references/tokens.md` para leer por partes.
3. **Escribir de 3 a 8 RF por módulo**, uno por cosa que el módulo hace para quien lo usa, con `documentar.py requisito --tipo RF --modulo <módulo> --titulo "…" --descripcion "…" --evidencia archivo:línea`. Cada uno:
   - **Un verbo y un objeto** en el título («Facturar un pedido», no «Facturación»).
   - **Descripción en una o dos oraciones**, con «debe» o en presente («El sistema calcula…»), sobre lo que el código hace, sin decir por qué.
   - **Evidencia real**: la línea donde está la parte principal. El script rechaza archivos o líneas que no existen.
   - Sin palabras vagas («rápido», «adecuado», «etc.»), sin porcentajes ni plazos que el código no muestre.
4. **No documentar:** código muerto, detalles de implementación (cómo se llama una variable), ni reglas de negocio. Si se ve una regla (un umbral, un descuento, un permiso), se anota para el próximo lote de la consulta de reglas y no se convierte en RF ni en RN.
5. **Cuando un módulo se cierra**, anotar en `docs/ESTADO.md` cuáles módulos faltan y seguir con el siguiente solo si el usuario lo aprueba.

## Diagramas de secuencia

1. `documentar.py secuencias` lista puntos de entrada (rutas y programas de consola), los de código más grande primero.
2. Elegir **cuatro o cinco** que representen lo más importante del sistema; no uno por ruta.
3. Leer la cadena de llamadas de cada uno (controlador, servicios, acceso a datos) y escribir un `sequenceDiagram` en `.temporal/secuencia.mmd` con **hasta 8 participantes y 20 mensajes**, nombres cortos y una nota `Note over` solo donde ayude.
4. Guardarlo con `documentar.py secuencia --titulo "…" --pregunta "¿Qué pasa cuando…?" --archivo .temporal/secuencia.mmd --evidencia archivo:línea` (una o varias evidencias). Si no es legible, el script lo rechaza: se divide en dos diagramas.
5. Un diagrama de secuencia describe lo que el código hace; si el flujo no está claro en el código (llamadas dinámicas, eventos), se escribe lo que se ve y se aclara en la pregunta qué parte no se pudo seguir.

## De provisorio a vigente

Un requisito pasa a `vigente` solo cuando el usuario lo confirma. Al confirmarlo se completan sus ejemplos verificables (entrada → resultado) y el origen pasa a «lo confirmó el usuario»; los tests salen de esos ejemplos (`senior-tdd`). Mientras sea provisorio no cuenta como pendiente en la trazabilidad y no exige ejemplos, pero tampoco respalda ningún test.
