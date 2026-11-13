---
name: senior-relevar
description: Relevamiento de un sistema ajeno, heredado u olvidado antes de tocarlo: inventario automático, mapa de arquitectura, convenciones, zonas de riesgo, reglas de negocio por confirmar y plan de tests de caracterización. Usar al abrir un proyecto que no se conoce, al recibir código de otra persona, al retomar algo que no se toca hace tiempo, o cuando haya que estimar el estado y los riesgos de un sistema antes de modificarlo. Usar SIEMPRE, sin excepción, cuando el usuario aporte, adjunte o mencione un documento externo (HTML o web, PDF, Word, Excel, PowerPoint, JSON, CSV, XML) o una imagen: un PDF o un HTML nunca se lee el original: se convierte antes a Markdown con convertir_fuentes.py (las imágenes y los demás formatos se leen como siempre).
---

# Relevar antes de tocar

Cambiar un sistema que no se entiende es la causa más común de roturas. El relevamiento se hace **de lo barato a lo caro**: primero lo que un script resuelve, después lo que exige leer, y al final lo que solo el usuario sabe.

## Pasos

1. **Memoria previa.** Si existe `docs/ESTADO.md` o `docs/INDEX.md`, leerlos primero (`senior-memoria`). Puede que el relevamiento ya esté hecho.
2. **Inventario automático** (sin tokens):
   ```
   python <esta-skill>/scripts/relevar.py --salida docs/relevamiento.md
   ```
   Entrega hechos: lenguajes, manifiestos, tests presentes, integración continua, documentación, historial git, archivos grandes y muy modificados, marcas TODO.
3. **Mapa de conceptos.** Generar el índice con símbolos (`senior-memoria/scripts/indexar_docs.py indexar`) y consultarlo en lugar de leer archivos completos.
4. **Lectura dirigida.** Leer solo lo que el inventario marca como central: puntos de entrada, los archivos más modificados y los más grandes. Anotar **hipótesis**, no verdades.
5. **Convenciones detectadas.** Anotar las que el proyecto ya sigue (nombres, estructura, estilo). Se respetan por sobre cualquier preferencia.
6. **Reglas de negocio por confirmar.** Listar las reglas que el código parece implementar y presentarlas al usuario para que las confirme o corrija (ver `senior-docs/references/requisitos.md`, sección "Extraer reglas de un sistema heredado"). Nunca se dan por válidas solo porque el código las cumple. Para sacarlas por lotes y con su evidencia: `documentar-proyecto/scripts/documentar.py reglas` deja una consulta lista para que el usuario la responda.
7. **Riesgos.** Zonas sin tests, código muy modificado y grande, dependencias desactualizadas, secretos o alertas de seguridad (`verificar.py seguridad`), documentación ausente.
8. **Plan de tests de caracterización.** Proponer qué comportamientos conviene "fotografiar" primero, ordenados por riesgo (ver `senior-tdd`).
9. **Entregable**: `docs/relevamiento.md` con la parte automática más una sección de interpretación breve (arquitectura en pocas líneas, convenciones, hipótesis de reglas, riesgos, plan). Actualizar `ESTADO.md` y regenerar el índice.

## PDF y HTML externos: nunca se leen directo (regla obligatoria)

Un PDF o un HTML externo pasa **siempre** por `convertir_fuentes.py`, y solo se lee lo que deja (`docs/fuentes/`). Está medido con agentes reales (Token Diet 1.0.2): un PDF entero cuesta 4 veces más y convertirlo antes ahorra ~74 %. **No** se aplica a las imágenes (la lectura nativa ya las reduce; bloquearlas costó +8 %), a Word y Excel (el agente los abre con la terminal y esta regla no los alcanza) ni a JSON, CSV y texto (compactarlos antes no ahorra): esos se leen como siempre.

**Una sola carpeta:** `documentos-externos/`, en la raíz del proyecto. Se crea sola al iniciar (`convertir_fuentes.py --iniciar`, paso 0 del flujo de `senior` y primera acción de `cargar_estado.py`), que además procesa lo pendiente.

**Modus operandi**
1. **Los archivos que el usuario deja** en `documentos-externos/` (y avisa): se ejecuta `python <esta-skill>/scripts/convertir_fuentes.py` y se lee lo que genera, con su origen y hash. No se reprocesa lo que no cambió. `--estado` muestra qué está al día, pendiente o cambiado.
2. **Los PDF o HTML que el usuario manda por el chat:** no se leen. Se **copian a `documentos-externos/` con `python <esta-skill>/scripts/convertir_fuentes.py --importar <archivos>`** (copiar no es leer; el original nunca se abre), el script los procesa y se lee el resultado.

**Prohibiciones**
- **`markitdown` es obligatoria para convertir** (`pip install "markitdown[all]"`). Si falta, no se lee el original como alternativa: se pide al usuario que apruebe la instalación, que nunca se hace sola, y se espera. El primer bloqueo del hook ya avisa y da el comando exacto (con el intérprete que corre el script).
- Nunca se conecta un modelo externo para describir imágenes sin aprobación del usuario (enviaría el contenido a un servicio de terceros).

**Cuándo la regla NO se aplica** (se pueden leer los originales, pero solo con el usuario al tanto):
- **PDF escaneados como imagen.** `markitdown` extrae el texto embebido y los metadatos; si el PDF es una foto sin OCR previo, la conversión sale casi vacía y hacen falta herramientas con reconocimiento óptico.
- **Documentos donde importa el diseño visual**: la estética, los colores o la ubicación exacta de los gráficos.
- Los SVG (texto vectorial) se pueden leer directo.

Cuando el script avisa «casi sin texto» o «sin encabezados», no se abre el original por cuenta propia: se avisa al usuario y él decide.

**Obligatoriedad técnica.** Un hook global de Claude Code (`hook_lectura_externa.py`, que registra `guardia_autoria.py asegurar` junto al de autoría) bloquea la herramienta Read, y de forma aproximada los comandos de lectura de la terminal, sobre un PDF y sobre un HTML dentro de `documentos-externos/`. Con Token Diet 1.0.2 o posterior instalada y su hook activo, el PDF lo bloquea ella y este hook se hace a un lado. En los casos de excepción (documento marcado «lectura-directa: sugerida» por el conversor) **lo frena sin interrumpir** (por defecto: le dice a Claude que anote el pendiente y siga) **o le pregunta al usuario** si `permisos_hooks.py modo preguntar`; el usuario también puede dejar autorizados originales concretos en `documentos-externos/.lectura-directa` (un nombre por línea), y modificar esa lista también le pide su aprobación. No es infalible, así que la regla sigue valiendo aunque el hook no lo detecte.

## Qué evitar

- Leer todo el código "para tener el panorama": cuesta mucho y diluye la atención. El inventario y el mapa existen para evitarlo.
- Documentar como requisito algo que solo es una hipótesis.
- Relevar a ciegas cuando no hay sistema que leer: si lo que falta es saber qué necesita la gente, se elicita con una consulta por lotes (`senior-docs/references/elicitacion.md`) en lugar de inferir.
- Proponer rediseños: el relevamiento describe, no corrige. Las mejoras van a `docs/pendientes.md` o a una ficha acordada con el usuario.

## Cuánto cuesta (orientativo)

Inventario y mapa: segundos y unos cientos de tokens. Lectura dirigida e interpretación: de unos pocos miles a decenas de miles de tokens según el tamaño del sistema; por eso se hace después del filtro automático.
