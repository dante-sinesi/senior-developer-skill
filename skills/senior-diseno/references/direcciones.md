# Tres alternativas y bosquejos por bloques

El objetivo de la primera ronda es **explorar con amplitud antes de comprometerse**. Tres alternativas que solo cambian de color no exploran nada; tienen que resolver la **estructura** de manera distinta. El aspecto de cada una lo decide el diseñador (ver `metodo.md`).

## Contenido
1. Ejes de divergencia
2. Los bloques
3. La carta de cada alternativa
4. Cómo elige el usuario
5. De la elección a la entrega

## 1. Ejes de divergencia

Las tres alternativas deben diferir siempre en la **estructura** y en al menos otro eje:

| Eje | Ejemplos de caminos opuestos |
|---|---|
| **Estructura y composición** | Narración vertical con ritmo / índice o lista como recurso principal / mosaico asimétrico / pantalla dividida / el objeto central a pantalla completa con paneles |
| **Recorrido** | Lineal / por pasos / todo a la vista con foco móvil |
| **Densidad y ritmo** | Aireada y pausada / densa y eficiente |
| **Voz** | Editorial y cálida / técnica y precisa / lúdica / austera |

Prueba rápida: si se tapan los colores y las tres se ven iguales, falta divergencia.

## 2. Los bloques

Las tres alternativas resuelven **las mismas partes**, cada una a su manera. Así el usuario puede combinarlas ("el menú de la A con la distribución de la B").

- **Sitio o landing:** cabecera, navegación, bloque principal, contenido, formulario, pie.
- **Aplicación web:** navegación, vista de trabajo, lista o tabla, formulario, estados (vacío, cargando, error).
- **Juego:** superficie de juego, estado de la partida, recursos o mano, acciones, navegación.

Cada bloque lleva `data-bloque="nombre"` en el HTML, con los mismos nombres en las tres alternativas, y cada pantalla `data-pantalla="nombre"` (las reglas se miden por pantalla).

## 3. La carta de cada alternativa

Va en un `<aside class="nota">` (se ve con «Ver notas» en la barra del bosquejo):

- **Nombre y idea en una frase** (una metáfora ayuda: "una carta náutica", "un cuaderno de laboratorio").
- **Cliché que evita** (`pautas-anti-genericas.md`, opcional).
- **Riesgo que asume:** algo que podría no gustar.
- **Comportamiento en mobile:** qué se conserva, qué se mueve y qué se esconde.
- **Presupuesto de atención:** cómo cumple la no saturación y, si hay una excepción, el motivo.

## 4. Cómo elige el usuario

Interacciones habituales: "sigamos con la B", "el menú de la A con la distribución de la B", "otras tres más densas". Para mezclar:
1. Anotar la elección por bloque en `comparar.html`.
2. Unificar las variables de diseño (si las dos alternativas usan tipografías distintas, decidir cuál queda, recordando que una familia es lo ideal y dos el máximo).
3. Comprobar coherencia: que los bloques combinados no se contradigan en espaciado, jerarquía o tono.

## 5. De la elección a la entrega

1. Crear la versión nueva con `crear_bosquejos.py --evolucionar <archivo>`.
2. Consolidar las variables en `docs/diseno/sistema/tokens.css` y los componentes en `inventario-componentes.md` (cada uno una sola vez).
3. Diseñar las pantallas completas con todos los estados (reposo, hover, foco, presionado, deshabilitado, cargando, éxito, error) cuando el usuario lo pida.
4. Dejar el contrato de campos de cada formulario en `docs/diseno/campos/`.
5. Pasar `revisar_diseno.py todo`, corregir con el cambio mínimo y mirar las capturas.
6. Registrar las decisiones con ID, dejar `docs/diseno/notas/decisiones.md` al día y actualizar las preferencias del usuario (qué aprobó y qué rechazó, con el motivo).
