---
name: docs-modo
description: Elige si las barreras de documentación bloquean o solo avisan. Solo con /docs-modo.
argument-hint: "exigir | aviso"
disable-model-invocation: true
---

# /docs-modo

Atajo para que el comando aparezca al escribir `/`: «exigir» (por defecto) no deja editar código sin haber leído antes la documentación del proyecto; «aviso» deja pasar y solo lo advierte.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
