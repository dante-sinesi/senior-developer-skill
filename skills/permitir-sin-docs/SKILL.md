---
name: permitir-sin-docs
description: Autoriza un Pull Request que cambia código sin documentación. Solo con /permitir-sin-docs.
argument-hint: "(sin argumentos: vale para el próximo)"
disable-model-invocation: true
---

# /permitir-sin-docs

Atajo para que el comando aparezca al escribir `/`: autoriza UNA vez abrir un Pull Request que la barrera de documentación frenaría. Se gasta al usarlo. Para dejar todo el proyecto en advertencia está `/docs-modo aviso`.

Lo aplica el hook de permisos de senior al enviar el mensaje, no esta skill: lo que el usuario escribe no lo puede falsificar Claude, y Claude no puede darse esta autorización. Tu parte es contarle al usuario, en una línea, lo que dijo el hook. Detalle en `docs/referencia.md`.
