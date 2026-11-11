# Inventario de campos: {{formulario}}

Se arma antes de diseñar el formulario y lo aprueba el usuario. Fuentes, en orden: requisitos y reglas de negocio, modelo de datos, respuestas del usuario, comportamiento del sistema actual.

Clasificación: **ahora** (imprescindible), **derivable** (se completa solo), **avanzado** (opcional, en un desplegable), **después** (se pide más adelante), **descartar** (ninguna regla lo usa).

| Campo | Etiqueta final | Clasificación | Motivo | Fuente |
|---|---|---|---|---|
| (dato) | (etiqueta única y específica) | ahora | (qué pasa si falta) | (RF-000, esquema, usuario) |

Reglas: como máximo 4 campos "ahora" a la vez (si hay más, pasos cortos); hasta 6 en "avanzado". Las etiquetas finales pasan al contrato `docs/diseno/campos/{{formulario}}.md`.
