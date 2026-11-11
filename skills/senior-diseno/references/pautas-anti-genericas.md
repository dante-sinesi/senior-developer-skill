# Pautas para romper el diseño genérico de la IA

**Material de consulta opcional.** No son reglas ni las controla ningún script: sirven para inspirarse cuando un diseño se siente promedio. El aspecto sigue siendo decisión del diseñador.

El diseño genérico no es un error: es el promedio. Aparece cuando se elige siempre lo más probable. Esta guía lista los patrones más repetidos, por qué aparecen y alternativas concretas. No son prohibiciones absolutas: un patrón común puede ser correcto si se eligió a propósito.

## Contenido
1. Tres pruebas rápidas
2. Los doce patrones y cómo romperlos
3. Reglas para diseñar con carácter

## 1. Tres pruebas rápidas

- **Prueba del intercambio:** si se cambia el logo por el de otra empresa y todo sigue funcionando, el diseño es genérico.
- **Prueba del borrado:** si se quita la capa decorativa (degradados, sombras, ilustraciones) y no queda identidad, la identidad era solo decoración.
- **Prueba de la pregunta:** ¿qué hace reconocible esta pantalla aunque no se vea el logo? Si no hay respuesta, falta una idea.

## 2. Los doce patrones y cómo romperlos

| # | Patrón repetido | Por qué aparece | Alternativas |
|---|---|---|---|
| 1 | **Degradado violeta a azul** como firma | Es el color "tecnológico" más frecuente en lo que la IA vio | Color tomado del dominio (materiales, objetos, lugar); paleta corta con un acento fuerte; campos de color planos; duotono |
| 2 | **Tipografía por defecto** (Inter, Roboto, Arial, la del sistema) | Es la opción segura y está en todos los ejemplos | Un par con carácter: una tipografía de titulares con personalidad y una de texto muy legible; ver `tipografia-y-color.md` |
| 3 | **Héroe centrado + tres tarjetas + doble botón** | Es la plantilla de landing más copiada | Estructura que salga del contenido: columnas editoriales, índice o lista como recurso principal, grilla asimétrica, titular largo alineado a la izquierda, tipografía como imagen |
| 4 | **Tarjetas con sombra suave y esquinas de 12–16 px en todo** | Parece "moderno" sin decidir nada | Una lógica de bordes elegida: líneas finas, sombras duras desplazadas, sin bordes y solo espacio, o radios con sentido (0 en todo, pastilla solo en acciones) |
| 5 | **Glassmorphism, desenfoque y orbes de fondo** | Efecto vistoso que no cuesta pensar | Superficies opacas con jerarquía clara; profundidad con color y tamaño, no con desenfoque |
| 6 | **Íconos emoji o círculos de color con iconos genéricos** | Rellenan espacio con apariencia de producto | Íconos propios y con función, de un solo set y un único grosor, o marcas tipográficas; nunca círculos genéricos para llenar |
| 7 | **Textos genéricos** ("Transforma tu negocio", "Potencia tu equipo", "Sin fricción") | Frases que sirven para cualquier producto | Afirmaciones concretas con cifras y sustantivos; vocabulario de las personas usuarias; microcopy con voz propia |
| 8 | **Simetría, centrado y espaciado uniforme en todo** | Es lo más fácil de equilibrar | Ritmo: densidad variable, espacio en blanco intencional, un solo elemento dominante por pantalla, contraste de escala fuerte entre titular y texto (al menos 3 a 1) |
| 9 | **Modo oscuro "tech" con neón, o blanco puro con gris** | Son los dos extremos habituales | Neutros con tinte (cálido o frío), papel hueso, negro tinta; el modo oscuro como diseño aparte, no una inversión |
| 10 | **Imágenes de relleno, blobs abstractos, ilustraciones intercambiables** | Cubren el hueco de contenido | Ilustración o imagen **del objeto real del negocio**, con intención (el grano de café, el tablero, el producto); datos, diagramas o fotografía propia. Las imágenes son bienvenidas cuando cuentan algo; lo que se evita es la que rellena |
| 11 | **La misma animación de aparición (fade-up) en todo** | Se aplica por reflejo | Movimiento con significado: un momento orquestado, transiciones que expliquen un cambio de estado |
| 12 | **Paneles con tarjetas de KPI idénticas y un gráfico de líneas** | Es el tablero de ejemplo universal | Jerarquía según la decisión que toma la persona: qué mirar primero y qué hacer; tablas densas y legibles, mini-gráficos junto al dato, anotaciones |

## 3. Reglas para diseñar con carácter

1. **Una idea por dirección**, formulada en una frase y, si ayuda, como metáfora (por ejemplo, "una carta náutica", "un diario de laboratorio").
2. **Restricción como motor:** limitar la paleta (tres colores y un acento), las tipografías (dos) y las formas (una lógica de bordes). Los límites obligan a decidir.
3. **Un foco por pantalla.** Si todo destaca, nada destaca.
4. **Declarar el cliché evitado y el riesgo asumido** en la carta de cada dirección. Un riesgo es algo que podría no gustar: una tipografía poco común, una composición asimétrica, un color inesperado.
5. **Contenido real desde el primer bosquejo**; si falta, escribir contenido plausible y marcarlo como provisorio.
6. **Probar con las tres pruebas** (intercambio, borrado, pregunta) antes de mostrar.
7. **Lo común está permitido si se eligió.** Un héroe centrado puede ser la mejor solución para un caso; lo que se evita es usarlo por inercia.

## Nota sobre el control automático

Ningún script controla estas pautas: el aspecto no se mide. `scripts/revisar_diseno.py` solo verifica las reglas objetivas (ver `SKILL.md`).
