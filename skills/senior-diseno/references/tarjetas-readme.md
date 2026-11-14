# Tarjetas SVG para el README: tres estilos a partir de la descripción

Método para cuando un repositorio nuevo elige README **con tarjetas SVG** (`/inicializar-repositorio --readme tarjetas`). Es el mismo método de `senior-diseno` (briefing, tres alternativas que difieren en estructura, feedback, evolución) aplicado a una portada. **El paquete no trae ningún estilo:** lo inventa el diseñador para cada proyecto, y lo único fijo son las reglas objetivas que hace cumplir `senior-docs/scripts/readme_tarjetas.py`.

## 1. Briefing (de la descripción, sin preguntar de más)

De la descripción y lo que haya en la carpeta, sacar en pocas líneas: **qué es** el proyecto, **para quién** (público técnico, clientes, comunidad), **el tono** (serio, cálido, lúdico, técnico), **palabras e imágenes que evoca** (un horno, una red, un faro) y si el repositorio es **público o privado**. Si la descripción es demasiado pobre para elegir un tono, preguntar una sola cosa: cómo querría que se sintiera.

## 2. Tres estilos que difieren en estructura

No tres paletas del mismo diseño: tres **composiciones** distintas, cada una con su lógica de color y su decoración. El motor ofrece cuatro composiciones del texto (`izquierda`, `centrada`, `cartel`, `dividida`); lo demás es libre. Lo que cada estilo decide:

| Decisión | Qué es |
|---|---|
| Composición | Dónde va el texto: alineado a la izquierda, centrado, un cartel (título grande abajo y subtítulo arriba) o dividido (texto a un lado, una zona de ilustración al otro) |
| Colores | Fondo, título, texto, acento y, si hace falta, los de sellos y barras. Una lógica explicable («el color del horno», «papel y tinta»), no un adorno |
| Tipografía | Una familia del sistema (`Georgia, serif`, `'Arial Black', Impact, sans-serif`, `ui-monospace, monospace`) o una fuente `woff2` que el proyecto ya tenga y se incrusta; con `mayusculas` si el tono lo pide |
| Decoración | SVG libre antes (`fondo_svg`) y después (`frente_svg`) del texto: formas, patrones, marcos, ilustraciones geométricas que evoquen lo del briefing |

Los tres tienen que poder **distinguirse a simple vista** (por ejemplo: uno oscuro con una forma grande, uno claro con marco, uno de alto contraste con franjas), y cada uno se nombra con una palabra que diga su idea.

## 3. El tema (JSON)

```json
{
  "nombre": "Una palabra",
  "composicion": "izquierda | centrada | cartel | dividida",
  "alto": 300,
  "colores": {"fondo": "#rrggbb", "titulo": "#rrggbb", "texto": "#rrggbb", "acento": "#rrggbb",
              "sello_medido": "#rrggbb", "sello_esperado": "#rrggbb", "barra_antes": "#rrggbb", "barra_despues": "#rrggbb", "barra_vacia": "#rrggbb"},
  "tipografia": {"familia": "…", "peso_titulo": 700, "peso_texto": 400, "mayusculas": false},
  "sombra_titulo": "#rrggbb o ausente",
  "decoracion": {"fondo_svg": "<g>…</g>", "frente_svg": "<g>…</g>"},
  "fuentes": [{"archivo": "ruta/en/el/proyecto.woff2", "familia": "Nombre", "peso": 700}]
}
```
Este formato es solo la forma de los datos, no un estilo. Obligatorios: `fondo`, `titulo`, `texto` y `acento`; el resto tiene un valor por defecto derivado. El lienzo mide 760 px de ancho (el del README) y el alto va de 200 a 400.

## 4. Reglas objetivas (las comprueba el script; el aspecto no se toca)

- **Pie de foto:** toda tarjeta dice en una frase qué muestra; va en el `<desc>` del SVG, en el `alt` y debajo de la imagen.
- **Origen de las cifras:** toda tarjeta con cifras es `medido` o `esperado` y lleva su sello; una esperada lleva una nota que dice cómo se calculó, y nunca se mezclan las dos. Una cifra no se inventa ni se redondea a favor.
- **Una idea por tarjeta, sin saturar:** título hasta 40 caracteres, subtítulo hasta 90, un solo mensaje.
- **Contraste:** el texto contra el fondo de al menos 4,5 : 1 y el acento de al menos 3 : 1.
- **Decoración segura:** sin scripts, eventos, recursos externos ni `foreignObject`; cada SVG pesa menos de 200 KB.
- **Los SVG no se hacen a mano:** salen de los JSON de `docs/tarjetas/` con `readme_tarjetas.py generar`, y `verificar.py tarjetas` avisa si alguno quedó desactualizado o suelto.

## 5. Pasos

1. Escribir los tres temas en `.temporal/estilos/a.json`, `b.json` y `c.json` y la portada en `.temporal/estilos/portada.json` (`{"tipo": "portada", "titulo": …, "subtitulo": …, "pie": …}`, con el título del nombre del repositorio y el subtítulo de la descripción).
2. `python <senior-docs>/scripts/readme_tarjetas.py comparar --tarjeta .temporal/estilos/portada.json --estilos .temporal/estilos/a.json .temporal/estilos/b.json .temporal/estilos/c.json`: dibuja **la misma portada** con cada estilo y arma `comparar.html`.
3. Mostrarla con `python <senior>/scripts/abrir_en_navegador.py .temporal/estilos/comparar.html` (una sola pestaña) y **esperar la elección del usuario** (A, B o C, con o sin ajustes). Para comparar más tarjetas o pantallas a la vez, `ver_propuestas.py crear .temporal/estilos` arma un visor con todas las imágenes y SVG juntos. La mirada del usuario es parte del proceso y no se reemplaza con un chequeo: una decoración puede tapar el texto y el script no lo ve.
4. Evolucionar el elegido con el feedback (un cambio por vez) y volver a comparar si hace falta.
5. Pasarlo a `/inicializar-repositorio` con `--readme tarjetas --estilo .temporal/estilos/<el elegido>.json`. Queda guardado en `docs/tarjetas/estilo.json` y las tarjetas nuevas (cifras medidas o esperadas) se agregan después como JSON en `docs/tarjetas/`.

## Lo que no se hace

No se agregan estilos de ejemplo al paquete, no se usan fuentes ni imágenes de internet sin pedirlo, y no se elige el estilo por el usuario.
