# Ceremonia según el tamaño del cambio

`scripts/verificar.py tamano` sugiere el nivel a partir de archivos y líneas tocadas. Es una guía: si un cambio chico toca algo crítico (autenticación, dinero, datos personales), se trata como mediano.

| Nivel | Criterio orientativo | Qué se hace |
|---|---|---|
| Trivial | 1 archivo, hasta 5 líneas | Sin ficha. Si cambia comportamiento, test primero igualmente. Una línea en `ESTADO.md`. |
| Chico | hasta 3 archivos y 50 líneas | Test primero, commit atómico, una línea en `ESTADO.md`. Plan en una frase. |
| Mediano | hasta 10 archivos y 300 líneas | Ficha de cambio propia con alcance y lista de pasos. Documentación afectada al día. Diagrama de secuencia si cruza capas. Revisión de seguridad con la lista de `senior-seguridad`. PR con descripción completa. |
| Grande | más que lo anterior | Todo lo del nivel mediano, y además: plantear al usuario si conviene dividirlo en cambios menores, presentar el plan antes de empezar y consultar el uso de agentes en paralelo (con su costo en tokens). |

## Qué no depende del tamaño

- Un cambio que **altera comportamiento** siempre empieza con un test que falle.
- Un **refactor** nunca se hace sin tests en verde.
- Un cambio que **no altera comportamiento** (texto, comentario, nombre de variable) no lleva test nuevo.
- La **seguridad** se revisa siempre; lo que cambia es la profundidad.

## Ficha de cambio (nivel mediano o grande)

Vive en `docs/cambios/AAAA-MM-DD-nombre.md`. Plantilla en `senior-memoria/plantillas/ficha-cambio.md`. Lo esencial:

- Qué y por qué.
- Requisitos que toca (con sus IDs).
- **Alcance**: lista de archivos o carpetas previstos (el verificador compara contra esto).
- Lista de pasos con casillas: test rojo, verde, refactor, docs, seguridad, PR.
- Estado: en curso, bloqueado o terminado.
