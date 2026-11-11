---
name: auditar-diseno
description: Audita el diseño de la interfaz de un proyecto que no usó la skill senior-diseno desde el principio y propone mejoras según sus directrices (no saturación, reactividad, etiquetas de formulario, contraste y accesibilidad, una familia tipográfica ideal y dos como máximo, sistema de diseño). Genera un informe con propuestas ordenadas por impacto y esfuerzo y no modifica el proyecto. Usar cuando el usuario escriba /auditar-diseno o pida revisar, auditar o evaluar la interfaz, la UX o el diseño de un proyecto existente, o saber qué mejorar de su frontend.
---

# Auditar diseño

Modo de revisión de un proyecto existente. Requiere la skill `senior-diseno` instalada en la misma carpeta (usa sus scripts y sus criterios).

## Pasos

1. **Ejecutar la auditoría** (solo lectura sobre el proyecto):
   ```
   python <ruta-de-senior-diseno>/scripts/auditar_proyecto.py --raiz <proyecto> [--tipo sitio|app]
   ```
   Escribe `docs/diseno/auditoria/AAAA-MM-DD.md` con el resumen, los hallazgos y las propuestas por impacto y esfuerzo. **No modifica nada del proyecto.**
2. **Leer el informe** (no los archivos del proyecto: el script ya los revisó) y presentarlo al usuario en pocas líneas: qué es lo más grave y qué rinde más por menos esfuerzo.
3. **Complementar con lo que el script no ve**: si el proyecto corre, revisar la página renderizada; ante plantillas complejas (JSX, Vue), confirmar los hallazgos clave a mano. Después agregar al mismo informe la sección `## Lectura de diseño` (especificidad, diez heurísticas de 0 a 4, carga cognitiva, fortalezas y problemas con caso concreto; formato en `senior-diseno/references/auditoria.md`). Lo subjetivo (identidad, tono, jerarquía) se conversa con el usuario.
4. **Priorizar con el usuario** y proponer cómo seguir: para lo que necesita decisiones de diseño, abrir una ronda con `crear_bosquejos.py` (la dirección actual como punto de partida y dos alternativas); para lo mecánico (etiquetas, contraste), dejarlo escrito en `docs/pendientes.md` para implementarlo después con las reglas de `senior`.
5. **Nada se aplica sin aprobación.** La auditoría solo escribe en `docs/diseno/auditoria/`; los cambios en el código son una tarea aparte, con las reglas de `senior`.

Más detalle en `senior-diseno/references/auditoria.md`.

## Regla de autoría

En todo lo que se suba a GitHub figura únicamente el usuario; Claude nunca aparece como autor, coautor ni colaborador.
