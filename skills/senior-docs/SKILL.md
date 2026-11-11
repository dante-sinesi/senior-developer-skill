---
name: senior-docs
description: Documentación viva en el repositorio (docs/) con requisitos de negocio, de usuario, de dominio, funcionales, no funcionales, de transición y de interfaces externas, más diagramas Mermaid legibles (clases, secuencia, entidad-relación, estados), decisiones de arquitectura (ADR) y trazabilidad requisito-test-código. Usar al crear la base documental de un proyecto, al agregar o cambiar un requisito, al dibujar un diagrama UML o de secuencia, al registrar una decisión de arquitectura, o cuando falte documentación clara. Usar también para elicitar requisitos de una idea o un pedido nuevo (consultas por lotes que el usuario responde en un Markdown) y para revisar la calidad de los requisitos escritos. Usar también cuando un cambio afecte comportamiento y haya que actualizar lo documentado.
---

# Documentación viva

La documentación sirve si se puede leer, encontrar y confiar en ella. Por eso: vive en el repositorio, tiene IDs, está indexada, se actualiza con cada cambio y sus diagramas son pequeños y legibles.

## README del repositorio (siempre al día)

El `README.md` de la raíz es lo primero que ve cualquiera en GitHub. Contiene: qué es, requisitos, instalación, uso, pruebas, estructura del proyecto (una línea por carpeta de primer nivel) y enlace a `docs/INDEX.md`. Se crea con `plantillas/readme.md` y **se revisa y actualiza en cada cambio**, sin excepción: se reescribe la parte afectada y no se agregan registros de cambios (eso es del PR y de git). Lo exige `verificar.py readme`.

## Completa no es redundante

Cada dato vive en **un solo lugar** (regla → requisito, decisión → ADR, estado → ESTADO.md, pasos → ficha, contrato externo → requisito RI) y el resto enlaza con `[[ID]]`. Cada tipo de documento tiene un límite de extensión; cuando se excede, el contenido se **divide o se mueve, nunca se recorta**. Tabla de destinos y procedimiento en `senior/references/comentarios-y-texto.md`; lo vigila `verificar.py texto`.

## Línea base y mantenimiento

- **Línea base** (una vez por proyecto): crear `docs/` y documentar lo esencial de los siete tipos de requisitos. Para un proyecto heredado se construye de forma incremental junto con el relevamiento, no de golpe.
- **Por cada cambio**: actualizar solo lo afectado (requisitos tocados, diagramas afectados, ADR si hubo una decisión). Un cambio de una línea no arrastra los siete tipos.
- **Estructura inicial**: `python <esta-skill>/scripts/iniciar_docs.py` crea las carpetas y archivos base sin pisar nada existente.

## Los siete tipos de requisitos

| Tipo | Prefijo | Carpeta | Responde a |
|---|---|---|---|
| Negocio | RN | `docs/requisitos/negocio/` | Reglas y objetivos del negocio (ej. descuento del 20% sobre 10 unidades) |
| Usuario | RU | `docs/requisitos/usuario/` | Qué necesita lograr cada tipo de usuario |
| Dominio | RD | `docs/requisitos/dominio/` | Conceptos, entidades y restricciones del dominio |
| Funcional | RF | `docs/requisitos/funcional/` | Qué debe hacer el sistema |
| No funcional | RNF | `docs/requisitos/no-funcional/` | Rendimiento, seguridad, disponibilidad, usabilidad |
| Transición | RT | `docs/requisitos/transicion/` | Migración de datos, puesta en marcha, capacitación |
| Interfaces externas | RI | `docs/requisitos/interfaces/` | APIs, archivos y sistemas con los que se conecta |

Detalle, ejemplos y cómo extraer reglas de código heredado: `references/requisitos.md`.

