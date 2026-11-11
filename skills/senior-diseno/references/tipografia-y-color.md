# Tipografía y color: lo objetivo

Esta referencia fija solo lo **objetivo**: la regla de tipografía del usuario, la legibilidad y el contraste. **Qué fuentes y qué colores se eligen es libre**: es parte del aspecto artístico y lo decide el diseñador para cada proyecto.

## Contenido
1. Regla de tipografía
2. Legibilidad
3. Contraste y color
4. Variables de diseño
5. Fuentes: de dónde salen

## 1. Regla de tipografía

**Una familia tipográfica es lo ideal; dos, el máximo, para toda la web** (no por pantalla: en todo el sitio). Controla `revisar_diseno.py tipografia`; con `--sitio` cuenta el conjunto de archivos.

- **Más de dos solo si el arte lo requiere al 100%.** Se justifica por escrito dentro del archivo con `<!-- excepcion-tipografia: motivo -->` y el script lo informa como JUSTIFICADA en lugar de FALLA. La decisión artística manda; lo que no se hace es sumar familias por inercia.
- Una familia en varios pesos y estilos cuenta como una sola; una fuente variable también.
- Una familia monoespaciada para datos o código cuenta como una de las dos.
- Las fuentes de íconos y las pilas genéricas de respaldo (`serif`, `sans-serif`) no cuentan.

## 2. Legibilidad

- **Texto de lectura:** 16 px como mínimo, líneas de 45 a 75 caracteres, interlineado de 1,4 a 1,6.
- **Elegir una escala y respetarla** da coherencia, pero cuántos tamaños se usan y cuáles es una decisión de diseño: no hay tope en la skill. `clamp()` permite escalar de forma fluida entre pantallas.
- **Objetivos táctiles** de al menos 44 px.

## 3. Contraste y color

- **Contraste obligatorio** (WCAG): 4,5 a 1 para texto normal; 3 a 1 para texto grande (desde 24 px, o 18,66 px en negrita) y para componentes de interfaz. `scripts/colores.py` y `revisar_diseno.py contraste` lo calculan.
- **Nada depende solo del color:** errores y estados también con texto o ícono.
- **Si el contraste falla, se corrige el par de colores afectado con el cambio mínimo**, sin repensar la paleta.
- La paleta, el acento, el modo oscuro y la identidad cromática son del diseñador.

## 4. Variables de diseño

Se declaran en `:root` y todo el CSS las usa; no hay valores sueltos. Nombres por rol, valores libres:

```css
:root {
  --c-fondo: ...;   --c-texto: ...;   --c-acento: ...;
  --f-titulo: ...;  --f-texto: ...;
  --t-1: ...;  --t-2: ...;  --e-1: ...;  --e-2: ...;
}
```

Plantilla en `plantillas/tokens.css` (nombres de ejemplo). Ver `sistema-de-diseno.md`.

## 5. Fuentes: de dónde salen

- Las que ya trae el sistema no necesitan nada externo (varían según el sistema operativo; cada pila termina en una genérica).
- **Fuentes web:** consultar al usuario antes de cargarlas desde un servicio externo (cada petición revela la visita a un tercero). Alojarlas junto al proyecto lo evita. Usar `font-display: swap`.
