---
id: {{id}}
tipo: no-funcional
titulo: Contraste de color mínimo
resumen: El texto normal tiene un contraste de al menos 4,5 a 1 y el texto grande y los componentes, de 3 a 1.
tags: [interfaz, accesibilidad]
paquete: interfaz
clave: contraste
verificado_por: senior-diseno/scripts/revisar_diseno.py contraste
---

# {{id}}: Contraste de color mínimo

## Descripción

El texto normal tiene un contraste mínimo de 4,5 a 1 contra su fondo. El texto grande (desde 24 px, o 18,66 px en negrita) y los componentes de interfaz, de 3 a 1. Nada depende solo del color: los estados también se indican con texto o ícono.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| Texto #767676 sobre #ffffff (4,54 a 1) | Cumple |
| Texto #999999 sobre #ffffff (2,85 a 1) | No cumple |
| Titular de 32 px con 3,2 a 1 | Cumple |
| Error indicado solo con color rojo | No cumple |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `tipografia-y-color.md`.

## Estado

provisorio
