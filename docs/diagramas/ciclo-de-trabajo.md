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
    A["Leer el estado y relevar si hace falta"] --> B["Acordar un plan breve"]
    B --> C["Rama por cambio"]
    C --> D["Test rojo desde la regla de negocio"]
    D --> E["Código mínimo en verde"]
    E --> F["Refactor con tests en verde"]
    F --> G["Actualizar docs y README"]
    G --> H["verificar.py"]
    H -->|hallazgos| E
    H --> I["Pull Request con descripción completa"]
    I --> J{"¿Lo aprueba el usuario?"}
    J -->|ajustes| E
    J -->|sí| K["Fusión y estado al día"]
```
