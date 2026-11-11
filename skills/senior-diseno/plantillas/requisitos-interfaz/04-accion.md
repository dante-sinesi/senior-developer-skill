---
id: {{id}}
tipo: no-funcional
titulo: Una sola acción principal por pantalla
resumen: Cada pantalla tiene 1 acción principal y no más de 5 acciones visibles.
tags: [interfaz, no-saturacion]
paquete: interfaz
clave: accion
verificado_por: senior-diseno/scripts/revisar_diseno.py saturacion
---

# {{id}}: Una sola acción principal por pantalla

## Descripción

Cada pantalla tiene una única acción principal, claramente dominante, y no más de 5 acciones visibles. Las acciones llevan texto con verbo y objeto, nunca solo un ícono.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| 1 principal y 2 secundarias | Cumple |
| 2 acciones principales | No cumple |
| 6 acciones visibles | No cumple (máximo 5) |
| Botón «Guardar pedido» | Cumple |
| Botón con solo un ícono | No cumple |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `no-saturacion.md`.

## Estado

provisorio
