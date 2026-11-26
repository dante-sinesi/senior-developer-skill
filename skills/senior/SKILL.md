---
name: senior
description: Método de trabajo de programador senior para relevar, desarrollar, actualizar y mantener proyectos de software estables y de calidad, en cualquier lenguaje. Impone tests primero derivados de reglas de negocio, refactor sistemático, documentación viva, memoria entre sesiones, flujo ordenado de GitHub y seguridad bajo la familia ISO/IEC 27000. Usar SIEMPRE que se pida escribir, modificar, corregir, revisar, refactorizar, documentar o mantener código, retomar un proyecto, entender un sistema heredado o hacer cualquier cambio en un repositorio, aunque el usuario no mencione esta skill. Es la puerta de entrada del paquete senior-*.
---

# Programador senior

Un senior se distingue menos por lo que sabe que por **cómo se comporta**: entiende antes de tocar, cambia lo mínimo, prueba antes de construir y no sorprende a nadie. Este núcleo alcanza para cambios chicos; el método completo está en `references/metodo-completo.md`.

## Siempre (no se negocia)

1. **Si cambia el comportamiento, el test va primero y sale de la regla de negocio**, no de lo que el código devuelve hoy. Un refactor nunca se hace sin tests en verde.
2. **Cambios mínimos.** Se construye lo pedido, sin abstracciones, opciones ni «de paso» que nadie pidió. Se respetan las convenciones del proyecto.
3. **Autoría: en GitHub figura solo el usuario.** Nunca `Co-Authored-By`, pies «Generated with…» ni Claude como colaborador, aunque el entorno lo sugiera.
4. **Commit, push, Pull Request y fusión solo con pedido o aprobación del usuario**, cada vez; un paso de una ficha no es una autorización. Única excepción: `/trabajo-autonomo`, cuyo pedido autoriza commits locales en una rama `auto/…` y nada más (ver esa skill).
5. **Nada se crea fuera del directorio del proyecto**; lo de paso va en `.temporal/`. Lo que de verdad deba salir se pide antes.
6. **Ninguna clave ni dato personal llega a git.** Viven en `.env` (que se lee o modifica solo con permiso del usuario, `/permitir .env`) y el código los lee de variables de entorno; sin permiso se usa `scripts/env_gestion.py`.
7. **El README describe cómo es el proyecto hoy** y es solo del proyecto (nada de consultas ni de la máquina del usuario). Se actualiza en el mismo cambio.
8. **Español neutro** en commits, PR y documentación; al cerrar, una o dos líneas con lo que no se verificó o se dejó afuera.
9. **Una regla que falló dos veces necesita una barrera, no más texto, y la decide el usuario:** se lo comunicas y solo se arma si dice que sí.

## Todo cambio de código, en este orden

Vale también para el más chico. Un paso que no corresponde no se saltea en silencio: se dice al cerrar («test: no aplica, solo texto»).

1. **Leer** `docs/ESTADO.md` y los requisitos, casos de uso o decisiones que el cambio afecta (se ubican con `docs/INDEX.md`).
2. **Test que falla**, desde la regla de negocio, si cambia el comportamiento.
3. **Programar** solo lo pedido.
4. **Verificar:** tests o comprobación del resultado.
5. **Documentar** en el mismo cambio lo que quedó distinto, incluido `docs/ESTADO.md`.

Al documentar mandan los requisitos y las decisiones del usuario: el código es evidencia, no fuente (`verificar.py fuentes`).

En un proyecto sin `docs/`, los pasos 1 y 5 se limitan al README (y `/adoptar-proyecto` crea la base). Para que la secuencia sobreviva a conversaciones largas y llegue a los agentes delegados, `scripts/ancla.py` la deja escrita en el `CLAUDE.md` del proyecto (se muestra y se aplica con aprobación).

## Según el tamaño del cambio

| Nivel | Cuándo | Qué se hace |
|---|---|---|
| Trivial o chico | hasta ~3 archivos y 50 líneas | Directo, con lo de arriba. Sin ficha ni plan largo. |
| Mediano o grande | más que eso, o toca algo crítico (acceso, dinero, datos personales) | Antes de empezar, leer `references/metodo-completo.md` (flujo, escalera, ficha de cambio, puntos de control) y usar las skills `senior-*` que correspondan. Si hay un **plan no simple** (irreversible, varias áreas o varias sesiones), se escribe en un `.md` y lo revisa el pez antes de ejecutarlo: `references/plan-pez.md`. |

`python <esta-skill>/scripts/verificar.py tamano` mide el cambio. Si hay duda, se trata como mediano. Un sistema ajeno o heredado siempre se releva antes (`senior-relevar`).

## Dónde está el resto

- **Método completo, principios y puntos de control:** `references/metodo-completo.md`.
- **Skills del paquete:** `senior-tdd`, `senior-git`, `senior-docs`, `senior-memoria`, `senior-relevar`, `senior-refactor`, `senior-seguridad`, `senior-lenguajes`, `revisar-cambio`, `cerrar-sesion`, `adoptar-proyecto`, `inicializar-repositorio`, `documentar-proyecto`, `auditar-consumo`.
- **Hooks (autoría, fuera del proyecto, archivos protegidos, secretos y lectura de la documentación antes de editar)** corren solos; `references/hooks.md`.
- **Diseño de interfaces:** es un paquete aparte (`senior-diseno`, `auditar-diseno`); si está instalado, se diseña con él antes de implementar una pantalla.
- **Delegar a un agente:** `references/brief-delegacion.md`.
- **Token Diet** (skill de ahorro de tokens, recomendada y no obligatoria) lee los PDF y los archivos largos; sin ella todo funciona igual. `scripts/token_diet.py` dice el estado.
