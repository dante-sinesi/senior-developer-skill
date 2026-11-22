---
name: permisos
description: Muestra qué frena cada guardia, lo autorizado y lo bloqueado. Solo con /permisos.
disable-model-invocation: true
---

# /permisos

Atajo para que el comando aparezca al escribir `/`: muestra la configuración de los guardias y lo último que se bloqueó. Mostrale al usuario lo que respondió el hook, completo y tal cual.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
