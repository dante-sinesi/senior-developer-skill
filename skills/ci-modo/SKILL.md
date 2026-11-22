---
name: ci-modo
description: Elige cómo se verifica la CI antes de fusionar un PR. Solo con /ci-modo, lo escribe el usuario.
argument-hint: "local [comando de pruebas] | estricto"
disable-model-invocation: true
---

# /ci-modo

Sirve para que el comando aparezca al escribir `/` y se vean los dos modos:

- `/ci-modo local [comando de pruebas]`: las pruebas que corren en esta máquina reemplazan a la CI de GitHub (por ejemplo, sin minutos de Actions). Sin comando se usa el detectado del proyecto.
- `/ci-modo estricto`: manda la CI de GitHub (el valor por defecto).

El cambio lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede cambiar el modo por su cuenta. Tu parte es confirmarle al usuario en una línea lo que dijo el hook (modo y comando). Después, en modo local, `python ~/.claude/skills/senior-git/scripts/ci.py local` corre las pruebas y anota el commit verificado; el guardia de fusión lo usa. Detalle en `senior-git/references/ci.md`.
