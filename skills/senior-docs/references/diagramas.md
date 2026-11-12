# Diagramas legibles con Mermaid

Mermaid se escribe como texto, vive en el repositorio y GitHub lo muestra dibujado. Un diagrama sirve solo si quien lo abre lo entiende en pocos segundos.

## Contenido
1. Reglas
2. Qué diagrama elegir
3. Plantilla de presentación
4. Ejemplos mínimos
5. Cómo dividir un diagrama grande
6. En el README
7. Forma y ancho de la página

## 1. Reglas

1. **Una pregunta por diagrama**, escrita en el título y en una línea de descripción ("¿Cómo se paga un pedido?").
2. **Límites** (los controla `scripts/diagramas.py`; ajustables en `docs/.diagramas.json`):
   - Clases: hasta 10 por diagrama y hasta 8 miembros por clase. Mostrar solo lo relevante para la pregunta, no todos los atributos.
   - Secuencia: hasta 8 participantes y 20 mensajes.
   - Flujo o estados: hasta 15 nodos.
   - Entidad-relación: hasta 10 entidades.
3. **Si no entra, se divide.** Nunca "el diagrama de todo".
4. Dirección de lectura consistente (`flowchart LR` o `TD`, y no mezclar), nombres cortos y significativos, sin cruces de líneas innecesarios.
5. Si la notación tiene algo especial (colores, líneas punteadas), agregar una leyenda de una línea.
6. Citar el ID de la regla en notas cuando corresponda (`Note over Pedido: RN-004`).

## 2. Qué diagrama elegir

| Pregunta | Diagrama |
|---|---|
| ¿Quién habla con quién, y en qué orden? | Secuencia |
| ¿Qué piezas existen y cómo se relacionan? | Clases (o componentes con flujo) |
| ¿Qué datos se guardan y cómo se vinculan? | Entidad-relación |
| ¿Cómo cambia de estado algo? | Estados |
| ¿Cómo se decide o fluye un proceso? | Flujo |

## 3. Plantilla de presentación

Encabezado, descripción de una línea y el bloque. El verificador exige título y descripción.

````markdown
### Pago de un pedido

¿Qué pasos siguen la interfaz, el servidor y la base de datos al pagar un pedido?

```mermaid
sequenceDiagram
    actor U as Usuario
    participant UI as Interfaz
    participant API as Servidor
    participant BD as Base de datos
    U->>UI: Confirmar pago
    UI->>API: POST /pagos
    Note over API: RN-004 saldo suficiente
    API->>BD: Registrar pago
    BD-->>API: ok
    API-->>UI: comprobante
```
````

## 4. Ejemplos mínimos

Clases (solo lo relevante para la pregunta):

```mermaid
classDiagram
    class Pedido {
        +id
        +total()
    }
    class Item {
        +cantidad
        +precio
    }
    Pedido "1" --> "*" Item
```

Entidad-relación:

```mermaid
erDiagram
    CLIENTE ||--o{ PEDIDO : realiza
    PEDIDO ||--|{ ITEM : contiene
```

Estados:

```mermaid
stateDiagram-v2
    [*] --> Creado
    Creado --> Pagado
    Pagado --> Despachado
    Creado --> Anulado
```

## 5. Cómo dividir un diagrama grande

1. Dibujar primero un **diagrama general** con 5 a 8 cajas que son las áreas o casos de uso.
2. Hacer un **diagrama de detalle por cada caja** que lo necesite, cada uno con su pregunta.
3. En el general, enlazar a los detalles con un texto debajo (`Detalle: [[pago-de-pedido]]`).
4. Los diagramas de detalle viven en `docs/diagramas/` con nombre que diga la pregunta (`pago-de-pedido.md`).
5. Correr `diagramas.py`; si algo excede, repetir la división.

## 6. En el README

El README orienta, así que muestra la arquitectura y los flujos principales dibujados, cada uno con un texto breve debajo, y el detalle queda en `docs/diagramas/`.

- **Cuáles:** la arquitectura (módulos y dependencias), de uno a tres flujos de secuencia y, si el proyecto gira en torno a datos, el entidad-relación. **Hasta 4 en total.** Un diagrama de clases de todo es ruido; si hace falta uno, de las pocas clases troncales.
- **Más chicos que en `docs/`**, porque se leen al ancho de la página: flujo de hasta 12 nodos, secuencia de hasta 6 participantes y 12 mensajes, entidad-relación de hasta 8 entidades, clases de hasta 8 con 6 miembros.
- **Una sola fuente:** el diagrama se copia desde `docs/diagramas/` con `senior-docs/scripts/readme_diagramas.py` entre marcas `<!-- diagrama: ruta#n -->` y `<!-- /diagrama -->`. No se edita en el README; se edita la fuente y se hace `sync`.
- **El texto de debajo** (hasta 400 caracteres) lo escribe una persona y dice qué se ve y qué mirar: «Las rutas llaman a los controladores y estos a los servicios». No repite el diagrama.
- **Provisorio o confirmado:** un diagrama inferido del código lleva la nota «sin confirmar»; al confirmarlo (`documentar.py confirmar-diagrama`) y hacer `sync`, la nota sale.
- **Sin renderizar a imagen:** se usa el Mermaid que GitHub dibuja solo; convertirlo a imagen necesitaría una herramienta externa y la aprobación del usuario.

## 7. Forma y ancho de la página

Un diagrama se lee al ancho de la página: si es más ancho, el navegador lo achica y el texto deja de leerse. Medido al dibujarlos con Mermaid: un flujo horizontal de 11 pasos con etiquetas de unos 30 caracteres midió 2.875 px y se leía al 29 % en un README; el mismo flujo en vertical y con etiquetas cortas midió 269 px.

- **Los flujos, en vertical** (`flowchart TB`) salvo que tengan pocos pasos (hasta unos 4). Un flujo horizontal suma el ancho de todos sus pasos; uno vertical solo el del más ancho.
- **Etiquetas cortas:** hasta unos 25 caracteres por línea; el detalle va en una segunda línea (`<br/>`) o en el texto de debajo, no en la caja.
- **Muchos pasos, se agrupan en fases:** más de 8 pasos se abstraen en 3 o 5 cajas con el detalle adentro («Construir: test, código, refactor»). El mismo ciclo de 11 pasos en 4 fases horizontales midió 773 × 123 px; con las 4 fases como columnas (`subgraph`, con los pasos adentro y los retornos entre fases) Mermaid lo acomoda casi cuadrado, 815 × 665 px, sin perder ningún paso. Los subgrafos no cuentan como pasos y su ancho no se estima: se mira dibujado.
- **Secuencias:** el ancho lo fijan los participantes (cada uno suma unos 220 px) y el mensaje más largo entre dos vecinos (unos 7 px por carácter). Hasta 4 o 5 participantes y mensajes de hasta unos 30 o 40 caracteres.
- **Lo controla `diagramas.py`:** estima el ancho de cada flujo y de cada secuencia (error de alrededor del 15 % contra Mermaid) y avisa cuando se achicaría por debajo del 85 % al ancho de un README; en el README (`readme_diagramas.py`) por debajo del 60 % ya no entra. Es una estimación: no reemplaza mirar el diagrama dibujado.
- **Lo que genera la skill sale así:** el mapa de módulos de `/documentar-proyecto` es vertical y las secuencias guardadas con `documentar.py secuencia` avisan si quedan anchas.
