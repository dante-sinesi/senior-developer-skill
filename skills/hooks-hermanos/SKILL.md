---
name: hooks-hermanos
description: Elige si cuentan como «dentro» los proyectos hermanos. Solo con /hooks-hermanos.
argument-hint: "si | no"
disable-model-invocation: true
---

# /hooks-hermanos

Atajo para que el comando aparezca al escribir `/`: decide si escribir en otros repositorios de la misma carpeta cuenta como dentro del proyecto (por defecto sí).

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
