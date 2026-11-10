---
name: adoptar-proyecto
description: Primer paso para incorporar la metodología senior a un proyecto, nuevo o existente. Detecta el estado del proyecto, muestra un plan de qué se va a crear (documentación base, README, relevamiento, índice) y espera aprobación antes de escribir nada. Usar cuando el usuario escriba /adoptar-proyecto, o diga que quiere empezar un proyecto con esta metodología, incorporar la skill a un proyecto, relevar un proyecto por primera vez o generar la documentación inicial.
---

# Adoptar un proyecto

Es el arranque ordenado: en lugar de imponer toda la metodología de golpe, se muestra qué se va a crear y se espera el visto bueno. Nada se escribe sin aprobación y nada existente se sobrescribe.

## Pasos

1. **Plan (solo lectura).** Ejecutar:
   ```
   python <esta-skill>/scripts/plan_adopcion.py --raiz <proyecto>
   ```
   Detecta si el proyecto es **nuevo o vacío** o **existente**, y qué le falta (docs, README, git, tests). Imprime la lista de acciones; no escribe nada.
2. **Mostrar el plan al usuario** y esperar su aprobación (puede pedir quitar acciones). Es un punto de control: sin visto bueno, no se continúa.
3. **Aplicar lo aprobado.** Con la aprobación:
   ```
   python <esta-skill>/scripts/plan_adopcion.py --raiz <proyecto> --aplicar
   ```
   Crea la estructura de `docs/` (`senior-docs/scripts/iniciar_docs.py`), el `README.md` desde la plantilla si no existe, y, en proyectos existentes, `docs/relevamiento.md` (`senior-relevar`). Regenera el índice. Nunca pisa archivos existentes.
4. **Completar a mano lo que el script no puede inferir**:
   - **Proyecto nuevo**: preguntar el stack y la herramienta de tests (perfil en `senior-lenguajes`), registrar el primer ADR con el stack elegido, completar las secciones marcadas `(completar)` del README y dejar la regla de ramas y commits (`senior-git`).
   - **Proyecto existente**: seguir `senior-relevar` (lectura dirigida, convenciones, riesgos), presentar al usuario las **reglas de negocio hipotéticas** para que las confirme (nunca se documentan como verdad por inferencia), proponer los tests de caracterización prioritarios (`senior-tdd`) y revisar la seguridad inicial (`verificar.py seguridad`).
5. **Propuestas que requieren aprobación aparte**: la **guardia de autoría** (hooks locales que impiden subir commits con Claude o coautores: `senior-git/scripts/guardia_autoria.py instalar`), el hook de apertura (`senior-memoria`), la plantilla de Pull Request de GitHub y la inicialización de git si el proyecto no es un repositorio.
6. **Cerrar**: `verificar.py`, actualizar `docs/ESTADO.md` con el punto de partida y mostrar al usuario un resumen de cinco líneas.

## Costo orientativo

Plan y aplicación: segundos. Proyecto nuevo: unos 2.000 a 4.000 tokens para completar lo manual. Proyecto existente: de 10.000 a 50.000 tokens según el tamaño, casi todo en la lectura dirigida y la confirmación de reglas.
