---
name: inicializar-repositorio
description: Inicializa un proyecto como repositorio de GitHub y sube lo que haya: identidad de Git local, .gitignore de secretos, README (simple o con tarjetas SVG), repositorio remoto (lo crea si falta), descripción y topics obligatorios, hooks de Git, escaneo de claves y commit y push. Usar cuando el usuario escriba /inicializar-repositorio, o pase el enlace o el nombre de un repositorio y pida inicializarlo, armarlo, dejarlo listo o subir el proyecto a GitHub.
---

# Inicializar un repositorio

Deja una carpeta lista y publicada en GitHub en un solo paso, sin armar cada comando. Un script hace lo mecánico (`scripts/inicializar_repo.py`); el modelo solo aporta lo que hay que redactar: la descripción y los topics.

## Qué se necesita

1. **El repositorio:** un enlace (`https://github.com/dueño/nombre`), `dueño/nombre` o solo el nombre (el dueño es el usuario de la sesión de `gh`). Si el usuario no lo dio, preguntarlo.
2. **La visibilidad, solo si hay que crearlo:** público o privado. No se decide por el usuario: si no la dijo, preguntarla.
3. **El tipo de README, que se pregunta siempre** (con la herramienta de preguntas): **README simple** (título, descripción y lo que contiene la carpeta) o **con tarjetas SVG** (una portada generada con un estilo propio del proyecto). Como orientación, los repositorios privados suelen llevar README simple y los públicos tarjetas, así que se recomienda según la visibilidad, pero no se decide por el usuario. Si ya hay un README, no se toca y no se pregunta.
   - **Con tarjetas:** `senior-diseno` crea **tres estilos** distintos a partir de la descripción (método en `senior-diseno/references/tarjetas-readme.md`), los muestra lado a lado con `readme_tarjetas.py comparar` y espera que el usuario elija. El elegido se pasa con `--estilo`.
4. **La descripción y los topics, que son obligatorios.** Se redactan leyendo el README y lo que haya en la carpeta: una sola línea (hasta 350 caracteres, sin correos ni claves) y topics en minúsculas con los de dominio (los de tecnología los suma el script). Si no hay de dónde sacarlos, preguntar; no inventarlos.

## Pasos

1. **Plan (no escribe nada):**
   ```
   python <esta-skill>/scripts/inicializar_repo.py <repo> --raiz <proyecto> [--publico | --privado] --descripcion "…" --topics a,b,c --readme simple | tarjetas [--estilo <tema.json>]
   ```
   Muestra qué existe en GitHub y en la carpeta, qué se va a hacer y qué **bloquea** (falta la visibilidad, la descripción o los topics; claves o datos personales a la vista; un `origin` distinto; un remoto que ya tiene contenido y la carpeta no es un repositorio; falta la sesión de `gh`).
2. **Aplicar:** si nada bloquea, el mismo comando con `--aplicar`. Hace, en orden: identidad local de Git, `git init` en `main`, `.gitignore` de secretos, hooks de Git, el repositorio remoto (lo crea si no existe), la descripción y los topics con `repo_meta.py`, el README (simple o con la portada de tarjetas), los commits (`chore: inicializa el repositorio` y, si ya había archivos, `chore: agrega el contenido existente`) y el push. Con `--sin-subir` hace todo menos el push.
3. **Informar:** la URL, los commits, la descripción y los topics que quedaron, y lo que no se hizo.

## Autorización

Invocar este comando es el pedido del usuario: cubre **exactamente** crear ese repositorio, el commit inicial y el push a `origin/main`. No cubre Pull Requests, otras ramas ni cambiar la visibilidad. Los commits llevan solo la identidad del usuario, sin coautores ni pies de atribución.

## Lo que el script nunca hace

Forzar un push; mezclar la historia local con un remoto que ya tiene contenido distinto; pisar una descripción que no puso `senior`; subir una carpeta con claves o datos personales a la vista (una clave que ya estuvo a la vista se rota, no alcanza con ocultarla); tocar la configuración global de git. Si algo **bloquea**, no hace nada y lo dice: no se espera una respuesta durante el trabajo, se anota qué falta y se sigue con lo demás.

## Después

Si el proyecto va a usar la metodología `senior`, el siguiente paso es `/adoptar-proyecto` (documentación base y relevamiento). Este comando no la crea.
