---
name: senior-diseno
description: Diseño de interfaces dentro del paquete senior: método fijo y reglas objetivas, con libertad total en lo artístico. Método: briefing, UX, tres alternativas que difieren en estructura (bosquejos HTML desktop y mobile), feedback del usuario y evolución de la elegida. Reglas verificadas por script que no atacan al aspecto: una familia tipográfica (dos como máximo), etiqueta visible en cada campo, no más de cuatro campos visibles, una sola acción principal, contraste, estados de hover y foco, sistema de diseño sin duplicados. Usar siempre que se pida diseñar, rediseñar o proponer el aspecto de un sitio, landing, aplicación web, panel, juego o pantalla; bosquejos, wireframes o formularios; mejorar la UI o la UX; o cuando algo parezca genérico, saturado o hecho por IA.
---

# Diseño de interfaces (senior-diseno)

Parte del paquete `senior`. Esta skill **define el diseño**: dirección, experiencia de uso, composición, variables y especificaciones. **Implementarlo** (programar la interfaz) sigue las reglas de `senior`: tests primero, documentación viva, Git ordenado. Es una sola sesión y un solo flujo: no hay traspaso entre roles.

Tiene dos partes, y la separación es deliberada:

1. **Un método** (cómo se trabaja con el usuario): `references/metodo.md`.
2. **Unas reglas objetivas** que no tocan el aspecto artístico y que un script verifica.

**El aspecto es libre.** Estilo, paleta, ilustración, imágenes, íconos, movimiento, tono: los decide el diseño, con ambición, para cada proyecto. La skill no trae plantillas con estilo, ni límites de expresión, ni listas de lo que "debe" tener un diseño artístico. Si una regla parece chocar con una idea artística fuerte, se justifica la excepción por escrito en lugar de achatar la idea.

## Dónde vive todo

Los artefactos de diseño viven en `docs/diseno/`, junto al resto de la documentación viva:
`estilo/` (la tarjeta de estilo y sus alternativas), `rondas/` (bosquejos y notas de cada ronda), `notas/preferencias.md` y `decisiones.md`, `sistema/` (variables e inventario de componentes), `campos/` (contratos de campos) y `auditoria/`.

- **Los bosquejos no llevan tests.** Son material de diseño, no comportamiento; el TDD de `senior-tdd` empieza cuando se **implementa** una pantalla.
- **Al implementar:** usar las variables de diseño sin copiar sus valores, programar cada componente una sola vez y usar las etiquetas de los formularios **exactamente** como figuran en el contrato de campos.
- **Decisiones de arquitectura** (por ejemplo, el framework de interfaz): van a un ADR de `senior-docs`. Las decisiones de diseño (D-001…) viven en `docs/diseno/notas/decisiones.md` y los ADR las citan por ID.
- **Requisitos de interfaz:** las reglas de abajo se pueden escribir como un **paquete de inicio** de requisitos no funcionales provisorios con `python scripts/paquete_interfaz.py` (sin `--aplicar` solo muestra qué crearía). Se proponen al adoptar un proyecto y desde `/auditar-diseno`; el usuario acepta, cambia o descarta cada uno, y cada requisito declara el chequeo que lo verifica.

## Escala del trabajo: liviano por defecto

El costo en tokens crece con el papeleo, no con el diseño. Por eso:
- **Trabajo chico** (una pantalla, una landing, un formulario): ronda **liviana**. Tres esqueletos y **una sola hoja de notas** (`NOTAS.md`: briefing mínimo, supuestos, decisiones, preguntas). Nada más.
- **Proyecto mediano o grande** (varias pantallas, sistema de diseño): `crear_bosquejos.py --completo`, que agrega briefing, inventario de campos, decisiones, variables e inventario de componentes.
- **Se lee lo mínimo:** este `SKILL.md` y `references/metodo.md` alcanzan para empezar. El resto de las referencias se abre solo cuando el caso lo pide (un formulario: `etiquetas-y-formularios.md` y `no-saturacion.md`; accesibilidad: `reactividad.md`; sistema de diseño: `sistema-de-diseno.md`). Los documentos de un proyecto grande se crean cuando hacen falta, no antes.

## El método (resumen)

