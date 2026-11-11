# Colaboración con un diseñador (protocolo v1)

Esta skill funciona sola. Si el proyecto tiene un rol de diseño (por ejemplo, la skill `disenador-frontend`), se coordinan por archivos con este protocolo. Es la única parte que comparten; cada skill puede cambiar su interior sin avisar.

## Contenido
1. Reparto de carpetas
2. Al empezar
3. Al implementar
4. Pedidos al diseñador
5. Documentar las decisiones
6. Una sesión por rol o un chat que alterna
7. Cuándo recomendar dividir el trabajo
8. Protocolo v1

## 1. Reparto de carpetas

- `diseno/` es **exclusiva del diseñador**: producción no escribe ahí.
- Todo lo demás (raíz, código, `docs/`, README) es de **producción**.
- **Ambos leen todo.** Producción lee `diseno/` para implementar; el diseñador lee el esquema, los requisitos y el código para saber qué proponer.

## 2. Al empezar

1. Leer `diseno/ENTREGA.md` (versión, decisiones con ID, pendientes, lo que debe respetarse).
2. Leer `diseno/sistema/tokens.css`, `diseno/sistema/inventario-componentes.md` y los contratos de `diseno/campos/`.
3. Ejecutar `python <esta-skill>/scripts/verificar.py diseno` para ver el estado de la entrega y las solicitudes abiertas. Sin `ENTREGA.md` no se implementa: se pide al diseñador.

## 3. Al implementar

- **Variables de diseño:** se usan con `var(--…)`; no se copian los valores (`verificar.py diseno` lo marca).
- **Componentes:** cada uno se implementa **una sola vez** y se reutiliza; una variante es una modificación declarada del mismo componente, no un componente nuevo. El detector de duplicados (`senior-refactor`) cubre el código; el inventario del diseñador cubre el diseño.
- **Etiquetas de formularios:** exactamente como figuran en el contrato de campos, sin reescribirlas ni "mejorarlas".
- **Estados y movimiento:** hover, foco visible, presionado, deshabilitado, cargando, éxito y error; transiciones breves; respetar `prefers-reduced-motion`.
- Si el diseño no cubre un caso, **no se inventa**: se pide.

## 4. Pedidos al diseñador

Producción no escribe en `diseno/`. Los pedidos y preguntas se dejan en `docs/solicitudes-de-diseno.md` (plantilla en `senior-docs/plantillas/solicitud-de-diseno.md`), con ID `S-001`… y `Estado: abierta`. El diseñador los responde en `diseno/ENTREGA.md` y los marca como respondidos.

`verificar.py fronteras` falla si producción tiene cambios sin guardar dentro de `diseno/` (con el rol marcado como `produccion`).

## 5. Documentar las decisiones

Las decisiones técnicas van en un ADR (`senior-docs`) que **cita** las decisiones de diseño por su ID (`D-001`) en lugar de copiarlas: "Se implementa la dirección B (ver D-003) con estos componentes…". Un dato, un lugar.

## 6. Una sesión por rol o un chat que alterna

- **Una sesión por rol** (proyectos medianos y grandes): una sesión de producción en la raíz del proyecto, con el marcador `produccion`, y otra de diseño abierta dentro de `diseno/`. Las sesiones no comparten la conversación; por eso todo va en `ENTREGA.md`, en las solicitudes y en `docs/`.
- **Un chat que alterna** (proyectos chicos): se cambia el rol con `python <esta-skill>/scripts/hook_aislamiento.py rol produccion|diseno|ninguno`.
- **Hook de aislamiento** (opcional, **con aprobación del usuario**): `hook_aislamiento.py configuracion` imprime el bloque para `.claude/settings.json`. Bloquea las escrituras fuera de la carpeta del rol. Controla `Write` y `Edit` con precisión y los comandos de terminal de forma aproximada.

## 7. Cuándo recomendar dividir el trabajo

**Cada vez que el usuario proponga un cambio grande**, recomendar dividir el trabajo en dos sesiones (diseño y producción) y remarcar que **podría ser importante para la estabilidad del proyecto**: se mantienen separados el contexto y los cambios, y las entregas son verificables. El usuario decide. No se repite en cada mensaje, solo ante cada cambio grande.

Señales: 5 o más pantallas, 8 o más componentes distintos, más de una ronda de diseño, varios módulos, un rediseño completo o un cambio clasificado como "grande" por `verificar.py tamano`. En proyectos chicos se propone alternar de rol.

Texto sugerido: "Este cambio es grande. Te recomiendo dividir el trabajo en dos sesiones, una de diseño y otra de producción: podría ser importante para la estabilidad del proyecto, porque mantiene separados el contexto y los cambios. Te dejo la entrega escrita. ¿Lo hacemos así?"

## 8. Protocolo v1

| Elemento | Convención |
|---|---|
| Carpeta del diseñador | `diseno/` (en la raíz del proyecto) |
| Entrega | `diseno/ENTREGA.md`, con `Versión` y `Fecha` |
| Decisiones de diseño | `D-001`, `D-002`… (en `ENTREGA.md`) |
| Solicitudes de producción | `docs/solicitudes-de-diseno.md`, IDs `S-001`… y `Estado: abierta` o `respondida` |
| Contrato de campos | `diseno/campos/<formulario>.md`, tabla con la columna `Etiqueta final` |
| Variables y componentes | `diseno/sistema/tokens.css` y `inventario-componentes.md` |
| Marcador de rol | `.claude/rol-activo` con `diseno` o `produccion` |
| Preferencias | `diseno/notas/preferencias.md` |
