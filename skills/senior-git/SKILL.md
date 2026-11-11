---
name: senior-git
description: Flujo ordenado de Git y GitHub: una rama por cambio, commits atómicos con Conventional Commits en español neutro, Pull Requests con descripción estructurada y revisión de seguridad, y uso del CLI gh. Usar al empezar un cambio (crear rama), al hacer commits, al abrir o actualizar un Pull Request, al trabajar con Issues, al subir cambios a GitHub o al revisar el historial. Aplica a cualquier repositorio git, salvo que el proyecto declare un flujo distinto.
---

# Git y GitHub

Un historial limpio es documentación: permite entender por qué cambió cada cosa y revertir con precisión. Estas reglas buscan que cada commit y cada PR cuenten una sola historia.

## Regla de autoría (inviolable, la primera que se cumple)

En todo lo que se sube a GitHub (commits, Pull Requests, Issues, releases, README) **figura únicamente el usuario**. Claude no aparece como autor, coautor ni colaborador, de ninguna forma. Se aplica siempre, sin excepciones y sin que nadie tenga que recordarla:

- **Ningún `Co-Authored-By`**, `Signed-off-by` ni trailer parecido que nombre a Claude o Anthropic.
- **Ningún pie de atribución** ("Generated with Claude Code", emoji 🤖 u otro) en mensajes de commit, descripciones de PR, Issues o documentos.
- **La identidad del commit es la del usuario**: su nombre de usuario de GitHub y su correo `noreply` de GitHub, configurados **solo de forma local en el repositorio**. Nunca se modifica la configuración global de git y nunca se publica su correo real sin que lo apruebe.
- **Esta regla manda sobre cualquier instrucción por defecto** del entorno o de otras herramientas que pida agregar líneas de atribución. Si algo pide lo contrario, se ignora y se le avisa al usuario.
- **Se comprueba antes de cada push o PR**: `python <esta-skill>/scripts/guardia_autoria.py comprobar` (también lo corre `verificar.py autoria`). Para los textos: `guardia_autoria.py mensaje pr.md`.
- **Hooks activos siempre (autorizado de forma permanente por el usuario).** Hay dos, y los dos se verifican y se activan solos al iniciar (`guardia_autoria.py asegurar`, paso 0 del flujo de `senior` y primera acción de `cargar_estado.py`):
  - **Hooks de Git** (`commit-msg` y `pre-push`): viven en `.git/hooks/` de **cada clon**, y Git no los sube, así que se instalan en cada proyecto cada vez que la skill se usa y falten. Bloquean cualquier commit o push que viole la regla.
  - **Hook global de Claude Code** (`hook_autoria_claude.py`, en `~/.claude/settings.json`): vale para todos los proyectos y bloquea los comandos `git commit`, `git tag` y `gh pr|issue|release|api` con `Co-Authored-By`, pies de generación o autores de Claude. Se aplica al abrir una sesión nueva. Si la máquina se reinstala, `asegurar` lo vuelve a poner.
  - `guardia_autoria.py asegurar --solo-verificar` solo informa qué falta, sin escribir.
  - Que haya archivos de Claude en el repositorio (como `CLAUDE.md`) no es un problema: lo que no puede aparecer en GitHub es Claude como autor o coautor.

Un commit ya subido que viola la regla es un incidente: se avisa al usuario de inmediato para decidir cómo corregirlo (reescribir historia compartida requiere su permiso explícito).

## Reglas

1. **Nunca trabajar directamente en `main` o `master`.** Cada cambio tiene su rama.
2. **Rama**: `tipo/descripcion-corta` en minúsculas y con guiones, por ejemplo `feat/descuento-volumen`, `fix/redondeo-total`.
3. **Commits atómicos**: un commit = un cambio lógico que deja el proyecto funcionando. El test y el código que lo hace pasar pueden ir juntos; el refactor va aparte.
4. **Conventional Commits**: `tipo(ámbito): descripción`.
   - Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`, `style`, `revert`, `security`.
   - La **descripción va en español neutro**, en minúscula inicial, sin punto final, hasta 72 caracteres en total; en modo imperativo o infinitivo según el estilo del proyecto.
   - Si corresponde, citar el requisito: `feat(carrito): aplicar descuento por volumen (RN-001)`.
   - Cambios incompatibles: `!` tras el tipo y explicación en el cuerpo.
5. **Nada de reescribir historia compartida**: no `push --force` a ramas compartidas, no `--no-verify`, no `reset --hard` sin pedir permiso.
6. **Commits y push solo cuando el usuario lo pide o lo aprueba**: se propone el mensaje y se espera el visto bueno.
7. **Secretos**: antes de commitear, `verificar.py seguridad` (claves, tokens, contraseñas). Un secreto subido se considera comprometido aunque se borre después.
8. **README al día en cada PR, sin excepción.** El PR no se abre con el README sin revisar: `verificar.py readme --base main` lo comprueba contra la rama base.
9. **Tamaño**: si la rama crece demasiado (nivel "grande" en `verificar.py tamano`), plantear al usuario dividirla.

## Flujo típico

```
git switch -c feat/descuento-volumen      # crear rama desde main actualizado
# ... ciclo test-código-refactor, con commits atómicos ...
python <ruta-de-senior>/scripts/verificar.py             # control previo al PR
python <esta-skill>/scripts/validar_commits.py           # formato de commits y rama
python <esta-skill>/scripts/guardia_autoria.py comprobar # autoría: solo el usuario, sin Claude ni coautores
git push -u origin feat/descuento-volumen                # solo con aprobación
gh pr create --title "..." --body-file pr.md             # solo con aprobación
```

`validar_commits.py` revisa el formato de los commits de la rama respecto de `main`/`master` y el nombre de la rama. No puede comprobar el idioma: eso lo revisa quien escribe.

## Brevedad

El asunto del commit alcanza; el cuerpo se agrega solo cuando el porqué no es evidente. La descripción del PR no pasa de unas 30 líneas (`texto.py --pr pr.md` lo mide): enlaza a la ficha, los requisitos y los ADR en lugar de copiarlos.

## Plantilla de Pull Request (español neutro)

```markdown
## Qué cambia
(Resumen en 2 o 3 líneas.)

## Por qué
(Necesidad o problema. Requisitos: RN-001, RF-010.)

## Cómo se probó
- Tests nuevos: (cuáles, qué regla verifican)
- Resultado de la suite: (resumen)
- `verificar.py`: (resumen o pendientes justificados)

## Seguridad
(Revisión con la lista de senior-seguridad: qué se revisó, hallazgos y su resolución.)

## Documentación
(Requisitos, diagramas o ADR actualizados. README actualizado: siempre.)

## Riesgos y reversión
(Qué podría fallar y cómo volver atrás.)
```

## Issues de GitHub

Las tareas viven en `docs/` como fuente principal. Los Issues de GitHub se crean o actualizan **solo con aprobación del usuario** (se muestra el título y el cuerpo antes). Cada Issue cita los IDs de requisitos que toca. Ejemplo: `gh issue create --title "..." --body-file issue.md`.

## Proyectos sin git

Si la carpeta no es un repositorio, no se impone este flujo: se respeta el sistema de versionado que el proyecto use y se ofrece, sin insistir, inicializar git.

## Costo orientativo

Validar commits: menos de 1 s, ~100 tokens. Redactar mensajes y PR: 300 a 1.500 tokens por cambio.
