---
id: {{id}}
tipo: no-funcional
titulo: Los elementos interactivos responden a hover, foco y presionado
resumen: Botones, enlaces y campos muestran hover, foco visible y presionado, con transiciones de 500 ms o menos.
tags: [interfaz, accesibilidad, reactividad]
paquete: interfaz
clave: estados
verificado_por: senior-diseno/scripts/revisar_diseno.py interaccion
---

# {{id}}: Los elementos interactivos responden a hover, foco y presionado

## Descripción

Todo elemento interactivo muestra un estado de hover, un foco visible (`:focus-visible`) y un estado presionado. Las transiciones duran 500 ms o menos y listan las propiedades que cambian.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| Botón con hover, foco visible y presionado | Cumple |
| Botón sin foco visible | No cumple |
| Transición de 300 ms | Cumple |
| Transición de 900 ms | Aviso: se siente lenta |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `reactividad.md`.

## Estado

provisorio
