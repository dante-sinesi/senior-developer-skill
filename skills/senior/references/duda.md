# Duda con contexto fresco

Interrogar una decisión importante **antes** de darla por buena, con un revisor que no vio la conversación. Después de una sesión larga las suposiciones se vuelven hechos, y la seguridad de quien escribió el código no es evidencia de que esté bien. Complementa a `/revisar-cambio`: esa revisa lo ya terminado; esta actúa mientras corregir todavía sale barato.

## Cuándo

Una decisión es no trivial si cumple al menos una de estas:
- agrega o cambia lógica con ramas;
- cruza el límite de un módulo o un servicio;
- afirma algo que el compilador no verifica (que algo es idempotente, seguro entre hilos, que conserva un orden o un invariante);
- depende de un contexto que quien lea después no va a ver;
- tiene un efecto difícil de deshacer: un despliegue, una migración de datos, un cambio de interfaz pública.

Se usa antes de commitear código así, antes de afirmar un hecho que no es obvio, al decidir una arquitectura con incertidumbre y al trabajar en código que no se conoce.

**No se usa** en trabajo mecánico (renombres, formato, mover archivos), cuando el usuario dio una instrucción clara, al leer código, en cambios de una línea, ni si el usuario pidió rapidez por sobre la verificación.

## Los cinco pasos

1. **Afirmar.** Escribir la decisión en dos o tres líneas y por qué importa. Si no cabe, todavía es una intuición y no una decisión.
2. **Extraer.** Aislar lo mínimo revisable: el diff o la función, o la propuesta con sus restricciones. Se conserva la evidencia (un llamador, una guarda, un test que contradiga la afirmación) y se quita el razonamiento.
3. **Dudar.** Lanzar un subagente nuevo con el texto que arma `python <esta-skill>/scripts/duda.py armar --artefacto <rutas> --contrato <texto o ruta>`. Lleva **solo el artefacto y el contrato**: nunca la afirmación ni el razonamiento del autor, porque un revisor que sabe qué se quiere probar tiende a coincidir. El texto de instrucciones se pega tal cual: un revisor con rol propio (como `/revisar-cambio`) da veredictos equilibrados por diseño y desactivaría la actitud adversarial. Se usa un subagente genérico.
4. **Reconciliar.** El resultado del revisor es un dato, no un veredicto. Se vuelve a leer el artefacto frente a cada hallazgo y se clasifica con la primera clase que corresponda:
   1. `contrato`: el revisor se confundió por un contrato poco claro; se aclara el contrato y se repite.
   2. `accionable`: válido y arreglable; se cambia el artefacto y se repite.
   3. `compromiso`: válido, pero arreglarlo cuesta más que aceptarlo; se documenta para el usuario.
   4. `ruido`: incorrecto por un contexto que el revisor no tenía; se anota, y se evalúa si conviene sumar ese contexto al contrato.
   5. `trivial`: menor o ya considerado.
5. **Parar.** `python <esta-skill>/scripts/duda.py decidir "accionable,ruido" "ruido" …` (un argumento por ciclo) dice qué sigue: corregir y repetir, aclarar el contrato, parar o escalar.

## Cuándo se frena

- El último ciclo no trae nada sustantivo: la decisión aguanta.
- **Tres ciclos** y todavía hay hallazgos sustantivos: se le plantea al usuario en vez de seguir solo. Si el artefacto es tan grande que tres ciclos no alcanzan, se divide, no se amplía el límite.
- **Teatro de duda:** dos ciclos seguidos con hallazgos y ninguno accionable. Significa que se está validando, no dudando: se frena y se le plantea al usuario.
- El usuario dice que se siga.

## Señales de que se hace mal

- Dudar de cambios triviales, o pedir «¿está bien?» en lugar de «busca cómo falla».
- Aceptar lo que dice el revisor sin volver a leer el artefacto.
- Repetir el ciclo sobre un artefacto que no cambió.
- Dudar después de commitear: eso ya es una revisión final (`/revisar-cambio`).
- Pasarle al revisor la afirmación o quitarle el contrato.

## Límites

- Todo queda dentro de la sesión de Claude: **no se invocan herramientas de otros modelos ni servicios externos** para pedir una segunda opinión sin que el usuario lo autorice de forma explícita, y esa autorización vale para esa vez.
- Un subagente no puede lanzar otro: dentro de uno, el camino es escalar al usuario. Una autocrítica sin contexto fresco es una versión degradada y se declara como tal.
- Quien duda es la sesión principal: un revisor no lanza a otro revisor.
