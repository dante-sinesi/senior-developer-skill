# Plan no simple: revisión a ciegas con el pez

Antes de ejecutar un plan que importa, un revisor que **solo recibe el `.md` del plan** intenta romperlo. Después de una sesión larga las suposiciones se vuelven hechos y quien escribió el plan ya no las ve; un lector sin contexto sí. Es el hermano de `duda.md` (que interroga una decisión o un cambio de código): el pez interroga un plan.

## Cuándo

Un plan es **no simple** si cumple al menos una de estas:
- toca varias áreas o más de unos cinco archivos;
- incluye algo irreversible o que sale del proyecto (borrar, migrar datos, publicar, rotar credenciales, mover dinero);
- introduce una mecánica nueva o cambia una regla del método;
- cruza más de una sesión o depende de otras personas;
- el usuario lo pide.

**No se usa** en un cambio chico, en trabajo mecánico ni cuando el usuario ya dio una instrucción clara y acotada.

## Cómo

1. **Redactar el plan** en un `.md` que se baste solo (`.temporal/planes/<tema>.md`; si vale conservarlo, pasa luego a `docs/`) con estas secciones:
   `## Contexto`, `## Decisiones ya tomadas (no reabrir)`, `## Pasos`, `## Qué pasa si falla`, `## Terminado cuando`.
   El revisor no sabe nada más: todo lo que necesita está en el plan, y lo ya resuelto va en «Decisiones ya tomadas» para que no lo reabra.
   `python <esta-skill>/scripts/pez.py validar <plan.md>` comprueba que las secciones estén.
2. **Pedir la revisión:** `python <esta-skill>/scripts/pez.py revisar <plan.md>`. Corre un pez en una sesión nueva de `claude -p` sin herramientas, sin skills ni configuración del proyecto, solo con el plan, y deja un resumen: veredicto, puntaje y hallazgos con su caso concreto y su arreglo. Sin CLI de Claude, `pez.py pedir` imprime el pedido para pasárselo a un subagente (menos aislado: puede leer el proyecto).
3. **Decidir cada hallazgo:** se anota en una sección `## Registro de revisión` del plan como **aceptado** (cambia el plan) o **rechazado** (con el motivo). Un hallazgo que se ignora en silencio es la falla de este método. Los que se discuten los decide el usuario.
4. **Cortar o repetir:** `python <esta-skill>/scripts/pez.py decidir <veredicto de cada ronda>`:
   - «pasa» o «corregir»: se sigue. Un plan bueno suele recibir «corregir»: los cambios son acotados y no piden otra ronda.
   - «bloquea» en la primera ronda: se corrige y se revisa de nuevo.
   - «bloquea» en la segunda: no hay tercera ronda; se le plantea al usuario qué se decide.
5. **Ejecutar solo con la aprobación del usuario** sobre el plan final.

## Qué se midió

Con agentes reales, 6 planes (3 con fallas sembradas y 3 que parecían sanos), 2 repeticiones: un revisor general halló 23 de las 24 fallas sembradas, a unos 0,03 USD por plan. Además encontró defectos que nadie había sembrado en los planes «sanos» (probar con clientes externos en un entorno interno, comparar código viejo y nuevo cuando el viejo ya no existe, un duplicado si el trabajador cae tras aceptar el proveedor). **Tres revisores con foco distinto** hallaron 24 de 24, por tres veces el costo y con mucho solapamiento: no hubo ventaja medible y se descartaron. En esa prueba ningún revisor dijo «pasa» ni una vez: «corregir» es el veredicto normal.

## Límites y señales de mal uso

- Es una ayuda para no ejecutar a ciegas, no una garantía: pocas pruebas, un solo modelo, y el revisor puede marcar preferencias como fallas (cerca de un tercio de los hallazgos medidos).
- El revisor ve el nombre de la carpeta de trabajo, no el contenido del proyecto.
- **Mal uso:** pasar un plan trivial por el pez; repetir rondas hasta que diga «pasa»; aceptar todo lo que dice sin mirarlo contra el plan; plan que no se basta solo.
