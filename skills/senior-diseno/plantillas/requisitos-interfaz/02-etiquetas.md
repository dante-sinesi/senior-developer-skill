---
id: {{id}}
tipo: no-funcional
titulo: Cada campo tiene una etiqueta visible, única y específica
resumen: Todo campo de formulario muestra 1 etiqueta propia; el texto de ayuda dentro del campo no la reemplaza.
tags: [interfaz, formularios]
paquete: interfaz
clave: etiquetas
verificado_por: senior-diseno/scripts/revisar_diseno.py etiquetas
---

# {{id}}: Cada campo tiene una etiqueta visible, única y específica

## Descripción

Cada campo de formulario tiene 1 etiqueta visible que dice qué dato es. No hay dos campos con la misma etiqueta en una pantalla, y un texto de ayuda dentro del campo no reemplaza a la etiqueta.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| Campo «Correo electrónico» con etiqueta visible | Cumple |
| Campo con solo texto de ayuda dentro | No cumple |
| Dos campos con la etiqueta «Fecha» | No cumple (usar «Fecha de entrega» y «Fecha de pago») |
| Campo con la etiqueta «Dato» | No cumple (etiqueta genérica) |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `etiquetas-y-formularios.md`.

## Estado

provisorio
