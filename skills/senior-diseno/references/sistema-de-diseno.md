# Sistema de diseño: sostenible y escalable

Prioridad del usuario: lo que se diseña tiene que **sostenerse y crecer**. Si se diseña diez veces el mismo botón y quedan diez botones iguales en diez lugares, cada cambio se multiplica por diez y la interfaz termina incoherente. El diseñador es dueño del **sistema de diseño**; quien implementa lo programa una sola vez.

## Contenido
1. Variables de diseño
2. Inventario de componentes
3. Regla: no hay componente nuevo sin justificarlo
4. Cómo se verifica
5. Del diseño al código

## 1. Variables de diseño

Colores, tipografías, tamaños, espacios, duraciones y curvas se definen **una sola vez** como variables CSS en `docs/diseno/sistema/tokens.css`, con nombres por rol (no por valor): `--c-acento`, no `--c-naranja`. El CSS usa solo variables: nada de valores sueltos.

- **Espaciado** con una escala corta (por ejemplo 4, 8, 16, 24, 40), no con números arbitrarios.
- **Tipografía** con cinco tamaños como máximo.
- **Color** por roles; los estados (éxito, error) también son roles.

## 2. Inventario de componentes

`docs/diseno/sistema/inventario-componentes.md`: cada componente con sus **variantes** (principal, secundario, peligro), sus **estados** (reposo, hover, foco, presionado, deshabilitado, cargando) y **dónde se usa**. Un botón se define una vez; una variante es una modificación declarada, no un botón nuevo.

## 3. Regla: no hay componente nuevo sin justificarlo

Antes de diseñar algo, se busca en el inventario:
1. ¿Ya existe un componente que sirve? Se usa.
2. ¿Sirve con una variante? Se agrega la variante al mismo componente.
3. ¿De verdad es otra cosa? Se registra el componente nuevo, con el motivo de por qué no servía ninguno existente.

Esto es un problema de **diseño** antes que de código: nadie le preguntaría a quien programa si dos botones son el mismo.

## 4. Cómo se verifica

`scripts/revisar_diseno.py sistema` marca:
- ausencia de variables de diseño,
- colores y espacios sueltos fuera de las variables,
- estilos en línea (`style="…"`), que saltean las variables,
- **dos definiciones casi idénticas** del mismo componente (por ejemplo `.btn-a` y `.btn-b`).

Es una heurística: una marca pide decidir si es el mismo componente o no.

## 5. Del diseño al código

El sistema de diseño se define en `docs/diseno/sistema/` y el código lo respeta:

| | En el diseño | En el código (senior) |
|---|---|---|
| Variables de diseño | Se definen y mantienen en `tokens.css` | Se usan; no se copian los valores |
| Componentes | Se inventarían con variantes y estados | Se implementan **una sola vez** y se reutilizan |
| Duplicación | La detecta este chequeo en el diseño | La detecta `duplicados.py` en el código, y se refactoriza |
| Etiquetas de formularios | Se fijan en el contrato de campos | Se implementan tal cual |
| Cambios | Se decide el componente o la variante | Si hace falta uno nuevo, se diseña primero y se agrega al inventario |
