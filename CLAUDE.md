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

## Secretos: nunca en el código ni en GitHub

Ninguna clave, credencial ni dato personal se escribe en archivos que van a git: viven en `.env` (ignorado) y el código los lee de variables de entorno. Los hooks de git y de Claude lo frenan (`skills/senior/scripts/secretos.py`). `.env` se lee o modifica solo con permiso del usuario (`/permitir .env`), y Claude lo propone; mientras tanto usa `env_gestion.py`. Una clave que se subió se rota.

## Objetivo principal: ahorrar tokens donde está medido, con Token Diet como dependencia blanda

`senior` ahorra tokens con sus mecánicas y se apoya en **Token Diet** ([token-diet-skill](https://github.com/dante-sinesi/token-diet-skill), una skill independiente) donde sus mediciones con agentes reales muestran ahorro (hoy: leer PDF y archivos largos). Una mecánica solo se retira de `senior` si esas mediciones mostraron que cuesta más (hoy: la reducción y el bloqueo de imágenes grandes); «Token Diet la cubre» no alcanza. La dependencia es **blanda**: la lectura de PDF y de archivos largos es de Token Diet (`senior` ya no trae conversor ni hook de lectura) y su auditoría de consumo tiene la última palabra; sin ella, `senior` sigue funcionando y lo avisa una vez por proyecto, nunca se rechaza ni se frena por eso. La dependencia va solo en ese sentido: Token Diet nunca depende de `senior`. Detalle y evidencia en `docs/revision-completa.md`.

## Reglas de trabajo en este repositorio

- **Commits, push, Pull Requests y fusiones solo con pedido o aprobación del usuario.** Se propone y se espera el visto bueno. Una rama por cambio, commits atómicos con Conventional Commits en español neutro, y nunca trabajar directo en `main`.
- **El diseñador es un paquete aparte** (`senior-diseno` y `auditar-diseno`, con las tarjetas SVG del README); su regla de enfoque vive en él. `senior` lo usa solo si está instalado: nunca depende de él.
- **`docs/revision-completa.md` es el documento vivo de mejora y se mantiene en el mismo PR.** Todo cambio que toque una parte puntuada o un punto ciego actualiza ahí su fila (nota hoy solo con evidencia, estado del punto ciego), agrega una línea al historial y recalcula el promedio. Un hallazgo nuevo entra como punto ciego. Los puntos de mejora se trabajan uno por rama, con su commit y su PR.
- **El README siempre al día** y sin saludos ni relleno; los textos en español neutro.
- **El README y todo lo que se sube es solo del proyecto.** Una respuesta a una consulta del usuario, su máquina, su memoria o configuración personal de Claude no se escriben en el README, en las skills ni en la documentación: se contestan en el chat. `verificar.py readme` avisa de las señales más comunes.

Proyecto: skill senior.
