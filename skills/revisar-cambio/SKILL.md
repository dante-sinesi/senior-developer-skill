---
name: revisar-cambio
description: Revisión de un cambio (diff sin commit, rama o Pull Request) con el rigor de quien recibe la llamada si se rompe en producción: errores, riesgos, escala, tests que faltan, reglas de negocio, velocidad y lo que sobra. Cada hallazgo trae un caso concreto, el arreglo mínimo y qué pasa si se omite; sin caso concreto no hay hallazgo. Usar cuando el usuario escriba /revisar-cambio o pida revisar, dar el visto bueno o auditar un cambio, un diff, una rama o un Pull Request, o pregunte si algo está listo para subir. Solo informa: no modifica código.
---

# Revisar un cambio

Se revisa como lo haría la persona senior a la que llaman cuando algo se rompe. Orden de importancia: **correcto, seguro, aguanta la carga, probado, rápido, sin sobrantes**. Lo que sobra importa: cada línea de más hay que leerla, probarla y corregirla después.

Es un informe que el usuario pidió, así que se entrega completo. **No cambia código**; commits, push y Pull Requests siguen necesitando su aprobación.

## 1. Entender primero

1. **Armar el expediente con el script**, que ahorra la parte mecánica: `python <esta-skill>/scripts/contexto.py [sin-guardar | preparado | rama | pr <número> | <archivos>]`. Sin objetivo revisa los cambios sin commit y, si no hay, el último commit. Devuelve los archivos tocados, los símbolos modificados con quién los usa fuera de su archivo, si hay tests y documentación, señales de riesgo en las líneas nuevas y pistas de la carga esperada.
2. **Leer el diff y después el código que toca:** los llamadores de cada función cambiada, las funciones que llama, los tests y el README. Para un símbolo en particular: `python <senior>/scripts/impacto.py <símbolo>`.
3. **Trazar el flujo real:** por dónde entran los datos, qué se guarda, qué sale.
4. **Un cambio puede romper código que no toca.** Si cambia una firma, un valor de retorno o un comportamiento, se buscan todos los llamadores.
5. **Averiguar la carga esperada** (README, despliegue): una persona corriendo un script, o muchos usuarios y procesos a la vez. La escala se juzga contra eso, y se dice qué carga se asumió.

## 2. Qué buscar

1. **Error:** resultado equivocado, cierre inesperado, caso límite sin cubrir (vacío, cero, último elemento, redondeo, zonas horarias), un llamador roto por el cambio, o un arreglo aplicado en un llamador mientras la función compartida sigue mal.
2. **Riesgo:** fallas de seguridad (inyección, aleatoriedad débil, secretos, entradas del usuario sin validar; ver `senior-seguridad`) y pérdida de datos (errores tragados, escrituras en mal orden, falta de transacción).
3. **Escala:** bien para una persona y mal para muchas: condiciones de carrera entre leer y escribir, el mismo trabajo repetido en cada proceso, memoria o listas que solo crecen, una consulta por elemento, O(n²) sobre entradas grandes, estado por proceso que debería compartirse.
4. **Test que falta:** lógica nueva con riesgo (una rama, un analizador, dinero, seguridad, escrituras de datos, una corrección de error) sin un test que falle cuando se rompe. Un buen test, no cobertura. El test sale de la regla de negocio (`senior-tdd`).
5. **Regla de negocio:** el cambio contradice un requisito documentado, o el comportamiento nuevo no está respaldado por ninguno (`docs/requisitos/`).
6. **Velocidad:** las lentitudes grandes son problemas; las mejoras chicas, sugerencias.
7. **Sobrante:** lo que no debería existir o debería ser más chico:
   - borrar: código muerto, opciones sin uso, funciones especulativas;
   - reusar: el proyecto ya tiene esa función (nombrar la ruta; `impacto.py --existe <palabras>` ayuda);
   - estándar o plataforma: la biblioteca estándar ya lo hace, o una dependencia nueva para pocas líneas;
   - una abstracción con una sola implementación, o configuración que nadie usa;
   - fusionar copias casi iguales que deben cambiar juntas;
   - dividir una función que hace trabajos sin relación, por trabajo y nunca por cantidad de líneas.
8. **Documentación:** README, requisitos y diagramas afectados sin actualizar.
9. **Control aflojado:** el cambio baja un umbral, saltea o borra un test, quita verificaciones o silencia un chequeo (`# noqa`, `@ts-ignore`) para pasar en verde. Correr `python <senior>/scripts/guardia_listones.py --base <rama-base>` y confirmar cada aviso; sin `motivo:` escrito es un hallazgo.

## 3. Comprobar antes de informar

- **Todo hallazgo lleva un caso concreto:** «con esta entrada o en esta situación pasa este resultado equivocado». Sin caso, no hay hallazgo.
- Releer las líneas y confirmar: el llamador existe, el valor realmente puede venir vacío, el código realmente no se usa.
- Un atajo marcado con `atajo: <límite>; cuándo: <disparador>` es una decisión, no un hallazgo, salvo que la carga esperada ya cruce ese límite.
- Proponer el arreglo más chico que funcione, mejor si borra código. Nunca agregar capas, bibliotecas ni configuración que el problema no pida.
- Nada de gustos de estilo, de «podría considerarse» ni de preocupaciones vagas.

## 4. Salida

Lenguaje simple: oraciones cortas, palabras de todos los días y cada término técnico explicado la primera vez. Quien lee puede no haber visto nunca este código.

Empezar con `Qué hace este cambio:` en dos o tres oraciones. Después los hallazgos en tres grupos (se omiten los vacíos):
- **Corregir antes de subir:** error, seguridad, pérdida de datos, o algo que se rompe con la carga esperada.
- **Conviene corregir:** código riesgoso sin test, lentitud real, duplicación, una función que mezcla trabajos, código que no debería existir, documentación desactualizada.
- **Opcional:** mejoras chicas de velocidad o de forma.

**Los hallazgos se numeran de corrido en todos los grupos**, para que el usuario pueda decir «arreglá el 2 y el 5». Cada uno tiene las cuatro partes, en una o dos oraciones cortas:

2. **El cierre mensual cuenta dos veces los pedidos anulados** (`facturacion/cierre.py:L40-52`)
   - **Qué es:** el último día del mes suma los pedidos del período para facturarlos.
   - **Problema:** toma los pedidos por fecha de creación y no excluye los anulados; un pedido anulado el día 31 entra dos veces, en el cierre de ese mes y en el siguiente.
   - **Arreglo:** filtrar `estado != "anulado"` en la consulta compartida `pedidos_del_periodo`; una línea, nada más cambia.
   - **Si se omite:** se factura de más y contabilidad lo corrige a mano cada mes.

Cerrar con:
- `Veredicto: se puede subir.` o `Veredicto: corregir primero el 1 y el 3.`
- `Sobrante: -N líneas posibles.`, si hay hallazgos de sobrante.
- `Sin revisar:` una línea, si algo importaba y no se pudo comprobar.

Si no hay hallazgos: `Qué hace este cambio:`, luego `Sin hallazgos. Se puede subir.` y una línea sobre qué se revisó.

## Límites

- Solo lista hallazgos; no corrige. Si el usuario pide arreglar alguno, se hace con el flujo normal de `senior` (test primero, rama, commits con su aprobación).
- El expediente es heurístico: marca qué mirar, no da veredictos.
