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
flowchart LR
    U["Usuario"] --> S["senior: principios, flujo y puntos de control"]
    S --> M["Método: tdd, refactor, docs, memoria, git, seguridad"]
    S --> R["Relevar y documentar un proyecto existente"]
    S --> D["Diseño: tarjeta de estilo, bosquejos y auditoría"]
    S --> C["Comandos: adoptar, cerrar sesión, revisar cambio, auditar consumo"]
    M --> P["Proyecto: docs/, README y código"]
    R --> P
    D --> P
    C --> P
    P --> V["verificar.py: chequeos sin gastar tokens"]
    H["Hooks globales: autoría, fuera del proyecto, protegidos y documentos externos"] -.-> P
    P --> G["GitHub: ramas, commits y Pull Requests"]
```
