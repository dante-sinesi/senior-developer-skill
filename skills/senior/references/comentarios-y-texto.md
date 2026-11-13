# Comentarios y exceso de texto

El exceso de texto es una forma de ilegibilidad, igual que un diagrama gigante. Lo que sobra confunde y envejece: hay que mantenerlo y termina mintiendo.

## Contenido
1. Comentarios en el código
2. Límites de extensión
3. Regla de desborde: dividir o mover, nunca recortar
4. Un dato, un lugar
5. Mensajes, PR y respuestas al usuario
6. Vigilancia automática

## 1. Comentarios en el código

Se comenta **el porqué**, nunca el qué. Los nombres y las funciones pequeñas explican el qué.

- Permitido y breve: la razón de una decisión no obvia, una advertencia, el ID del requisito que implementa el código (`RN-004`), un `TODO` con su motivo.
- Prohibido: código comentado (git lo conserva), banners decorativos, comentarios de historial o autoría ("agregado hoy", fechas, `@author`) y comentarios que repiten la línea siguiente.
- Documentación de funciones (JSDoc, docstrings): una o dos líneas sobre qué garantiza y qué errores lanza, con el ID del requisito. Sin `@param` ni `@returns` que repitan la firma: es lo que más infla los comentarios cuando se pide "dejarlo bien documentado" (la evaluación mostró hasta un 48% de líneas de comentario así).
- Un comentario largo es señal de una decisión que merece un ADR: dejar en el código una línea que lo cite (`// Ver ADR-004`).
- Idioma: español neutro.
- **No se tocan los comentarios de código que no se está modificando.** Si hay mucho para limpiar, se anota en `docs/pendientes.md` y se propone como cambio aparte.

Ejemplo:

```
// Mal: repite el código
// incrementa el contador
contador++;

// Bien: explica la razón
// Se cuenta antes de validar porque el límite de intentos incluye los fallidos (RN-012)
contador++;
```

**Excepción: el atajo.** Una simplificación deliberada con un límite conocido se marca en una línea, `atajo: <límite>; cuándo: <qué la haría insuficiente>`. Dice un límite y un disparador, no repite el código, y `atajos.py` los junta en un registro (`docs/atajos.md`). Un atajo sin «cuándo:» se avisa como SIN DISPARADOR en `verificar.py deuda`.

## 2. Límites de extensión

Por defecto (líneas con contenido, sin encabezado ni vacías); se ajustan en `docs/.texto.json`:

| Documento | Máximo |
|---|---|
| ESTADO.md | 60 |
| Requisito | 40 |
| Ficha de cambio | 50 |
| ADR | 60 |
| Descripción de PR | 30 |
| Asunto de commit | 72 caracteres |

Son avisos, no bloqueos: sirven para detectar que algo creció más de lo razonable.

## 3. Regla de desborde: dividir o mover, nunca recortar

Lo que excede no se borra: se clasifica y va a su lugar propio, dejando un enlace.

| Documento | Si excede |
|---|---|
| ESTADO | Historial a `docs/historial/AAAA-MM.md`; decisiones a un ADR; detalle del trabajo en curso a su ficha. |
| Requisito | Dividir en requisitos atómicos con ID propio; tablas largas de ejemplos a un anexo enlazado. |
| Ficha | Dividir en fichas menores bajo una ficha general; ideas a pendientes; decisiones a un ADR; al cerrar, archivar con resumen de 3 líneas. |
| ADR | Una decisión por ADR; análisis y evidencia a un anexo enlazado. |
| PR | Enlazar a la ficha, los requisitos y los ADR en vez de repetirlos. |
| Comentario largo | Explicación a un ADR y comentario de una línea que lo cite. |

Procedimiento: (1) clasificar lo que sobra: repetido (se reemplaza por un enlace), detalle distinto (se mueve a su lugar), histórico (se archiva), obsoleto (se elimina; git lo conserva); (2) dejar en el original un enlace o un resumen de una línea; (3) correr `texto.py check` y `texto.py compare` de Token Diet para comprobar que nada se perdió.

## 4. Un dato, un lugar

Documentación completa no significa redundante. Cada tipo de dato tiene un lugar de referencia y el resto enlaza con `[[ID]]`:

| Dato | Lugar de referencia |
|---|---|
| Regla de negocio | Requisito RN |
| Concepto del dominio | Requisito RD |
| Contrato con un sistema externo | Requisito RI |
| Decisión y su porqué | ADR |
| Estado actual | ESTADO.md |
| Pasos de un cambio | Ficha |

Si el mismo párrafo aparece en dos documentos, se deja en el de referencia y se reemplaza el otro por un enlace.

## 5. Mensajes, PR y respuestas al usuario

- Commit: solo el asunto; agregar cuerpo únicamente cuando el porqué no es evidente.
- PR: las cinco secciones de la plantilla, cada una breve, enlazando en lugar de copiar.
- Respuestas al usuario: primero el resultado, sin recapitular lo que ya sabe ni listar cada archivo tocado.

## 6. Vigilancia automática

```
python <token-diet>/scripts/comentarios.py --changed       # solo el código modificado
python <token-diet>/scripts/texto.py check docs            # límites, repetidos, información perdida
python <token-diet>/scripts/comentarios.py <carpeta>       # todo un árbol, para proponer una limpieza aparte
python <token-diet>/scripts/texto.py check pr.md           # medir la descripción de un PR
python <token-diet>/scripts/texto.py compare ANTERIOR NUEVO  # al mover o recortar texto: qué información se perdió
```

Son heurísticas: marcan candidatos a revisar. `texto` compara con la versión anterior en git y avisa si un párrafo desapareció sin aparecer en otro documento (posible información perdida); no detecta reescrituras con otras palabras.
