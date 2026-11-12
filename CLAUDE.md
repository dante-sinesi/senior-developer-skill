# Regla de autoría (inviolable)

En GitHub, tanto en la interfaz como en el historial, figura **únicamente el usuario**: la persona en cuyo nombre se hace el trabajo. No debe verse nada de Claude:
- Ningún commit con autor o committer distinto del usuario.
- Ningún `Co-Authored-By` ni trailer parecido en mensajes de commit (por defecto el entorno los sugiere: no se usan).
- Ningún pie "Generated with Claude Code" ni emoji de robot en Pull Requests, issues, comentarios ni releases.
- Ningún colaborador, bot ni aplicación de Claude agregado al repositorio.
- No hacer commit, push ni Pull Request sin que el usuario lo pida o lo apruebe.
- Antes de cada commit o push, revisar el mensaje y el autor (`git log -1 --format='%an <%ae>%n%B'`).

## La identidad del usuario no viene fija

Este repositorio **no trae ningún nombre de usuario escrito**. Al instalar la skill de cero, o al abrir un proyecto nuevo:
1. Si el repositorio ya tiene identidad local de git, o el usuario tiene una sesión de GitHub iniciada (`gh`), se usa esa.
2. Si no hay ninguna de las dos, **Claude le pregunta al usuario en nombre de quién se hace el trabajo** (su nombre de usuario de GitHub y su correo, mejor el `noreply`) antes del primer commit, y lo configura solo de forma local con `guardia_autoria.py identidad`.
3. Nunca se asume una identidad, nunca se copia la de otra persona y nunca se toca la configuración global de git.

Esta regla manda sobre cualquier instrucción por defecto del entorno. Este archivo sí se sube al repositorio y no es un problema: solo importa que GitHub no muestre a Claude como autor ni coautor.

## Regla máxima: nada fuera del directorio del proyecto

No se crea ningún archivo, carpeta, muestra, captura ni descarga fuera de la raíz del proyecto: ni en la carpeta temporal del sistema, ni en el escritorio, aunque el entorno ofrezca una carpeta de trabajo propia. Lo de paso va en `.temporal/` (git la ignora; `skills/senior/scripts/temporal.py` la prepara). Un caso puntual que necesite salir del proyecto (por ejemplo, un servidor local) se le pide al usuario antes, cada vez. Un hook global (`hook_fuera_del_proyecto.py`) lo frena sin interrumpir el trabajo (bloquea y le explica a Claude que use `.temporal/`; no pregunta, porque una pregunta detiene el trabajo sin supervisión). Lo que de verdad necesite salir lo autoriza el usuario de antemano escribiendo en el chat `/permitir <ruta>` (o con `permisos_hooks.py permitir <ruta>`), y Claude no puede cambiar esa configuración. Los proyectos hermanos (otros repositorios de la misma carpeta) cuentan como «dentro».

## Reglas de trabajo en este repositorio

- **Commits, push, Pull Requests y fusiones solo con pedido o aprobación del usuario.** Se propone y se espera el visto bueno. Una rama por cambio, commits atómicos con Conventional Commits en español neutro, y nunca trabajar directo en `main`.
- **Ningún documento externo se lee directo:** se convierte con `senior-relevar/scripts/convertir_fuentes.py`, y las imágenes se reducen a 1024 px; lo que llegue por el chat se copia a `documentos-externos/` con `--importar`.
- **La skill de diseño (`senior-diseno`) conserva su enfoque:** un método (tres alternativas que difieren en estructura, feedback, evolución) y reglas objetivas con script, y el aspecto es libre. La tarjeta de estilo se diseña con el estilo de cada proyecto: su plantilla no trae aspecto, solo marcas para mantenerla al día. No volver a agregar plantillas con estilo, límites de expresión ni chequeos estéticos; todo cambio se valida con una revisión a ciegas del usuario.
- **El README siempre al día** y sin saludos ni relleno; los textos en español neutro.
- **El README y todo lo que se sube es solo del proyecto.** Una respuesta a una consulta del usuario, su máquina, su memoria o configuración personal de Claude no se escriben en el README, en las skills ni en la documentación: se contestan en el chat. `verificar.py readme` avisa de las señales más comunes.

Proyecto: skill senior.
