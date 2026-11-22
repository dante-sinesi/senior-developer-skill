---
name: quitar-permiso
description: Quita la autorización de una carpeta. Solo con /quitar-permiso, lo escribe el usuario.
argument-hint: "<ruta>"
disable-model-invocation: true
---

# /quitar-permiso

Atajo para que el comando aparezca al escribir `/`: revoca la autorización de una carpeta que se había permitido con /permitir.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar esta configuración por su cuenta. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
