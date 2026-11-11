---
id: {{id}}
tipo: no-funcional
titulo: Se respeta la preferencia de movimiento reducido
resumen: Con `prefers-reduced-motion` activo, el movimiento se apaga: al menos 1 regla lo contempla.
tags: [interfaz, accesibilidad]
paquete: interfaz
clave: movimiento
verificado_por: senior-diseno/scripts/revisar_diseno.py interaccion
---

# {{id}}: Se respeta la preferencia de movimiento reducido

## Descripción

Cuando la persona pide movimiento reducido, las animaciones y transiciones se desactivan o se reducen a lo mínimo. Hay al menos 1 regla `prefers-reduced-motion` en toda interfaz con movimiento.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| Animación con regla de movimiento reducido | Cumple |
| Animación infinita sin esa regla | No cumple |
| Interfaz sin movimiento | Cumple |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `reactividad.md`.

## Estado

provisorio
