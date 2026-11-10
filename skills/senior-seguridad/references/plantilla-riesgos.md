# Registro de riesgos (modo formal, al estilo ISO/IEC 27005)

Archivo del proyecto: `docs/seguridad/riesgos.md`. Se crea solo si el usuario acepta pasar al modo formal. Se revisa al agregar funciones que manejen datos nuevos y al menos en cada versión importante.

## Criterios

- **Probabilidad**: baja (1), media (2), alta (3).
- **Impacto**: bajo (1), medio (2), alto (3).
- **Nivel** = probabilidad × impacto: 1 a 2 bajo, 3 a 4 medio, 6 a 9 alto.
- Un riesgo alto no se acepta sin decisión explícita del usuario.

## Activos

| ID | Activo | Descripción | Sensibilidad |
|---|---|---|---|
| A-01 | (ej. datos de clientes) | (qué contiene y dónde vive) | (personal / financiera / pública) |

## Riesgos

| ID | Activo | Amenaza | Control (ISO 27002:2022) | Prob. | Impacto | Nivel inicial | Tratamiento | Nivel residual | Responsable |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | A-01 | (ej. inyección SQL que expone datos) | 8.28 consultas parametrizadas | 2 | 3 | 6 | mitigar | 2 | (nombre) |

## Decisiones de aceptación

- R-00: aceptado por (persona) el AAAA-MM-DD porque (motivo).
