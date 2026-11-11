---
name: senior-tdd
description: Desarrollo guiado por tests (rojo, verde, refactor) con tests derivados de reglas de negocio y no del código; tests de caracterización para código heredado; pruebas de interfaz automatizadas; y guardia que impide probar contra bases de datos que no sean de prueba. Usar SIEMPRE antes de escribir o modificar código que cambie comportamiento: funcionalidades nuevas, corrección de errores, cambios de reglas. También al elegir herramienta de tests, al probar contra una base de datos o al encarar código sin tests.
---

# Tests primero

El orden importa: el test fija **qué debe pasar** antes de decidir **cómo**. Si se escribe después, termina copiando lo que el código ya hace, defectos incluidos.

## El ciclo

1. **Fuente de verdad.** Identificar la regla de negocio (requisito RN/RF con ejemplos, ver `senior-docs`). Si no existe o es ambigua, **preguntar al usuario**; nunca deducir el valor esperado ejecutando el código.
2. **Rojo.** Escribir un test que exprese la regla con valores concretos. Ejecutarlo y comprobar que **falla por la razón correcta** (la aserción no se cumple), no por un error de sintaxis, un import faltante o una dependencia sin configurar. Un rojo por el motivo equivocado no prueba nada.
3. **Verde.** Escribir el mínimo código que lo hace pasar. Nada de funcionalidad adicional.
4. **Refactor.** Con todo en verde, eliminar duplicación y mejorar nombres (`senior-refactor`). Los tests siguen en verde.
5. **Registrar.** El test cita el ID del requisito (`// RN-001` o en el nombre) para la trazabilidad. Actualizar `ESTADO.md` (hito).

Si regla y código discrepan (la regla dice 0,2 y el código da 0,1), el test **debe fallar**. Se informa al usuario la discrepancia y él decide qué manda.

## Un test en rojo no se arregla aflojándolo

Cuando un test falla, se corrige el código o, si la regla cambió, el requisito y después el test, con el usuario. No se salta, no se borra, no se le quitan verificaciones, no se baja el umbral de cobertura ni se silencia el chequeo para que pase. `verificar.py listones` lo detecta en el diff; lo que de verdad debe quedar como excepción lleva `motivo: …` escrito.

## Cuándo no hay test nuevo

- Cambios que no alteran comportamiento (texto, comentario, nombre de variable, formato): no hay qué probar. Pero antes de **cualquier refactor** los tests existentes deben estar en verde; si no existen, se escriben primero los de caracterización.
- No existe una excepción por "es chico" para cambios de comportamiento.

## Código heredado sin tests

No se puede escribir un test que falle sobre algo que ya está programado. Se procede así:

1. **Tests de caracterización**: fijan lo que el sistema hace hoy ("sacarle una foto") para poder cambiar sin romper. Se marcan como *estado actual, no necesariamente correcto* (por ejemplo, nombre o comentario `caracterizacion`).
2. Se priorizan por riesgo (lo más modificado, lo más crítico), no por cobertura total.
3. A medida que el usuario confirma reglas, se escriben tests de reglas de negocio y se retiran los de caracterización que contradigan a la regla.
4. Todo cambio nuevo sigue el ciclo normal.

## Si no hay infraestructura de tests

El primer paso es crearla: elegir la herramienta estándar del lenguaje (ver `senior-lenguajes/perfiles/<lenguaje>.json`, sección `tests`) o la que el proyecto ya use, instalarla con aprobación del usuario y dejar un comando único que corra todo. Documentarlo en el README.

## Pruebas de interfaz

Se escriben **como código y se ejecutan con un comando**, igual que cualquier test; no son manuales. Para cuidar tiempo y tokens:
- Ejecución sin ventana y salida resumida (solo fallos).
- Pocos recorridos críticos (iniciar sesión, completar una compra); no cada pantalla.
- La lógica va en funciones que se prueban aparte, que es mucho más barato que simular a un usuario.
- Herramienta sugerida: Playwright (ver perfil `html`).
- Lo que no se puede verificar automáticamente (por ejemplo, la apariencia) se declara y se deja al usuario.

## Bases de datos: solo base de prueba

Los tests **nunca** corren contra la base de desarrollo ni la de producción (ISO/IEC 27002:2022, controles 8.31 y 8.33: separar entornos y no usar datos reales en pruebas).
- La base de prueba tiene un nombre que lo dice (`..._test`, `..._prueba`) y se crea desde el esquema versionado.
- Cada test puede correr dentro de una transacción que se descarta al final, o recrear los datos.
- Antes de ejecutar la suite, pasar la guardia:
  ```
  python <esta-skill>/scripts/guardia_bd_prueba.py --variable DB_NAME -- <comando de tests>
  ```
  Se niega a continuar (código 2) si el nombre de la base no parece de prueba.
- Los datos de prueba son ficticios; nunca copias de datos reales con información personal.

## Agente verificador

Redactar tests desde las reglas con un agente independiente reduce el sesgo de "que pase", pero cuesta entre 8.000 y 25.000 tokens por uso. **Solo se usa con autorización explícita del usuario**, y el agente solo reporta: no corrige código.

## Costo orientativo

Ejecutar la suite: segundos a un minuto y unos 300 tokens si se lee solo el resumen. Escribir un test: unos cientos a 1.500 tokens. Pruebas de interfaz: 10 a 60 s; unos 300 tokens si pasan, 1.000 a 3.000 si fallan.
