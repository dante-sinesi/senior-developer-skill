---
name: senior-refactor
description: Refactor sistemático y seguro: detectar código repetido, decidir qué extraer y hacerlo en pasos pequeños con los tests en verde, sin mezclarlo con funcionalidades nuevas. Usar después de poner un test en verde, al notar código muy parecido repetido varias veces, al pedir limpiar, simplificar, reducir duplicación u ordenar código, o antes de ampliar una zona del sistema con mucha repetición.
---

# Refactor

El código repetido no falla hoy: falla el día que hay que cambiar una de las copias y se olvida otra. El refactor es la fase del ciclo (rojo, verde, **refactor**) que lo evita, pero solo es seguro con una red de tests.

## Antes de escribir algo nuevo

El mejor refactor es el que no hace falta: antes de crear una función o un componente, se busca si el proyecto ya tiene algo parecido para reusar (ver «la escalera» en `senior`; `impacto.py <nombre>` de Token Diet para un nombre exacto).

## Reglas

1. **Tests en verde antes de empezar.** Sin tests, primero se escriben los de caracterización (`senior-tdd`). Un refactor sin red es una apuesta.
2. **Un paso, un commit.** Cada extracción o renombre es un paso pequeño, con los tests corridos al terminar y un commit propio de tipo `refactor:`.
3. **Nunca mezclado con funcionalidad.** Si hace falta cambiar comportamiento, es otro paso con su propio test rojo.
4. **Acordado con el usuario.** El refactor no se hace "de paso": se propone qué se extraerá y por qué, y se espera el visto bueno (principio de minimalismo). Lo notado fuera de alcance va a `docs/pendientes.md`.
5. **Regla de tres.** Dos copias se toleran; a la tercera se extrae. Excepción: lógica de negocio crítica, donde conviene unificar a la segunda.
6. **Abstraer lo que cambia por la misma razón.** Dos bloques parecidos que cambian por motivos distintos no se unifican; la abstracción prematura cuesta más que la repetición.

## Detectar duplicación (script)

```
python <token-diet>/scripts/duplicados.py [--min-lines 6] [--ext py,js] [rutas]
```

Busca bloques de N o más líneas idénticas (salvo espacios y comentarios) en dos o más lugares y devuelve los grupos con sus ubicaciones. Solo detecta repetición literal; son **candidatos**: el criterio de extraer o no es de quien refactoriza. Para repetición con nombres cambiados, leer los candidatos y buscar patrones a mano con el mapa de conceptos.

## Procedimiento

1. Ejecutar `duplicados.py` de Token Diet y elegir el grupo de mayor valor (más copias, lógica de negocio, zonas que se van a tocar).
2. Confirmar que los tests de esa zona están en verde.
3. Proponer al usuario la extracción (nombre, firma, dónde vive).
4. Extraer en pasos mínimos: crear la función nueva, reemplazar una copia, correr tests, reemplazar la siguiente, correr tests.
5. Commit `refactor(ámbito): extraer <nombre> de <lugares>`.
6. Actualizar documentación si cambia una interfaz pública y registrar en `ESTADO.md`.

## Limpieza de comentarios

Los comentarios de código que no se está modificando no se tocan. Si hay mucho por limpiar (código comentado, banners, comentarios que repiten el código), `python <ruta-de-senior>/scripts/comentarios.py --todo` arma la lista; se anota en `docs/pendientes.md` y se propone como cambio aparte, con commit `refactor:` propio.

## Excusas frecuentes y qué se responde

Atajos que se ofrecen solos cuando el trabajo aprieta. Si aparece uno de estos pensamientos, es la señal para frenar.

| Excusa | Respuesta |
|---|---|
| «Ya que estoy, limpio esto también» | Fuera de lo acordado va a `docs/pendientes.md`. El refactor se propone y se espera el visto bueno. |
| «Refactorizo y cambio el comportamiento en el mismo commit» | Son pasos distintos: el refactor con los tests en verde y la funcionalidad con su propio rojo. |
| «No hay tests, pero el cambio es obvio» | Sin red no se refactoriza: primero los tests de caracterización. |
| «Son dos bloques parecidos, los unifico» | Si cambian por razones distintas, la abstracción cuesta más que la repetición. Regla de tres. |
| «Hago todo el refactor y después corro los tests» | Un paso, los tests y un commit. Si algo se rompe, se sabe cuál fue el paso. |

## Cuánto cuesta (orientativo)

La detección es un script (1 a 5 s, ~300 tokens de lectura). Cada extracción acordada ronda entre 1.000 y 4.000 tokens, más la ejecución de tests.
