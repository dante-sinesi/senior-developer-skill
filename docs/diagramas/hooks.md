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
    participant H as Hook
    participant K as Configuración
    actor U as Usuario
    C->>H: escribe fuera del proyecto
    H->>K: ¿autorizada? ¿qué modo?
    alt está autorizada
        H-->>C: pasa
    else modo denegar, por defecto
        H-->>C: bloquea y da la ruta nueva
        H->>K: registra el bloqueo
        C->>C: rehace dentro del proyecto
    else modo preguntar
        H->>U: pregunta y espera
    end
    U->>K: al volver: bloqueos o permitir
```
