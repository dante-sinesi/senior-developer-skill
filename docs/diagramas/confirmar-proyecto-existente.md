---
tipo: diagrama
titulo: Cómo se confirma un proyecto existente
resumen: De adoptar un proyecto a tener requisitos vigentes y tests, pasando por lo provisorio y la consulta de reglas.
tags: [diagrama, secuencia]
---

# Cómo se confirma un proyecto existente

### Cómo se confirma un proyecto existente

¿Cómo pasa un proyecto que ya existe de no tener documentación a tener requisitos confirmados y tests?

```mermaid
sequenceDiagram
    actor U as Usuario
    participant C as Claude
    participant S as Scripts
    participant D as docs/
    U->>C: /adoptar-proyecto
    C->>D: crea docs/ y relevamiento
    U->>C: /documentar-proyecto
    C->>S: analiza el código
    S->>D: genera docs provisorios
    S->>D: consulta de reglas
    Note over D: provisorio hasta confirmar
    U->>D: responde la consulta
    C->>D: confirma y pasa a vigente
    C->>D: tests desde los ejemplos
```
