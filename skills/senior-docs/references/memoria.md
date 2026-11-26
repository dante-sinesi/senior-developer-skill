# Memoria del proyecto

Las conversaciones se pierden; el repositorio no. Todo lo que una sesión futura necesite para continuar vive en `docs/`. El diseño busca tres cosas: no perder el contexto entre sesiones, no perder lo que se nota de pasada, y no perder lo que quedó a medias.

## Piezas

| Pieza | Archivo | Para qué |
|---|---|---|
| Estado | `docs/ESTADO.md` | Dónde estamos, próximo paso, bloqueos. Corto. |
| Ficha de cambio | `docs/cambios/AAAA-MM-DD-nombre.md` | Un cambio mediano o grande con alcance y pasos con casillas. |
| Bandeja de pendientes | `docs/pendientes.md` | Lo notado fuera de alcance. |
| Deuda técnica | `docs/deuda-tecnica.md` | Decisiones pospuestas, siempre con `motivo:`. |
| Decisiones | `docs/decisiones/ADR-000.md` | El porqué de decisiones importantes (ver `SKILL.md`). |
| Índice y mapa | `docs/INDEX.md`, `docs/.grafo.json` | Navegar sin leer todo. Se regeneran con el script. |

Las plantillas están en `../plantillas/`. Si el proyecto no tiene `docs/`, se crea con `scripts/iniciar_docs.py` (nunca pisa archivos existentes).

## Protocolo de inicio de sesión

1. Leer `docs/ESTADO.md`. Con el recordatorio registrado, ya llegó como contexto.
2. Si hay una ficha "en curso", leer solo sus pasos abiertos.
3. Para ubicar un concepto, **no leer documentos completos**: consultar el mapa. Cada resultado indica los tokens aproximados de abrirlo: lo chico se lee entero, lo grande por partes.
   ```
   python <esta-skill>/scripts/indexar_docs.py consultar <término>
   python <esta-skill>/scripts/indexar_docs.py vecinos <id>
   ```
4. Resumir al usuario en dos o tres líneas dónde se quedó y proponer el siguiente paso.

## Guardado continuo (cada hito, no al final)

Un cierre brusco (Alt+F4, apagón) no ejecuta ningún hook, así que el estado no puede depender del cierre. Actualizar `ESTADO.md` y la ficha cuando:
- un test pasa de rojo a verde,
- se hace un commit,
- se marca un paso de la ficha,
- aparece un bloqueo o una pregunta para el usuario.

Cada actualización es breve (una o dos líneas); no se reescribe el documento.

## Qué entra en el estado: lo costoso de redescubrir

En `ESTADO.md` y en las fichas va lo que costaría volver a averiguar (una decisión y su motivo, un callejón sin salida ya recorrido, el comando exacto que funciona), no lo que se ve en el código o en el historial de git. Un estado corto se lee en cada sesión; uno largo se paga siempre.

## Fuera de alcance: a la bandeja, no al olvido

Si se nota una duplicación, un bug o una mejora mientras se trabaja en otra cosa, se anota en `docs/pendientes.md` con fecha y lugar. No se arregla de paso (minimalismo) y tampoco se pierde. Al cerrar, mencionarlo al usuario.

## Cuando ESTADO.md crece

`ESTADO.md` es una foto del presente (máximo 60 líneas), no un diario. Lo que envejece sale sin perderse: los cambios chicos antiguos y los bloqueos resueltos pasan a `docs/historial/AAAA-MM.md`, las decisiones a un ADR y el detalle del trabajo en curso a su ficha. En `ESTADO.md` queda solo un enlace. Al cerrar una ficha, se archiva en `docs/historial/` con un resumen de tres líneas. `verificar.py texto` avisa si algo se perdió.

## Fichas escalonadas

- Cambio trivial o chico: una línea en la sección "Cambios chicos recientes" de `ESTADO.md`.
- Cambio mediano o grande: ficha propia con `## Alcance` y pasos. La ficha pasa a `Estado: terminado` al cerrarse.

## Índice y mapa de conceptos

`scripts/indexar_docs.py` (solo biblioteca estándar):
- `indexar`: genera `docs/INDEX.md` y `docs/.grafo.json`. Une documentos, requisitos (RN-001, RF-012…), tests y código por enlaces `[[id]]` y por IDs citados en el código; suma clases, funciones y tablas detectadas con los perfiles de `senior-lenguajes`. Marca requisitos sin test e IDs usados sin documento.
- `consultar <término>` y `vecinos <id>`: navegan el mapa sin leer todo.

Regenerar el índice con `indexar` después de tocar documentación; `verificar.py docs` solo lo revisa y nunca modifica archivos. `docs/INDEX.md` se versiona junto con el cambio (su salida no tiene fechas, así que no ensucia el historial); `docs/.grafo.json` es regenerable y `iniciar_docs.py` lo deja ignorado en `docs/.gitignore`.

## Recordatorio al abrir y al compactar

`scripts/cargar_estado.py --hook` es un hook `SessionStart` que registra el instalador (`guardia_autoria.py asegurar`): al abrir, retomar, limpiar y compactar una sesión entran como contexto la escala, el estado (recortado si es largo, hasta unas 600 palabras en total), los documentos que hay y cuántos commits de código pasaron desde el último cambio en la documentación. Fuera de un proyecto con `docs/ESTADO.md` no hace nada. Busca el proyecto desde la carpeta de la sesión hacia arriba: una sesión abierta por encima del proyecto no lo recibe.

## Cierre ordenado

El comando `/cerrar-sesion` (skill `cerrar-sesion`) hace el cierre completo, pero es opcional: el guardado continuo ya protege lo esencial.
