---
tipo: diagrama
titulo: Cómo frenan los hooks
resumen: Qué decide un hook cuando Claude intenta algo protegido: pasar, bloquear sin interrumpir o preguntar, y qué queda registrado.
tags: [diagrama, secuencia]
---

# Cómo frenan los hooks

### Cómo frenan los hooks

¿Qué pasa cuando Claude intenta escribir fuera del proyecto o editar un archivo protegido?

```mermaid
sequenceDiagram
    participant C as Claude
    participant H as Guardia (hook)
    participant K as Configuración
    actor U as Usuario
    C->>H: escritura riesgosa
    H->>K: ¿está autorizada?
    K-->>H: no
    Note over H: modo denegar (el predeterminado, sin interrumpir)
    H->>C: bloquea y explica
    H->>K: registra el bloqueo
    Note over U: al volver el usuario
    H->>U: informa bloqueos
    U->>K: /permitir ruta
```
