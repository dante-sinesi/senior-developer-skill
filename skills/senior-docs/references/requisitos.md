# Requisitos: los siete tipos en detalle

## Contenido
1. Qué es cada tipo, con ejemplos
2. Cómo escribir un buen requisito
3. Extraer reglas de un sistema heredado
4. Requisitos de seguridad y etiquetas ISO

## 1. Qué es cada tipo

**Negocio (RN).** Reglas, políticas y objetivos de la organización que el sistema debe respetar. Ejemplo: *RN-001: toda compra de más de 10 unidades recibe un 20% de descuento.* Son la fuente de verdad de los tests.

**Usuario (RU).** Lo que cada tipo de usuario necesita lograr. Ejemplo: *RU-003: el vendedor puede anular un pedido propio mientras no esté despachado.*

**Dominio (RD).** Los conceptos del problema y sus restricciones, independientes de la tecnología. Ejemplo: *RD-002: un pedido tiene uno o más ítems; un ítem pertenece a un solo pedido.*

**Funcional (RF).** Qué debe hacer el sistema para cumplir lo anterior. Ejemplo: *RF-010: el sistema calcula el total del carrito aplicando RN-001 y redondea a dos decimales.*

**No funcional (RNF).** Cualidades medibles: rendimiento, seguridad, disponibilidad, usabilidad, mantenibilidad. Ejemplo: *RNF-004: el listado de pedidos responde en menos de 2 segundos con 10.000 registros.* Debe ser medible; "rápido" no sirve.

**Transición (RT).** Lo necesario para pasar del estado actual al nuevo: migración de datos, convivencia con el sistema viejo, capacitación, plan de puesta en marcha. Ejemplo: *RT-001: migrar los clientes del sistema anterior conservando sus identificadores.*

**Interfaces externas (RI).** Contratos con otros sistemas: APIs, archivos, dispositivos. Ejemplo: *RI-002: la pasarela de pagos recibe un POST con monto y moneda y responde con un identificador de transacción.* Incluir formato, errores esperados y autenticación.

## 2. Cómo escribir un buen requisito

- **Uno por archivo**, con ID estable. Nunca se reutiliza un ID; si deja de valer se marca `Estado: reemplazado por RN-0XX`.
- **Atómico**: una regla, una idea. Si lleva un "y", probablemente son dos.
- **Verificable**: debe poder decirse si se cumple o no. Los de negocio y funcionales llevan **ejemplos con valores**:

  | Entrada | Resultado esperado |
  |---|---|
  | 10 unidades a 5,00 | 50,00 (sin descuento) |
  | 11 unidades a 5,00 | 44,00 (20% de descuento) |

  Esos ejemplos son la materia prima de los tests (`senior-tdd`).
  Si un requisito se verifica con un script en lugar de un test (por ejemplo, las reglas de interfaz), lo declara en el encabezado con `verificado_por: <ruta del script y su chequeo>` y cuenta como verificado en la trazabilidad.
- **Con origen**: quién lo dijo o dónde está definido (el usuario, un contrato, una norma).
- **Enlazado**: citar otros requisitos con `[[RN-001]]` para que el mapa de conceptos arme la red.

## 3. Extraer reglas de un sistema heredado

El código muestra qué hace el sistema, no qué debería hacer. Para reconstruir requisitos:

1. Leer el código y listar **hipótesis** de reglas ("parece que más de 10 unidades da 20%").
2. **Presentarlas al usuario** para que las confirme, corrija o descarte. Nunca documentarlas como verdad por cuenta propia.
3. Registrar cada regla confirmada como RN con ejemplos.
4. Donde el código y la regla confirmada discrepen, anotarlo: es un defecto candidato. El test de la regla fallará hasta que se decida qué corregir.
5. Mientras no haya reglas confirmadas, los tests de caracterización (ver `senior-tdd`) protegen el comportamiento actual, marcados como "estado actual, no necesariamente correcto".

## 4. Requisitos de seguridad y etiquetas ISO

Los requisitos de seguridad se escriben como RNF y llevan la etiqueta `iso:` con el control de la ISO/IEC 27002:2022 al que responden, por ejemplo:

```
---
id: RNF-007
tipo: no-funcional
titulo: Contraseñas almacenadas con hash
resumen: Las contraseñas nunca se guardan en claro.
tags: [seguridad, autenticacion]
iso: 8.24
---
```

Los controles organizacionales, de personas o físicos que el código no puede resolver se registran igualmente (como RNF o RT) indicando que dependen de la organización.
