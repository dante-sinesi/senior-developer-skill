---
name: permitir-fusion
description: Autoriza UNA fusión de un Pull Request con chequeos sin verde. Solo con /permitir-fusion.
argument-hint: "[número del Pull Request]"
disable-model-invocation: true
---

# /permitir-fusion

Atajo para que el comando aparezca al escribir `/`: autoriza una sola fusión de ese Pull Request (o del de la rama actual) aunque sus chequeos de CI no estén en verde; se gasta al usarla.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
