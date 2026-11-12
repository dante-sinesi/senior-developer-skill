---
tipo: diagrama
titulo: Cómo está armado el paquete
resumen: senior como puerta de entrada y qué hay alrededor: método, relevamiento, diseño, comandos, verificador y hooks.
tags: [diagrama, arquitectura]
---

# Cómo está armado el paquete

### Cómo está armado el paquete

¿Qué skills forman el paquete, cuál es la puerta de entrada y qué vigila el trabajo?

```mermaid
flowchart TB
    U["Usuario"] --> S["senior: principios, flujo y control"]
    S --> M["Método: tdd, refactor, docs, git, seguridad"]
    S --> R["Relevar y documentar"]
    S --> D["Diseño"]
    S --> C["Comandos"]
    M --> P["Proyecto: docs/, README y código"]
    R --> P
    D --> P
    C --> P
    P --> V["verificar.py"]
    P --> G["GitHub: ramas y PR"]
    H["Hooks globales"] -.-> P
```
