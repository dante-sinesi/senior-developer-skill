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
    participant C as Claude con senior
    participant S as Scripts
    participant D as docs/
    U->>C: /adoptar-proyecto
    C->>D: crea docs/, README y relevamiento
    U->>C: /documentar-proyecto
    C->>S: analiza el código sin gastar tokens
    S->>D: diagramas, interfaces, dominio y decisiones, todo provisorio con evidencia
    S->>D: consulta con las reglas de negocio candidatas
    Note over D: provisorio hasta que el usuario confirma
    U->>D: responde la consulta
    C->>D: reglas confirmadas pasan a requisitos vigentes con ejemplos
    C->>D: los tests salen de esos ejemplos
```
