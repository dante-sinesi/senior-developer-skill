---
id: {{id}}
tipo: no-funcional
titulo: Navegación principal corta
resumen: La navegación principal tiene hasta 7 destinos en escritorio y 5 en mobile.
tags: [interfaz, no-saturacion]
paquete: interfaz
clave: navegacion
verificado_por: senior-diseno/scripts/revisar_diseno.py saturacion
---

# {{id}}: Navegación principal corta

## Descripción

La navegación principal ofrece hasta 7 destinos en escritorio y hasta 5 en mobile. Lo que no entra se agrupa o se mueve a una sección secundaria.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| 7 destinos en escritorio | Cumple |
| 8 destinos en escritorio | No cumple |
| 5 destinos en mobile | Cumple |
| 6 destinos en mobile | Aviso: reducir para mobile |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `no-saturacion.md`.

## Estado

provisorio
