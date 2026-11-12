---
name: senior-relevar
description: Relevamiento de un sistema ajeno, heredado u olvidado antes de tocarlo: inventario automático, mapa de arquitectura, convenciones, zonas de riesgo, reglas de negocio por confirmar y plan de tests de caracterización. Usar al abrir un proyecto que no se conoce, al recibir código de otra persona, al retomar algo que no se toca hace tiempo, o cuando haya que estimar el estado y los riesgos de un sistema antes de modificarlo. Usar SIEMPRE, sin excepción, cuando el usuario aporte, adjunte o mencione un documento externo (HTML o web, PDF, Word, Excel, PowerPoint, JSON, CSV, XML) o una imagen: nunca se lee el original; los documentos se convierten antes a Markdown y las imágenes se reducen a 1024 px, ambos con convertir_fuentes.py.
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

## Documentos e imágenes externos: nunca se leen directo (regla obligatoria)

Ningún documento ni imagen externos se leen directo. Pasan **siempre** por `convertir_fuentes.py`, y solo se lee lo que deja. **Lo prohibido es leer directamente un PDF, DOCX, XLSX, PPTX, HTML, JSON u otro documento, y una imagen sin reducirla**, venga de donde venga.

- **Documentos** (PDF, Word, Excel, PowerPoint, HTML, JSON, CSV, XML, TXT, MD): se convierten a Markdown (`markitdown`, obligatoria) y se lee el `.md` de `docs/fuentes/`.
- **Imágenes** (PNG, JPG, GIF, WebP, BMP, TIFF): se reducen a un máximo de **1024 px** en el lado más largo (`Pillow`, obligatoria), sin agrandar nunca, y se lee la copia de `docs/fuentes/imagenes/`. Según el estudio que adoptó el usuario, ahorra entre 50 % y 75 % de tokens de visión. Si no se lee algo por ser pequeño, el usuario puede pedir un máximo mayor con `--max-px`.

**Una sola carpeta:** `documentos-externos/`, en la raíz del proyecto. Se crea sola al iniciar (`convertir_fuentes.py --iniciar`, paso 0 del flujo de `senior` y primera acción de `cargar_estado.py`), que además procesa lo pendiente.

**Modus operandi**
1. **Los archivos que el usuario deja** en `documentos-externos/` (y avisa): se ejecuta `python <esta-skill>/scripts/convertir_fuentes.py` y se lee lo que genera, con su origen y hash. No se reprocesa lo que no cambió. `--estado` muestra qué está al día, pendiente o cambiado.
2. **Los archivos que el usuario manda por el chat** (incluidas las imágenes): no se leen. Se **copian a `documentos-externos/` con `python <esta-skill>/scripts/convertir_fuentes.py --importar <archivos>`** (copiar no es leer; el original nunca se abre), el script los procesa y se lee el resultado. Es el procedimiento normal, sin pedirle nada al usuario.

**Prohibiciones**
- **`markitdown` (documentos) y `Pillow` (imágenes) son obligatorias** (`pip install "markitdown[all]"`, `pip install pillow`). Si falta alguna, no se lee el original como alternativa: se pide al usuario que apruebe la instalación, que nunca se hace sola, y se espera. El primer bloqueo del hook ya avisa qué biblioteca falta y da el comando exacto (con el intérprete que corre el script): ese es el que se le muestra al usuario.
- Nunca se conecta un modelo externo para describir imágenes sin aprobación del usuario (enviaría el contenido a un servicio de terceros).

**Cuándo la regla NO se aplica** (se pueden leer los originales, pero solo con el usuario al tanto):
- **PDF escaneados como imagen.** `markitdown` extrae el texto embebido y los metadatos; si el PDF es una foto sin OCR previo, la conversión sale casi vacía y hacen falta herramientas con reconocimiento óptico.
- **Documentos donde importa el diseño visual**: la estética, los colores o la ubicación exacta de los gráficos en una diapositiva. Ahí conviene el archivo original o capturas de pantalla.
- Los SVG (texto vectorial) y las imágenes que ya miden 1024 px o menos se pueden leer directo.

Cuando el script avisa «casi sin texto» o «sin encabezados», no se abre el original por cuenta propia: se avisa al usuario y él decide.

**Obligatoriedad técnica.** Un hook global de Claude Code (`hook_lectura_externa.py`, que registra `guardia_autoria.py asegurar` junto al de autoría) bloquea la herramienta Read, y de forma aproximada los comandos de lectura de la terminal, sobre PDF, Word, Excel, PowerPoint y similares, sobre HTML, JSON, CSV, XML y TXT dentro de `documentos-externos/`, y sobre imágenes de más de 1024 px. En los casos de excepción (documento marcado «lectura-directa: sugerida» por el conversor) **lo frena sin interrumpir** (por defecto: le dice a Claude que anote el pendiente y siga) **o le pregunta al usuario** en la interfaz si `permisos_hooks.py modo preguntar`; el usuario también puede dejar autorizados originales concretos en `documentos-externos/.lectura-directa` (un nombre por línea), y modificar esa lista también le pide su aprobación. No es infalible, así que la regla sigue valiendo aunque el hook no lo detecte.

**Por qué:** el original arrastra metadatos, estilos XML o imágenes de cada página, y una foto de 4000x3000 px cuesta unas 16.000 unidades de visión frente a unas 1.000 a 1024 px; el texto plano estructurado y la imagen reducida eliminan ese ruido.

| Formato original | Ahorro aproximado en `.md` | Motivo principal |
|---|---|---|
| HTML / web | 65 % a 87 % | Quita etiquetas de diseño, scripts y CSS |
| PDF con diseño o tablas | 40 % a 75 % | Evita que el modelo convierta cada página en imagen para leerla |
| DOCX / XLSX / PPTX | 30 % a 60 % | Descarta el XML interno de formato, fuentes y márgenes |
| JSON / datos | 15 % a 30 % | Reduce la repetición de llaves, comillas y corchetes |

## Qué evitar

- Leer todo el código "para tener el panorama": cuesta mucho y diluye la atención. El inventario y el mapa existen para evitarlo.
- Documentar como requisito algo que solo es una hipótesis.
- Relevar a ciegas cuando no hay sistema que leer: si lo que falta es saber qué necesita la gente, se elicita con una consulta por lotes (`senior-docs/references/elicitacion.md`) en lugar de inferir.
- Proponer rediseños: el relevamiento describe, no corrige. Las mejoras van a `docs/pendientes.md` o a una ficha acordada con el usuario.

## Cuánto cuesta (orientativo)

Inventario y mapa: segundos y unos cientos de tokens. Lectura dirigida e interpretación: de unos pocos miles a decenas de miles de tokens según el tamaño del sistema; por eso se hace después del filtro automático.
