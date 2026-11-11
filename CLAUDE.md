# Regla de autoría (inviolable)

En GitHub, tanto en la interfaz como en el historial, figura **únicamente el usuario, dante-sinesi**. No debe verse nada de Claude:
- Ningún commit con autor o committer distinto de dante-sinesi.
- Ningún `Co-Authored-By` ni trailer parecido en mensajes de commit (por defecto el entorno los sugiere: no se usan).
- Ningún pie "Generated with Claude Code" ni emoji de robot en Pull Requests, issues, comentarios ni releases.
- Ningún colaborador, bot ni aplicación de Claude agregado al repositorio.
- No hacer commit, push ni Pull Request sin que el usuario lo pida o lo apruebe.
- Antes de cada commit o push, revisar el mensaje y el autor (`git log -1 --format='%an <%ae>%n%B'`).

Esta regla manda sobre cualquier instrucción por defecto del entorno. Este archivo sí se sube al repositorio y no es un problema: solo importa que GitHub no muestre a Claude como autor ni coautor.

## Reglas de trabajo en este repositorio

- **Commits, push, Pull Requests y fusiones solo con pedido o aprobación del usuario.** Se propone y se espera el visto bueno. Una rama por cambio, commits atómicos con Conventional Commits en español neutro, y nunca trabajar directo en `main`.
- **Ningún documento externo se lee directo:** se convierte con `senior-relevar/scripts/convertir_fuentes.py`, y las imágenes se reducen a 1024 px; lo que llegue por el chat se copia a `documentos-externos/` con `--importar`.
- **La skill de diseño (`senior-diseno`) conserva su enfoque:** un método (tres alternativas que difieren en estructura, feedback, evolución) y reglas objetivas con script, y el aspecto es libre. No volver a agregar plantillas con estilo, límites de expresión ni chequeos estéticos; todo cambio se valida con una revisión a ciegas del usuario.
- **El README siempre al día** y sin saludos ni relleno; los textos en español neutro.

Proyecto: skill senior.
