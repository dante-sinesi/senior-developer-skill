# Elicitación por lotes: aportar, no interrogar

Cómo pasar de una idea o un pedido a requisitos confiables cuando todavía no existen. El método está pensado para **gastar poco tiempo del usuario**: no hay un ida y vuelta de pregunta y respuesta. El modelo prepara **un documento con una batería de preguntas**, el usuario lo responde **en el mismo archivo**, y ese archivo queda como documentación. Complementa `requisitos.md` (cómo se escribe un requisito) y `senior-relevar` (cómo se entiende un sistema existente).

## Contenido
1. La idea central
2. Antes de preguntar
3. El ciclo por lotes
4. Cómo armar un buen lote
5. Aportar, no limitar
6. De las respuestas a `docs/requisitos/`
7. Cuándo parar
8. Validar y priorizar
9. Trampas frecuentes

## 1. La idea central

- **Un pedido no es todavía un requisito.** "Necesitamos reportes mensuales" es el comienzo de una conversación: falta saber para qué, para quién, con qué datos y qué se hace después. Escribirlo tal cual fija una solución sin haber entendido el problema.
- **Nunca de a una pregunta.** Preguntar de a una obliga al usuario a quedarse esperando y a contestar sin ver el panorama. Se agrupa todo lo que hay que saber en un **lote**.
- **El usuario responde cuando puede, en el archivo.** No hay que estar presente mientras el modelo trabaja, ni contestar todo, ni contestar en orden.
- **Lo respondido es documentación.** Cada lote queda en `docs/consultas/` y es el **origen** de los requisitos que de él salen.

## 2. Antes de preguntar

Todo lo que se pueda averiguar sin molestar al usuario, se averigua primero:
1. **Leer lo que ya existe:** documentos, planillas, formularios, capturas, correos pegados, el código si lo hay. Los archivos externos se convierten con `senior-relevar/scripts/convertir_fuentes.py` y las imágenes se leen directo.
2. **Inferir lo razonable.** Lo que un proyecto de este tipo casi siempre necesita no se pregunta: se **propone** como supuesto y el usuario corrige solo si no le sirve.
3. **Identificar quiénes importan:** quien usa, quien paga, quien opera, quien recibe resultados, quien audita. Cada uno ve algo distinto; si hay más de uno, el lote pregunta por cada uno.
4. **Anotar el vocabulario** del usuario y usarlo en las preguntas, no términos técnicos.

## 3. El ciclo por lotes

1. **Crear el lote:** `python <senior-docs>/scripts/consultas.py nueva "tema"` genera `docs/consultas/NN-tema.md` con la plantilla `plantillas/consulta.md`.
2. **Completarlo** con:
   - **Lo que entendí hasta ahora** (de 5 a 10 puntos, para que el usuario corrija lo que esté mal de un vistazo).
   - **Supuestos que usaré salvo que digas lo contrario.**
   - **Preguntas agrupadas por tema**, cada una con su propuesta (ver apartado 4).
3. **Entregarlo y avisar dónde está.** El usuario lo responde cuando pueda, escribiendo debajo de cada pregunta.
4. **Leer las respuestas** (`consultas.py estado` indica cuántas quedaron sin responder sin abrir el archivo) y actualizar los requisitos.
5. **Armar el lote siguiente solo con lo que falta**, relacionado con lo anterior o sobre un tema nuevo, y repetir.

Lo que quedó **sin responder no bloquea**: se avanza con la propuesta del modelo y el requisito resultante queda `provisorio` hasta que el usuario lo confirme.

## 4. Cómo armar un buen lote

- **Tamaño:** hasta unas 12 a 15 preguntas por lote, agrupadas por tema. Si hay más, se priorizan las que cambian el diseño y el resto va al lote siguiente.
- **Cada pregunta lleva:** por qué importa (qué decide), opciones cerradas cuando sea posible, y **una propuesta del modelo** para responder con un `ok`. Las abiertas son pocas y se piden con un ejemplo real ("cuéntame el último caso en que pasó").
- **Solo preguntas que cambian una decisión.** Si la respuesta no altera nada, no se pregunta.
- **Cubrir las dimensiones de una regla**, mezcladas en los temas, no como interrogatorio:

| Dimensión | Qué se quiere saber |
|---|---|
| Quién | Quién lo hace o lo pide; roles y permisos distintos |
| Cuándo | Momento, plazos, horarios, fechas límite |
| Por qué | Qué problema resuelve y qué pasa si no se hace |
| Cuánto | Cantidades, montos, volúmenes, máximos y mínimos |
| Condiciones | Siempre o solo a veces; qué cambia según el caso |
| Después | Qué sucede a continuación; quién se entera; si se puede deshacer |
| Errores y excepciones | Qué se hace hoy cuando falla algo o falta un dato |