**Cuando los requisitos no existen todavía** (una idea nueva, un pedido vago, alguien que no sabe qué pedir): se elicitan **por lotes, no pregunta a pregunta**. El modelo prepara un archivo `docs/consultas/NN-tema.md` con lo que entendió, los supuestos y una batería de preguntas agrupadas, cada una con su propuesta; el usuario responde en el mismo archivo cuando pueda (con un `ok` alcanza), y eso queda como documentación y como origen de los requisitos. Lo que no se responde no bloquea: se avanza con la propuesta y el requisito queda provisorio. Si el pedido es vago y el usuario está presente, una **entrevista corta con hipótesis** (una pregunta a la vez, cada una con su suposición; la intención se reformula y solo un sí explícito la confirma: «dale, lo que te parezca» no cuenta) es más rápida que un lote: apartado 10 del método. Método completo en `references/elicitacion.md`; el archivo se crea con `python <esta-skill>/scripts/consultas.py nueva "tema"` y `consultas.py estado` resume qué quedó sin responder.

**Revisión de la forma:** `python <esta-skill>/scripts/revisar_requisitos.py` (también como `verificar.py requisitos`) controla, sin gastar tokens, el encabezado, los IDs, los enlaces `[[ID]]`, los ejemplos verificables, las palabras ambiguas («rápido», «fácil», «etc.»), el estado y el origen. No juzga si el requisito es correcto ni detecta contradicciones: eso se decide con el usuario. Se corre antes de mostrar requisitos nuevos.

Reglas de oro:
- **Un archivo por requisito**, con su ID (`RN-001.md`) y el encabezado de la plantilla `plantillas/requisito.md`.
- Los requisitos de negocio llevan **ejemplos con valores concretos** (entrada → resultado esperado). De ahí salen los tests (`senior-tdd`).
- **Nunca se infiere una regla de negocio mirando qué hace el código**: se pregunta al usuario. El código puede estar equivocado.
- Los requisitos de seguridad se registran como RNF con la etiqueta `iso:` del control correspondiente (ver `senior-seguridad`). Los controles de políticas, personas o seguridad física que el código no resuelve se registran como RNF o RT, sin pretender cubrirlos.

## Diagramas (Mermaid, legibles)

Un diagrama que existe pero no se entiende no sirve. Reglas completas y ejemplos en `references/diagramas.md`. Resumen:

- **Una pregunta por diagrama**, escrita en su título y en una línea de descripción.
- **Límites de tamaño**: clases hasta 10 (con pocos miembros), secuencia hasta 8 participantes y 20 mensajes, flujo o estados hasta 15 nodos, entidad-relación hasta 10 entidades.
- **Si no entra, se divide**: un diagrama general con pocas piezas que enlaza a diagramas de detalle por caso de uso.
- **Se verifica con script**: `python <ruta-de-senior>/scripts/diagramas.py` antes de dar un diagrama por bueno. Si excede, se divide.
- Cualquier cambio que cruce capas (por ejemplo interfaz, servidor y base de datos) lleva antes un diagrama de secuencia; las notas citan el ID de la regla (`Note over X: RN-004`).
- Los cambios a diagramas de arquitectura se muestran como **diff antes/después y esperan aprobación** del usuario antes de escribirse.

## Decisiones de arquitectura (ADR)

Para decisiones importantes y difíciles de revertir: `docs/decisiones/ADR-001.md` con la plantilla `plantillas/adr.md` (contexto, decisión, alternativas, consecuencias). Evita rediscutir lo ya decidido.

## Cuando se diseña una interfaz

Las decisiones de diseño viven en `docs/diseno/notas/decisiones.md` (IDs `D-001`…), que mantiene `senior-diseno`. Los ADR las **citan** por ID, sin copiarlas. Los requisitos de usabilidad y accesibilidad se documentan aquí como requisitos no funcionales.

## Trazabilidad

Cada test cita el ID del requisito que verifica (en un comentario o nombre). `senior-memoria/scripts/indexar_docs.py` arma la matriz requisito → test → código y marca requisitos sin test e IDs sin documento. Regenerar el índice tras cambiar documentación.
