---
id: {{id}}
tipo: no-funcional
titulo: Cada componente y cada variable de diseño se define una sola vez
resumen: Los colores, tipografías y espacios salen de variables, y cada componente tiene 1 sola definición.
tags: [interfaz, sistema-de-diseno]
paquete: interfaz
clave: sistema
verificado_por: senior-diseno/scripts/revisar_diseno.py sistema
---

# {{id}}: Cada componente y cada variable de diseño se define una sola vez

## Descripción

Los colores, las tipografías y los espacios se declaran una vez como variables de diseño y todo el estilo las usa. Cada componente tiene una sola definición; un componente nuevo se justifica antes de crearlo.

## Ejemplos verificables

| Caso | Resultado esperado |
|---|---|
| 0 colores sueltos fuera de las variables | Cumple |
| Colores copiados como literales en 5 reglas | Aviso: usar variables |
| Dos botones con definiciones casi idénticas | Aviso: unificar |

## Origen

Reglas de diseño de `senior-diseno`, propuestas al iniciar el proyecto. El usuario decide si las acepta, las cambia o las descarta.

## Relacionados

- Referencias de `senior-diseno`: `sistema-de-diseno.md`.

## Estado

provisorio
