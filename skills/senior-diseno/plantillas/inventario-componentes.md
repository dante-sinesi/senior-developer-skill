# Inventario de componentes

Cada componente se define **una sola vez** acá. Regla: no hay un componente nuevo sin justificarlo; antes de diseñar uno, buscar si ya existe uno que sirva (o una variante).

Ejemplo de fila: `| Botón | principal, secundario, peligro | reposo, hover, foco, presionado, deshabilitado, cargando | formularios, cabecera | Una sola acción principal por pantalla |`.

Cada componente del inventario se muestra también en la tarjeta de estilo (`docs/diseno/estilo/`), con todas sus variantes y estados, en el mismo cambio que lo agrega: `python scripts/tarjeta_estilo.py componente "Nombre" --variantes … --estados …`.

| Componente | Variantes | Estados | Dónde se usa | Notas |
|---|---|---|---|---|

## Componentes nuevos propuestos

| Fecha | Componente pedido | Por qué no sirve uno existente | Decisión |
|---|---|---|---|
