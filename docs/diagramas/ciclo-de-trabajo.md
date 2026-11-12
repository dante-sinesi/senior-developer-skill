---
tipo: diagrama
titulo: Ciclo de trabajo de un cambio
resumen: Los pasos de un cambio, desde leer el estado hasta fusionar, con el test primero y la aprobación del usuario.
tags: [diagrama, flujo]
---

# Ciclo de trabajo de un cambio

### Ciclo de trabajo de un cambio

¿Qué pasos sigue un cambio desde que se pide hasta que se fusiona?

```mermaid
flowchart LR
    subgraph P["Preparar"]
        direction TB
        A["Leer estado"] --> B["Plan breve"] --> C["Rama"]
    end
    subgraph K["Construir"]
        direction TB
        D["Test rojo"] --> E["Código mínimo"] --> F["Refactor"]
    end
    subgraph V["Verificar"]
        direction TB
        G["Docs y README"] --> H["verificar.py"]
    end
    subgraph R["Revisar y fusionar"]
        direction TB
        I["Pull Request"] --> J{"¿Aprobado?"} --> L["Fusión"]
    end
    P --> K --> V --> R
    V -->|hallazgos| K
    R -->|ajustes| K
```
