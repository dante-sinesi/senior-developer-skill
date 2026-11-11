---
id: {{id}}
tipo: no-funcional
titulo: La interfaz se adapta a mobile
resumen: La interfaz declara el viewport y tiene reglas responsivas; se revisa a 390 px y a 1280 px de ancho.
tags: [interfaz, responsive]
paquete: interfaz
clave: responsive
verificado_por: senior-diseno/scripts/revisar_diseno.py base
---

# {{id}}: La interfaz se adapta a mobile

## Descripción

Toda página declara el viewport y tiene reglas responsivas. Se revisa a 390 px (mobile) y a 1280 px (escritorio) de ancho, y la prioridad del contenido puede cambiar entre ambos.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| Página con viewport y reglas `@media` | Cumple |
| Página sin viewport | No cumple |
| Revisión a 390 px y a 1280 px | Cumple |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `metodo.md`.

## Estado

provisorio
