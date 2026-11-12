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
flowchart TB
    A["Leer estado y relevar"] --> B["Plan breve"]
    B --> C["Rama por cambio"]
    C --> D["Test rojo"]
    D --> E["Código mínimo en verde"]
    E --> F["Refactor"]
    F --> G["Docs y README"]
    G --> H["verificar.py"]
    H -->|hallazgos| E
    H --> I["Pull Request"]
    I --> J{"¿Aprobado?"}
    J -->|ajustes| E
    J -->|sí| K["Fusión y estado al día"]
```
