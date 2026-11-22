---
name: hooks-modo
description: Elige si los guardias bloquean sin interrumpir o preguntan. Solo con /hooks-modo.
argument-hint: "denegar | preguntar"
disable-model-invocation: true
---

# /hooks-modo

Atajo para que el comando aparezca al escribir `/`: «denegar» (por defecto) bloquea y le explica a Claude qué hacer sin interrumpir; «preguntar» pregunta en la interfaz y espera.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
