# UX: tareas, flujos, desktop y mobile

La interfaz es el medio; lo que importa es que la persona logre algo. El orden de trabajo es: tareas, flujo, jerarquía de contenido y recién después composición visual.

## Contenido
1. Tareas y flujo
2. Jerarquía del contenido
3. Desktop y mobile
4. Estados que se suelen olvidar
5. Sitio o aplicación
6. Accesibilidad mínima
7. Diez heurísticas para revisar

## 1. Tareas y flujo

1. Listar las 3 a 5 tareas principales en lenguaje de la persona ("encontrar un horario", "pagar", "cancelar un pedido").
2. Para cada una, dibujar el camino mínimo: punto de entrada, pasos, resultado. Contar pasos y decisiones.
3. Detectar dónde hay fricción: demasiadas opciones, términos que la persona no usa, pasos que podrían omitirse.
4. Definir la **acción principal** de cada pantalla. Si hay dos igual de importantes, probablemente son dos pantallas.

## 2. Jerarquía del contenido

- Ordenar el contenido por importancia para la tarea, no por importancia para la organización.
- Cada pantalla tiene **un foco**; lo demás se subordina con tamaño, peso, color y espacio.
- Agrupar lo relacionado (proximidad) y separar lo distinto; el espacio en blanco también comunica.
- Escribir etiquetas con el vocabulario de quien usa el sistema.

## 3. Desktop y mobile

Se diseñan juntos, con prioridades distintas. Reducir una pantalla de escritorio no es diseñar para mobile.

| | Desktop | Mobile |
|---|---|---|
| Atención | Escaneo en múltiples zonas; se pueden ver varias cosas a la vez | Una cosa por vez; el contenido se apila y se prioriza |
| Navegación | Barra superior o lateral, menús con más ítems | Pocos destinos principales (hasta cinco) al alcance del pulgar; el resto, detrás de un menú |
| Interacción | Puntero preciso, hover disponible | Toque impreciso: sin depender de hover; áreas táctiles amplias |
| Texto | Líneas de 45 a 75 caracteres | Cuerpo de al menos 16 px; los campos de formulario también, para que el navegador no amplíe la pantalla |
| Formularios | Varias columnas cuando conviene | Una columna, teclado adecuado (numérico, email), mínimo de campos |

Decidir qué se **conserva, qué se mueve y qué se esconde** al pasar de desktop a mobile; esa decisión es parte del diseño y se anota en la carta de la dirección.

## 4. Estados que se suelen olvidar

Todo componente tiene más de un estado: **vacío, cargando, con error, éxito, deshabilitado, foco, con datos largos o ausentes**. El bosquejo no los resuelve todos, pero la propuesta fuerte sí. `revisar_diseno.py estados` avisa de los que faltan (error, vacío y carga en una app, texto largo) y de lo que el navegador deja por defecto (color de selección, casillas, cifras de tablas, barras de scroll). Son solo avisos y se resuelven con diseño, no con una plantilla.

## 5. Sitio o aplicación

| | Sitio o landing | Aplicación web |
|---|---|---|
| Meta | Persuadir, contar, generar identidad | Permitir hacer tareas rápido y sin errores |
| Estructura | Narrativa vertical, secciones con ritmo | Navegación persistente, vistas de trabajo |
| Densidad | Aireada, con énfasis | Mayor, con jerarquía muy clara |
| Foco del diseño | Composición, tipografía, imagen, voz | Estados, tablas, formularios, atajos, consistencia |
| Riesgo típico | Verse como cualquier otra landing | Tableros idénticos y formularios largos sin ayuda |

Dentro de cada uno, el **modo de la pantalla** (ver `briefing.md`) decide cómo se gasta la ambición. No limita el arte: lo orienta.

| Modo | Dónde se nota la ambición |
|---|---|
| **Decidir** (landing, precios, campaña) | Composición, voz y un punto de vista propio; es donde más se arriesga |
| **Hacer una tarea** (panel, editor, ajustes) | Precisión: escaneo rápido, consistencia, los patrones que la persona ya conoce; la identidad vive en los detalles |
| **Entender** (documentación, artículo, ayuda) | Estructura para comprender primero y después una lectura que valga la pena |
| **Recorrer una obra** (portfolio, galería) | La obra manda desde la primera vista y la interfaz se corre |

## 6. Accesibilidad mínima (no negociable)

- **Contraste:** 4,5 a 1 para texto normal; 3 a 1 para texto grande (desde 24 px, o 18,66 px en negrita) y para componentes de interfaz y gráficos (WCAG).
- **Tamaño táctil:** mínimo 24×24 px (WCAG 2.2, nivel AA); recomendado 44×44 px.
- **Foco visible** en todo elemento interactivo; nada que dependa solo del color; nada que dependa solo del hover.
- **Texto alternativo** en imágenes con significado; estructura de encabezados lógica; respeto de `prefers-reduced-motion`.

## 7. Diez heurísticas para revisar (Nielsen, resumidas)

1. Visibilidad del estado del sistema. 2. Coincidencia con el mundo real (lenguaje de la persona). 3. Control y libertad (deshacer, salir). 4. Consistencia y estándares. 5. Prevención de errores. 6. Reconocer en lugar de recordar. 7. Flexibilidad y eficiencia (atajos). 8. Diseño estético y minimalista. 9. Ayuda para reconocer, diagnosticar y recuperarse de errores. 10. Ayuda y documentación.
