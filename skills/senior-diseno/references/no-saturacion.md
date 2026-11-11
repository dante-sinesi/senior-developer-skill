# Política de no saturación del usuario

Estricta y permanente. **Mide cuánto se le pide hacer a la persona (campos, acciones, destinos); no mide cuánto arte tiene la pantalla**: imágenes, íconos, ilustración y movimiento con propósito no cuentan. Una interfaz saturada obliga a la persona a pensar en la interfaz y no en su tarea. Esta política se aplica a todo bosquejo y propuesta, y la verifica `revisar_diseno.py saturacion`.

## Contenido
1. Presupuesto de atención por pantalla
2. Reglas de fondo
3. Formularios
4. Acciones reconocibles antes de interactuar
5. Excepciones
6. Ejemplo

## 1. Presupuesto de atención por pantalla

Una "pantalla" es lo que la persona ve a la vez; se marca con `data-pantalla="nombre"`. Límites iniciales (heurísticos; se ajustan por proyecto con justificación):

| Qué se cuenta | Límite |
|---|---|
| Acción principal | **1** |
| Campos de formulario visibles a la vez | **4** |
| Campos dentro de "opciones avanzadas" (desplegable) | 6 |
| Acciones visibles (sin contar la navegación) | 5 |
| Destinos de navegación principal | 7 en desktop, 5 en mobile |
| Texto por bloque (en sitios) | una idea; referencia de 80 palabras |

## 2. Reglas de fondo

- **Solo lo necesario para la tarea actual.** Lo demás, a pedido: un desplegable, un detalle, otra vista.
- **Una idea por bloque**, con jerarquía clara y espacio como herramienta.
- **Sin ruido innecesario:** nada de avisos, banners, ventanas modales ni insignias que no sean esenciales. Un solo elemento "ruidoso" por vista.
- **Densidad deliberada:** en una aplicación de trabajo se puede mostrar mucha información si la jerarquía y la agrupación son fuertes; lo que se evita es mostrar de más sin propósito.
- **El espacio en blanco es parte del diseño**, no un hueco para rellenar.

## 3. Formularios

- **Pedir solo lo imprescindible ahora** y dejar el resto para después, en pasos cortos.
- **Opciones avanzadas desplegables** (`<details>` u otro recurso) para lo opcional: los campos dentro no cuentan como visibles, pero tienen su propio tope y el desplegable lleva una etiqueta clara ("Más opciones").
- **Valores por defecto y autocompletado** (`autocomplete`, teclado adecuado: numérico, correo).
- **No pedir lo que ya se sabe** ni lo que se puede derivar.
- Mostrar el progreso en formularios de varios pasos; validar en línea con mensajes específicos.
- En mobile, una columna.
- Antes de diseñar, armar el **inventario de campos** (ver `etiquetas-y-formularios.md`).

## 4. Acciones reconocibles antes de interactuar

- **Etiquetas verbales con objeto:** "Guardar pedido", no "Aceptar" ni "Enviar".
- **Nunca solo un ícono** como acción: siempre con texto visible.
- Lo clicable **parece clicable** (forma, color, subrayado de los enlaces) y tiene estados visibles.
- El texto **anticipa lo que va a pasar**; las acciones destructivas se separan de las demás y se confirman.
- Una acción **principal** claramente dominante; las secundarias, subordinadas.
- Un deshabilitado explica por qué lo está.

## 5. Excepciones

Si un diseño necesita superar un límite, **se justifica por escrito en el propio bosquejo**, dentro de la pantalla:

```html
<!-- excepcion-saturacion: formulario regulatorio; todos los campos son obligatorios por ley -->
```

Sin esa justificación, el script marca FALLA. Una excepción justificada se informa como tal y el usuario la ve.

## 6. Ejemplo

Antes: un alta de cliente con 11 campos en una pantalla (nombre, apellido, documento, teléfono, correo, dirección, ciudad, provincia, código postal, fecha de nacimiento, notas).

Después, en dos pasos:
1. **Paso 1 (4 campos):** nombre y apellido, documento, correo, teléfono. Es lo que la regla de negocio exige para crear el cliente.
2. **Paso 2 (opcional):** dirección, ciudad, provincia y código postal pasan a "Más opciones"; fecha de nacimiento se pide recién si hace falta para facturar; las notas se agregan después de crear.
