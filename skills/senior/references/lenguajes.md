# Perfiles de lenguaje

Cada lenguaje es **un archivo de datos** en `../perfiles/<lenguaje>.json`. Los scripts del paquete (verificador, indexador, relevamiento) leen esos archivos, así que soportar un lenguaje nuevo significa agregar un perfil, no tocar código.

Un perfil contiene:
- `extensiones`: qué archivos le pertenecen.
- `simbolos`: expresiones regulares que detectan clases, funciones, tablas, etc. (alimentan el mapa de conceptos).
- `tests`: herramienta estándar, comando de instalación y de ejecución, patrón de nombres.
- `convenciones`: convenciones **estándar de la comunidad**. Nunca estilo personal del usuario; si el proyecto ya tiene convenciones, se respetan esas primero.
- `alertas_seguridad`: reglas de patrón con su control ISO/IEC 27002:2022 asociado.

Perfiles disponibles: php, javascript (incluye TypeScript), css, sql, html. Para ver el formato exacto de un perfil nuevo, leer `perfiles/_plantilla.json`.

## Cuándo se usa

- Al elegir cómo probar algo: leer la sección `tests` del lenguaje.
- Al relevar o indexar: los scripts usan `simbolos` automáticamente.
- Al verificar: `scripts/verificar.py seguridad` aplica las `alertas_seguridad`.

## Agregar un lenguaje nuevo

La skill puede ampliarse sola, pero **nunca guarda un perfil sin aprobación del usuario**, porque un perfil incorrecto produciría falsas alarmas o ceguera silenciosa en todos los proyectos.

1. **Investigar**: consultar la documentación oficial del lenguaje para identificar la herramienta de tests estándar, su comando, y la forma de declarar clases y funciones. Si un dato no está confirmado, dejarlo anotado como tal en `nota`.
2. **Redactar** el perfil copiando `_plantilla.json` a un archivo temporal (por ejemplo en `perfiles/_borrador_<lenguaje>.json`).
3. **Probarlo**: conseguir o escribir un archivo de ejemplo breve y correr
   `python <ruta-de-senior>/scripts/probar_perfil.py perfiles/_borrador_<lenguaje>.json <ejemplo>`.
   El script valida la estructura, compila las expresiones regulares y muestra qué símbolos y alertas detecta. Ajustar hasta que detecte bien.
4. **Mostrar al usuario** el perfil, el resultado de la prueba y las fuentes consultadas. Esperar su aprobación explícita.
5. Solo entonces **renombrar** el borrador a `perfiles/<lenguaje>.json`.

Para lenguajes de sintaxis poco regular (ensamblador, por ejemplo), las expresiones regulares detectan solo lo básico; si hay una herramienta especializada instalada (como Universal Ctags), se puede mencionar en `nota` como apoyo opcional.

## Alertas de seguridad: criterio

Las alertas son heurísticas por patrón: pueden marcar de más o dejar pasar casos. Por eso se informan como "revisar", y el criterio final es de quien revisa. Cada alerta indica su control ISO para que la trazabilidad de seguridad quede visible (ver la skill `senior-seguridad`).
