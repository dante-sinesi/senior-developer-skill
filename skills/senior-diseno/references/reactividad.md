# Reactividad: la interfaz responde a lo que la persona hace

Política permanente. Toda acción del usuario recibe una respuesta visible e inmediata: un botón que se resalta, un menú que se desliza en lugar de aparecer de golpe, un envío que muestra que está en curso. Lo verifica `revisar_diseno.py interaccion`.

## Contenido
1. Estados de cada elemento interactivo
2. Movimiento: duraciones y curvas
3. Patrones habituales
4. Accesibilidad y movimiento reducido
5. Equilibrio con la no saturación

## 1. Estados de cada elemento interactivo

Todo botón, enlace y campo define:

| Estado | Qué comunica | Nota |
|---|---|---|
| Reposo | Que se puede usar | Parece interactivo antes de tocarlo |
| **Hover** | "Esto responde a vos" | Solo con puntero; nunca es la única señal |
| **Foco visible** | Dónde está el teclado | `:focus-visible`, contorno nítido; imprescindible |
| **Presionado** | "Recibí tu acción" | `:active`; es la señal de toque en mobile |
| Deshabilitado | No disponible, y por qué | Explicar el motivo cerca |
| Cargando | La acción está en curso | Indicador y bloqueo de doble envío |
| Éxito / error | Resultado | Texto específico, no solo color |

## 2. Movimiento: duraciones y curvas

Referencias iniciales (heurísticas):

| Tipo | Duración |
|---|---|
| Microinteracción (botón, enlace, campo) | 120 a 200 ms |
| Paneles, menús, desplegables | 200 a 300 ms |
| Cambios de página o de vista | hasta 400 ms |
| Algo que supere 500 ms | revisar: se siente lento |

- **Curvas de desaceleración** (entrada rápida y final suave), por ejemplo `cubic-bezier(0.2, 0.7, 0.2, 1)`; evitar el movimiento lineal.
- **Animar solo lo que importa:** `transform` y `opacity` rinden mejor que propiedades de layout. Listar las propiedades en `transition`; evitar `transition: all`.
- Que algo cambie de estado con movimiento ayuda a entender qué pasó; el movimiento **debe tener función**.

## 3. Patrones habituales

- **Menú lateral en mobile:** se desliza con `transform: translateX()` y cambia `visibility` al terminar; el botón actualiza `aria-expanded`.
- **Desplegable de opciones avanzadas:** con transición de altura sutil o de opacidad; respeta el estado abierto con teclado.
- **Botón de envío:** pasa a "cargando" al presionar, se bloquea y confirma el resultado.
- **Mensajes de éxito o error:** aparecen junto al elemento que los causó, con una entrada suave, y no desaparecen sin que se puedan leer.
- **Carga de contenido:** esqueletos o indicadores que ocupan el lugar final, para que no salte el diseño.

## 4. Accesibilidad y movimiento reducido

- Respetar `prefers-reduced-motion`: con esa preferencia se quitan o se reducen las transiciones.

```css
@media (prefers-reduced-motion: reduce) {
  .boton, .menu { transition: none; }
}
```
- Nada que parpadee más de tres veces por segundo.
- Todo lo que responde al hover tiene su equivalente de foco y de toque.
- Las animaciones no retrasan una tarea: la persona puede actuar sin esperar a que termine.

## 5. Equilibrio con la no saturación

La reactividad responde a lo que la persona hace. El movimiento decorativo o ambiental es libre (decisión artística), siempre que respete `prefers-reduced-motion` y no retrase una tarea. Los banners, insignias que pulsan y ventanas modales siguen limitados por la no saturación.