- **Cerrar cada regla con valores concretos.** "Los socios con más de un año tienen descuento" se completa con cuánto, desde qué día exacto y qué pasa el día del aniversario. Esos casos límite son la tabla de **ejemplos verificables** del requisito y la materia prima de los tests (`senior-tdd`).
- **Dejar siempre un espacio libre** al final para lo que el usuario sepa y el modelo no haya preguntado.

## 5. Aportar, no limitar

La consulta es una ayuda, no un trámite:
- **Proponer antes de preguntar.** Cada pregunta trae una opción sugerida con su razón; el usuario solo corrige lo que no le sirve.
- **Poner sobre la mesa lo que el usuario no mencionó:** lo obvio que nadie dice (permisos, auditoría, qué pasa con los datos viejos, límites, idiomas), los riesgos y los huecos, con una sugerencia de cómo suele resolverse.
- **Ofrecer alternativas con sus consecuencias** cuando hay un cambio de rumbo posible, sin imponer ninguna.
- **Aceptar cualquier forma de respuesta:** un `ok`, una opción, una frase, un párrafo, un "no sé", un "decide tú". Un "no sé" se transforma en una propuesta provisoria, no en una nueva pregunta.
- **No retener el trabajo hasta tener todas las respuestas.** Con el primer lote ya se puede dejar un borrador de requisitos provisorios y, si el usuario quiere, empezar a diseñar o a probar ideas.

## 6. De las respuestas a `docs/requisitos/`

1. **Clasificar** cada respuesta en uno de los siete tipos (RN, RU, RD, RF, RNF, RT, RI) según `requisitos.md`.
2. **Redactar uno por archivo**, atómico y verificable, con `plantillas/requisito.md`. El **Origen** apunta a la consulta, por ejemplo `docs/consultas/01-reservas.md (P3)`, sin copiar el texto: se enlaza.
3. **Estado:** lo que el usuario respondió explícitamente pasa a `vigente`; lo que se tomó de una propuesta sin respuesta queda `provisorio`.
4. **Contradicciones:** si dos respuestas chocan (o chocan con un documento), no se elige en silencio: se muestran ambas versiones en el lote siguiente.
5. Correr `python <senior-docs>/scripts/revisar_requisitos.py` para detectar ambigüedad, falta de ejemplos y enlaces rotos antes de mostrar nada.
6. Lo que sigue abierto se anota en `docs/pendientes.md`.

## 7. Cuándo parar

Se deja de preguntar cuando:
- cada requisito tiene ejemplos con valores y origen, o está marcado como provisorio a propósito;
- no quedan preguntas que cambien el diseño;
- o el usuario dice que alcanza (se avanza con lo provisorio y se vuelve a preguntar solo si aparece un problema).

Como referencia, la mayoría de los temas se resuelven en **uno a tres lotes**. Si hace falta un cuarto, conviene mostrar primero el borrador de requisitos y preguntar qué falta.

## 8. Validar y priorizar

- **Validar** es comprobar que lo escrito es lo que el usuario necesita; **verificar** es comprobar que el sistema cumple lo escrito (los tests). Para validar se le presenta un resumen en sus palabras, no los archivos de requisitos.
- **Criterios de aceptación:** para cada requisito de usuario o funcional, una condición que permita decir "cumplido" o "no cumplido": son los mismos ejemplos verificables, en forma de caso (dado un contexto, cuando ocurre algo, entonces se espera tal resultado).
- **Priorizar con el usuario**, dentro de un lote si hace falta: imprescindible, importante, deseable o para después. Los imprescindibles definen la primera versión.
- **Cambios posteriores:** un requisito confirmado que cambia se registra con el motivo y la fecha; si deja de valer se marca `reemplazado por ID`.

## 9. Trampas frecuentes

- **Requisitos que chocan:** dos personas piden plazos distintos para lo mismo. Se resuelve con quien decide.
- **Una palabra, dos significados:** un estado como "listo" puede significar cosas distintas en dos áreas. Se fija el término en un requisito de dominio (RD).
- **Solución disfrazada de necesidad:** "necesitamos un botón que exporte" esconde el problema real; se pregunta para qué se usa el resultado.
- **Procedimiento formal contra práctica real:** lo que dice el manual y lo que se hace no coinciden. Se registran ambos y se pregunta cuál debe regir.
- **Ambigüedad:** "rápido", "fácil", "adecuado". Cada una se convierte en un número, en un caso o se descarta. Lo detecta `revisar_requisitos.py`.
- **El cuestionario eterno:** lotes largos o demasiados lotes cansan. Mejor pocas preguntas con propuesta que muchas abiertas.