1. **Briefing** y **UX** (`references/briefing.md`, `ux.md`): para quién, qué tarea, en qué orden; inventario de campos de cada formulario.
1b. **Estilo** (proyectos medianos y grandes con interfaz; opcional en los chicos): antes de las pantallas, tres alternativas de estilo A, B y C como tarjetas, feedback y ajuste. La elegida queda como **tarjeta de estilo viva** que usa las variables reales del sistema y crece con cada componente nuevo (`references/estilo.md`).
2. **Tres alternativas que difieren en estructura** (disposición, jerarquía, navegación, recorrido). No se impone estilo ni ausencia de estilo: cada alternativa tiene el aspecto que se crea mejor para ella, con la ambición que el proyecto pida.
3. **Esperar el feedback del usuario.** No se avanza solo.
4. **Evolucionar o corregir** la elegida (o pedir tres nuevas): una versión nueva por cambio, con el estilo del proyecto y las correcciones aplicadas.
5. **Revisión final antes de entregar,** en un solo paso: `revisar_diseno.py todo <archivos> --capturas` (reglas y capturas de desktop y mobile), y **mirar las capturas**. Las reglas se corrigen con el cambio mínimo, sin rediseñar.
6. **Cierre:** en un trabajo chico, un resumen corto en el chat y las notas de la ronda; en uno grande, `docs/diseno/notas/decisiones.md` al día y las preferencias actualizadas.

Detalle, ejemplos y qué se entrega en cada paso: `references/metodo.md`.

## Reglas objetivas (con script)

| Regla | Esencia | Detalle |
|---|---|---|
| Tipografía | **Una familia es lo ideal, dos el máximo en toda la web**; más solo si el arte lo requiere, con excepción escrita | `references/tipografia-y-color.md` |
| Etiquetas | Cada campo con su etiqueta visible, única y específica | `references/etiquetas-y-formularios.md` |
| No saturación | 1 acción principal, 4 campos visibles (hasta 6 más en "opciones avanzadas"), navegación corta, acciones con texto | `references/no-saturacion.md` |
| Accesibilidad | Contraste suficiente, foco visible, objetivos táctiles, uso sin hover, `prefers-reduced-motion` | `references/reactividad.md`, `tipografia-y-color.md` |
| Reactividad | Estados de hover, foco y presionado; transiciones breves | `references/reactividad.md` |
| Sistema de diseño | Variables e inventario de componentes; cada componente se define una vez | `references/sistema-de-diseno.md` |

Comandos (todos en `<esta-skill>/scripts/`):

```
python crear_bosquejos.py --nombre <proyecto> [--tipo sitio|app] [--completo]
python crear_bosquejos.py --evolucionar docs/diseno/rondas/<ronda>/direccion-b.html
python tarjeta_estilo.py nueva --nombre <proyecto>      # tres alternativas de estilo (A, B y C)
python tarjeta_estilo.py elegir <estilo-x.html>         # la elegida pasa a ser la tarjeta viva
python tarjeta_estilo.py componente "Nombre" --variantes a,b --estados x,y   # componente nuevo: inventario y tarjeta
python tarjeta_estilo.py estado                         # ¿la tarjeta está al día?
python revisar_diseno.py todo docs/diseno/rondas/<ronda>/*.html [--tipo sitio|app] [--sitio] --capturas
python capturar.py <archivo.html>        # solo capturas, si hace falta por separado
python colores.py "#1a1a1a" "#ffffff"
```

`revisar_diseno.py` acepta los chequeos `base`, `tipografia`, `saturacion`, `interaccion`, `estados`, `etiquetas`, `contraste` y `sistema`; ninguno juzga el aspecto. FALLA incumple una regla estricta; una excepción se justifica por escrito dentro de la pantalla con `<!-- excepcion-saturacion: motivo -->` (o `excepcion-tipografia`). Son heurísticas: marcan qué mirar. `capturar.py` usa el Edge o Chrome instalados para sacar PNG de desktop y mobile, que se leen como imágenes.

## Otros modos

- **Auditar un proyecto existente:** `/auditar-diseno` (skill `auditar-diseno`). Informe en `docs/diseno/auditoria/`; no modifica el proyecto. Ver `references/auditoria.md`.
- **Llevar preferencias a un proyecto nuevo**, solo cuando el usuario lo pide: `scripts/importar_preferencias.py <otro-proyecto>`.

## Puntos de control (se consulta antes de)

- Instalar algo (fuentes, herramientas) o usar servicios externos (fuentes web, bancos de imágenes).
- Aplicar una excepción a una regla estricta que el usuario no haya aceptado.
- Importar preferencias de otro proyecto.
- Pasar de los bosquejos a implementar: solo cuando el usuario aprueba la dirección.
- Pasar de las alternativas de estilo a las de estructura: solo cuando el usuario elige el estilo.

## Imágenes del usuario

Las referencias visuales o capturas se leen directamente. Se pregunta qué le gusta de cada una y se extraen principios; no se copian.

## Tarjetas del README

Cuando un repositorio nuevo elige README con tarjetas SVG, este método se aplica a la portada: tres estilos que difieren en estructura a partir de la descripción del proyecto, el usuario elige y se evoluciona. Los pasos, el formato del tema y las reglas objetivas están en `references/tarjetas-readme.md`. No hay estilos incluidos: se inventan por proyecto.
