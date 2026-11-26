# Brief para un agente delegado (en lugar del método completo)

Cuando se lanza un subagente que escribe o modifica código, no se le pide que «trabaje como senior»: arrancaría con el contexto vacío y pagaría el método entero para un cambio chico. Se le pasa este brief en el prompt (unas diez líneas) junto con la tarea y la regla de negocio:

```
Trabajá así:
- Antes de editar, leé docs/ESTADO.md y <documentos afectados>. Lo que cambie respecto de ellos, actualizá en el mismo cambio (<documentos>).
- Si cambia el comportamiento, escribí primero el test desde la regla que te paso y comprobá que falla antes de implementar.
- Cambio mínimo: solo lo pedido, sin refactor, opciones ni abstracciones nuevas.
- No hagas commit, push ni Pull Request; no toques .env ni escribas fuera de este directorio.
- Al terminar devolvé, en 10 líneas como máximo: qué archivos cambiaste, qué test agregaste, qué documentación actualizaste, cómo lo verificaste y qué no pudiste comprobar.
```

Notas (documentación de subagentes de Claude Code):
- Un subagente **no hereda** lo que el agente principal ya cargó ni las skills ya invocadas; sí puede descubrir y usar las skills instaladas con la herramienta `Skill`. Por eso conviene el brief en el prompt.
- Un subagente de tarea **mecánica** (buscar, listar, resumir, convertir) no necesita ningún método: se le quita la herramienta `Skill` (`disallowedTools: Skill`) para que no cargue `senior` por su cuenta y pague de más.
- Lanzar agentes en paralelo sigue siendo un punto de control: se explica el costo en tokens y se pide el visto bueno del usuario.
