---
name: permitir
description: Autoriza de antemano una carpeta fuera del proyecto. Solo con /permitir, lo escribe el usuario.
argument-hint: "<ruta> [-- motivo]"
disable-model-invocation: true
---

# /permitir

Atajo para que el comando aparezca al escribir `/`: autoriza de antemano una carpeta (y todo lo que contiene) para que los guardias no la bloqueen. Confirma en una línea qué ruta quedó autorizada.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
