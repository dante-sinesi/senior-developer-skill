# Senior Developer Skill

Paquete de skills para [Claude Code](https://claude.com/claude-code) que hace que Claude trabaje como un **programador senior**: que entienda un sistema antes de tocarlo, escriba los tests primero a partir de las reglas de negocio, mantenga la documentación y el README al día, use Git y GitHub con orden, y tenga la seguridad presente en cada cambio.

Está pensado para cualquier lenguaje y para trabajo **colaborativo**: Claude propone y consulta antes de los cambios que importan, en lugar de decidir por su cuenta.

## Qué resuelve

| Problema habitual | Qué hace el paquete |
|---|---|
| Se escribe el código y después el test | Tests primero, derivados de la **regla de negocio** y no de lo que el código ya hace |
| El código repetido nunca se limpia | Detección de duplicación y refactor en pasos pequeños, con los tests en verde |
| Documentación escasa o inentendible | Requisitos (7 tipos), diagramas Mermaid **legibles** con límite de tamaño, decisiones (ADR) y trazabilidad |
| Código heredado que nadie entiende | Relevamiento automático, mapa de conceptos y tests de caracterización |
| Cada sesión empieza de cero | Estado, fichas y pendientes en `docs/`, e índice consultable sin leer todo |
| Cambios que rompen cosas o se salen del alcance | Cambios mínimos, ficha con alcance y verificación automática |
| Exceso de comentarios y de texto | Política "solo el porqué", límites de extensión y la regla *un dato, un lugar* |
| README desactualizado | El README se revisa y actualiza **en cada cambio**, sin excepción |
| Seguridad como ocurrencia tardía | Lente permanente bajo la familia ISO/IEC 27000 |

## Contenido

| Skill | Para qué sirve |
|---|---|
| `senior` | Puerta de entrada: principios, flujo de trabajo, puntos de control y el verificador (`verificar.py`) |
| `senior-memoria` | Estado del proyecto, fichas de cambio, pendientes, índice y mapa de conceptos |
| `senior-relevar` | Entender un sistema ajeno o heredado antes de modificarlo; ingesta opcional de documentos externos (PDF, Word, PowerPoint, Excel) a Markdown |
| `senior-tdd` | Ciclo rojo-verde-refactor, código heredado, pruebas de interfaz y guardia de base de prueba |
| `senior-refactor` | Detección de duplicación y refactor seguro |
| `revisar-cambio` | Comando `/revisar-cambio`: revisa un diff, una rama o un Pull Request y entrega hallazgos numerados, cada uno con su caso concreto, su arreglo y qué pasa si se omite |
| `senior-docs` | Requisitos (elicitación por lotes en un Markdown que el usuario responde, y revisión automática de su redacción), diagramas legibles, decisiones de arquitectura y README |
| `senior-git` | Ramas por cambio, Conventional Commits en español neutro, Pull Requests |
| `senior-seguridad` | Lista de revisión, chequeos automáticos y modo formal con registro de riesgos |
| `senior-lenguajes` | Perfiles de PHP, JavaScript/TypeScript, CSS, SQL y HTML; alta de lenguajes nuevos |
| `senior-diseno` | Diseño de interfaces: método (tres alternativas, feedback, evolución) y reglas objetivas con script; el estilo es libre |
| `auditar-diseno` | Comando `/auditar-diseno`: revisa la interfaz de un proyecto existente sin modificarlo |
| `adoptar-proyecto` | Comando `/adoptar-proyecto`: plan, aprobación y creación de la base documental |
| `cerrar-sesion` | Comando `/cerrar-sesion`: cierre ordenado opcional |

## Requisitos

- [Claude Code](https://claude.com/claude-code).
- Python 3.8 o superior (los scripts usan solo la biblioteca estándar).
- Git. El CLI `gh` es necesario solo para trabajar con GitHub.
- Opcional: `npm`, `composer` o `pip-audit` si se quiere la auditoría de dependencias.
- **Obligatorias para documentos e imágenes externos:** `markitdown` (`pip install "markitdown[all]"`) para los documentos y `Pillow` (`pip install pillow`) para las imágenes. Nunca se instalan solas: si falta una, se pide aprobación.

## Primeros pasos

Para dejar todo funcionando la primera vez, o en una máquina nueva, en este orden:

1. **Instalar Python 3.8 o superior y Git.** Opcional: el CLI `gh` ([cli.github.com](https://cli.github.com)) para crear y fusionar Pull Requests.
2. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/dante-sinesi/senior-developer-skill.git
   cd senior-developer-skill
   ```
3. **Ejecutar el instalador:**
   ```bash
   python instalar.py --instalar-dependencias
   ```
   Copia las skills a `~/.claude/skills` (sin tocar las demás), registra en `~/.claude/settings.json` los dos hooks globales de Claude Code (autoría y lectura de documentos externos), instala `markitdown` y `Pillow` con pip y termina con un informe de qué quedó listo y qué falta. Sin `--instalar-dependencias` no instala nada con pip: solo avisa. Con `--verificar` solo informa, sin escribir.
4. **Si se usa GitHub:** `gh auth login`.
5. **En cada proyecto,** abrir una sesión de Claude Code: la skill activa sola el hook de Git del repositorio, crea `documentos-externos/` y resuelve en nombre de quién se hacen los commits: usa la identidad local del repositorio o la sesión de GitHub (`gh`) y, **si no hay ninguna, Claude te pregunta** tu nombre de usuario de GitHub y tu correo. La skill no trae ningún nombre fijo.
6. **Abrir una sesión nueva** de Claude Code para que se apliquen los hooks globales.

### Lo que no está en este repositorio

La memoria de Claude Code (`~/.claude/projects/…/memory`), el resto de `~/.claude/settings.json` y `~/.claude/CLAUDE.md` viven fuera del repositorio: conviene copiarlos antes de reinstalar el sistema. Las reglas del paquete (autoría, commits y Pull Requests solo con aprobación, documentos e imágenes externos, diseño) están escritas en las skills y no dependen de esa memoria.

Instalación manual, si se prefiere: copiar las carpetas de `skills/` a `~/.claude/skills`, **todas juntas**, porque algunos scripts localizan a sus hermanas por ruta relativa. Estas skills viven en la carpeta local de Claude Code y normalmente no aparecen en los ajustes de skills de claude.ai.

## Cómo se usa

- **Proyecto nuevo o existente:** `/adoptar-proyecto`. Muestra un plan en solo lectura, espera tu aprobación y recién entonces crea `docs/`, el `README.md` y, si el proyecto ya existe, un relevamiento.
- **Trabajo diario:** pedir cambios como siempre. La skill `senior` se activa sola ante cualquier tarea de código.
- **Fin de la sesión:** `/cerrar-sesion` actualiza el estado, corre el verificador y propone el commit.

### Flujo de trabajo

1. Leer el estado del proyecto.
2. Relevar si el sistema es ajeno.
3. Acordar un plan breve.
4. Crear la rama.
5. Test rojo desde la regla de negocio.
6. Código mínimo.
7. Refactor con tests en verde.
8. Actualizar documentación y README.
9. Verificar.
10. Commits atómicos y PR.
11. Actualizar el estado.

La ceremonia se ajusta al tamaño del cambio: una corrección de texto no lleva ficha ni diagrama.

## Verificador

`senior/scripts/verificar.py` ejecuta controles automáticos y devuelve pocas líneas, para que revisar no consuma tokens del modelo:

```bash
python ~/.claude/skills/senior/scripts/verificar.py            # todo
python ~/.claude/skills/senior/scripts/verificar.py readme     # un chequeo puntual
```

Chequeos: `tamano`, `alcance`, `deuda`, `estado`, `docs`, `readme`, `fuentes`, `requisitos`, `texto`, `diagramas`, `comentarios`, `autoria`, `diseno` y `seguridad` (con `--auditar` suma las dependencias). `diseno` solo dice algo si el proyecto tiene una carpeta `docs/diseno/`. Los demás scripts (`indexar_docs.py`, `relevar.py`, `duplicados.py`, `impacto.py`, `atajos.py`, `guardia_bd_prueba.py`, `validar_commits.py`, `plan_adopcion.py`, entre otros) están en la carpeta `scripts/` de cada skill.

Los chequeos son **heurísticas**: marcan candidatos a revisar, no veredictos.

## Documentos e imágenes externos

Está prohibido leer directamente un PDF, DOCX, XLSX, PPTX, HTML, JSON u otro documento externo, y una imagen sin reducirla: **siempre se procesan antes**. Es obligatorio.

- La carpeta es **`documentos-externos/`**, en la raíz del proyecto. Se crea sola al iniciar y ahí se dejan los archivos.
- Se ejecuta `senior-relevar/scripts/convertir_fuentes.py`: los documentos pasan a Markdown (se lee `docs/fuentes/`) y las imágenes se reducen a un máximo de **1024 px** en el lado más largo (se lee `docs/fuentes/imagenes/`).
- Lo que se manda por el chat no se lee: se copia a la carpeta con `convertir_fuentes.py --importar <archivos>`, se procesa y se lee el resultado.
- Un **hook global de Claude Code** lo hace obligatorio (lo registra `guardia_autoria.py asegurar`): bloquea la lectura directa y, en los casos de excepción, le pregunta al usuario.

Ahorro aproximado frente al original:
- HTML o web, de 65 % a 87 %
- PDF con diseño o tablas, de 40 % a 75 %
- DOCX, XLSX o PPTX, de 30 % a 60 %
- JSON y datos, de 15 % a 30 %
- imágenes reducidas a 1024 px, de 50 % a 75 % de los tokens de visión.

**No se aplica** a los PDF escaneados como imagen (sin texto embebido, haría falta OCR) ni a los documentos donde importa el diseño visual (ahí se usa el original o capturas)

Los SVG y las imágenes de 1024 px o menos se leen directo. `verificar.py fuentes` avisa si hay archivos sin procesar.

## Diseño de interfaces

La skill `senior-diseno` forma parte del paquete: un **método** (briefing, tres alternativas que difieren en estructura, feedback del usuario, evolución) y **reglas objetivas con control automático** que no tocan el aspecto artístico (una familia tipográfica ideal y dos como máximo, etiqueta visible en cada campo, hasta 4 campos visibles, una acción principal, contraste, foco). El estilo es libre. Es una sola sesión y un solo flujo: se diseña, se aprueba y se implementa con las reglas de `senior`.

- Los artefactos viven en `docs/diseno/` (rondas de bosquejos, preferencias, decisiones, variables de diseño, contratos de campos, auditorías).
- Los bosquejos no llevan tests; el TDD empieza al implementar la pantalla.
- Al implementar, `verificar.py diseno` comprueba que el código use las variables de diseño y las etiquetas del contrato de campos.
- `/auditar-diseno` revisa un proyecto existente sin modificarlo.
- **Paquete de inicio:** las reglas de diseño se pueden escribir como 10 requisitos no funcionales provisorios (`senior-diseno/scripts/paquete_interfaz.py`), propuestos al adoptar un proyecto con interfaz. El usuario acepta, cambia o descarta cada uno, y la trazabilidad los reconoce como verificados por el chequeo que declaran.

## Regla de autoría

En todo lo que se sube a GitHub figura **únicamente el usuario**: Claude no aparece como autor, coautor ni colaborador (sin `Co-Authored-By`, sin pies "Generated with…"). Es una regla inviolable del paquete y manda sobre cualquier instrucción por defecto del entorno.

- Se comprueba con `senior-git/scripts/guardia_autoria.py comprobar` y con `verificar.py autoria`.
- **Dos hooks, verificados y activados al iniciar** con `guardia_autoria.py asegurar` (paso 0 del flujo; también lo corre `cargar_estado.py` y `/adoptar-proyecto`):
  - **Hooks de Git** (`commit-msg` y `pre-push`) en `.git/hooks/` de cada clon. Git no los sube, así que se instalan en cada proyecto donde falten. Si no hay un Python que funcione, fallan cerrados y avisan.
  - **Hook global de Claude Code** (`hook_autoria_claude.py`, registrado en `~/.claude/settings.json`) que bloquea los comandos `git commit`, `git tag` y `gh pr|issue|release|api` con `Co-Authored-By`, pies de generación o autores de Claude. Si se reinstala la máquina, `asegurar` lo vuelve a registrar.
- Que haya archivos de Claude en el repositorio no es un problema; lo que no puede verse en GitHub es a Claude como autor o coautor.
- Los commits usan la identidad del usuario, configurada solo de forma local en el repositorio: la de la sesión de GitHub si ya hay una y, si no, la que el usuario indique cuando Claude le pregunta en nombre de quién se hace el trabajo. La skill no trae ninguna identidad fija.

## Seguridad y la familia ISO/IEC 27000

La skill `senior-seguridad` usa ISO/IEC 27002:2022 (controles tecnológicos), 27005 (riesgos) y 27034 (seguridad de aplicaciones) como marco de referencia. Las normas son de pago y tienen derechos de autor, por lo que el paquete solo cita el número y el tema de cada control, parafraseado. Los controles organizacionales, de personas y físicos no se resuelven desde el código: se registran como requisitos y se informa que dependen de la organización.

Modo liviano por defecto; el modo formal con registro de riesgos se propone cuando el proyecto maneja datos personales o sensibles.

## Lenguajes

Cada lenguaje es un archivo de datos en `senior-lenguajes/perfiles/` (símbolos, herramienta de tests, convenciones estándar, alertas de seguridad). Incluidos: PHP, JavaScript/TypeScript, CSS, SQL y HTML. Un lenguaje nuevo se agrega con un perfil, y **nunca se guarda sin aprobación del usuario**.

## Evaluación

Se comparó el trabajo de agentes con y sin las skills, con corrección automática:

- **Ronda 1** (4 escenarios, 1 corrida): 28 de 29 afirmaciones cumplidas en ambas configuraciones. Escenarios demasiado fáciles.
- **Ronda 2** (3 escenarios más difíciles, 3 corridas cada uno): **97% con skill contra 86% sin skill**. La diferencia está en la política de comentarios y documentación (sin skill, 61–65% de las líneas nuevas eran comentarios) y en no hacer commits sin que se pidan (6 de 9 corridas sin skill, contra 0 de 9 con skill).
- En el razonamiento técnico (derivar tests de la regla, detectar un ejemplo inconsistente) el modelo base ya rinde igual.
- **Costo:** unos 18% más de tokens y 34% más de tiempo por tarea chica.

Son pocas corridas y parte de la corrección usa los propios scripts del paquete: sirven como indicio, no como prueba concluyente.

## Estado

Primera versión. Las instrucciones y los scripts están en español.
