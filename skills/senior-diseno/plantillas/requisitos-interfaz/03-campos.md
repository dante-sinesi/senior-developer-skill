---
id: {{id}}
tipo: no-funcional
titulo: Máximo cuatro campos visibles por pantalla
resumen: Una pantalla muestra hasta 4 campos; los opcionales van en un desplegable de hasta 6 campos.
tags: [interfaz, formularios, no-saturacion]
paquete: interfaz
clave: campos
verificado_por: senior-diseno/scripts/revisar_diseno.py saturacion
---

# {{id}}: Máximo cuatro campos visibles por pantalla

## Descripción

Una pantalla muestra como máximo 4 campos de formulario a la vez. Los opcionales van dentro de un desplegable («Más opciones») con hasta 6 campos más. Lo imprescindible se pide primero y lo demás, después.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| 4 campos visibles y 6 en «Más opciones» | Cumple |
| 5 campos visibles | No cumple |
| 4 visibles y 7 en «Más opciones» | No cumple (máximo 6) |
| Formulario por pasos de 3 campos cada uno | Cumple |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `no-saturacion.md`.

## Estado

provisorio
