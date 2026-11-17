# Integración continua (CI) en GitHub Actions: detalle

`scripts/ci.py` hace tres cosas, y ninguna fusiona nada:
- **`ci.py estado [--pr N]`: antes de proponer una fusión.** Resume los chequeos del Pull Request. Con algún chequeo en rojo o pendiente (salida 1 o 2) **no se propone fusionar**: se le informa al usuario qué falla o qué falta y decide él, incluso si ya había pedido fusionar. Un PR sin chequeos en un proyecto que sí tiene flujos de CI cuenta como pendiente: los chequeos todavía no arrancaron. Si no se pudo saber el estado (sin `gh`, sin respuesta) sale con 3 y no se da por verde: se informa al usuario.
- **El guardia (`hook_fusion_ci.py`) lo hace cumplir.** Una medición con agentes reales mostró que la instrucción sola no se cumple (los agentes fusionaron 9 de 9 sin mirar, 4 con un chequeo en rojo), así que cada `gh pr merge` pasa por `ci.py estado`: con rojo, o con pendientes (salvo `--auto`), se bloquea sin interrumpir el trabajo; la razón manda a anotar el pendiente en `docs/pendientes.md` y seguir. Para fusionar igual, **solo el usuario** escribe en el chat `/permitir-fusion N` (vale para una fusión de ese Pull Request; Claude no puede darse esa autorización). Si no se pudo saber el estado (sin `gh` o sin red), deja pasar.
- **`ci.py generar`:** arma `.github/workflows/ci.yml` con las pruebas del proyecto (Python, Node o PHP), permisos de solo lectura y la rama principal detectada. Es configuración persistente del repositorio: sin `--aplicar` solo muestra el plan, y se aplica con el visto bueno del usuario. Nunca pisa un flujo existente y, si no encuentra cómo correr pruebas, no escribe nada.
- **`ci.py auditar`:** avisa de un flujo sin pruebas, sin disparo en Pull Request, con `continue-on-error` o `|| true` o con acciones por rama móvil. Lee texto, no analiza YAML: es una guía y no un veredicto.

## Códigos de salida de `ci.py estado`

0 todo en verde o sin CI; 1 hay chequeos en rojo; 2 hay pendientes; 3 no se pudo saber. Con `--pr` acepta un número, una URL o una rama, y con `--repo dueño/nombre` otro repositorio.
