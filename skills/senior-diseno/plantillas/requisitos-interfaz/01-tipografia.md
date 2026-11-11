---
id: {{id}}
tipo: no-funcional
titulo: Una familia tipográfica, dos como máximo en toda la web
resumen: Toda la web usa una familia tipográfica; dos como máximo; más solo si el arte lo requiere, con excepción escrita.
tags: [interfaz, tipografia]
paquete: interfaz
clave: tipografia
verificado_por: senior-diseno/scripts/revisar_diseno.py tipografia
---

# {{id}}: Una familia tipográfica, dos como máximo en toda la web

## Descripción

La interfaz usa una familia tipográfica en todo el sitio. Se admite una segunda. Una tercera solo si la dirección artística la requiere, y queda justificada por escrito en el archivo con `<!-- excepcion-tipografia: motivo -->`.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| 1 familia en varios pesos | Cumple |
| 2 familias (títulos y texto) | Cumple |
| 3 familias sin excepción escrita | No cumple |
| 3 familias con excepción escrita | Cumple y se informa como excepción |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `tipografia-y-color.md`.

## Estado

provisorio
