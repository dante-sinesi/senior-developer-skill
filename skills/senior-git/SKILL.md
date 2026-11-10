---
name: senior-git
description: Flujo ordenado de Git y GitHub: una rama por cambio, commits atómicos con Conventional Commits en español neutro, Pull Requests con descripción estructurada y revisión de seguridad, y uso del CLI gh. Usar al empezar un cambio (crear rama), al hacer commits, al abrir o actualizar un Pull Request, al trabajar con Issues, al subir cambios a GitHub o al revisar el historial. Aplica a cualquier repositorio git, salvo que el proyecto declare un flujo distinto.
---

# Git y GitHub

Un historial limpio es documentación: permite entender por qué cambió cada cosa y revertir con precisión. Estas reglas buscan que cada commit y cada PR cuenten una sola historia.

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
