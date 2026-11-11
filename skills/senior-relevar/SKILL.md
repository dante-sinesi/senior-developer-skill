---
name: senior-relevar
description: Relevamiento de un sistema ajeno, heredado u olvidado antes de tocarlo: inventario automático, mapa de arquitectura, convenciones, zonas de riesgo, reglas de negocio por confirmar y plan de tests de caracterización. Usar al abrir un proyecto que no se conoce, al recibir código de otra persona, al retomar algo que no se toca hace tiempo, o cuando haya que estimar el estado y los riesgos de un sistema antes de modificarlo.
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
6. **Reglas de negocio por confirmar.** Listar las reglas que el código parece implementar y presentarlas al usuario para que las confirme o corrija (ver `senior-docs/references/requisitos.md`, sección "Extraer reglas de un sistema heredado"). Nunca se dan por válidas solo porque el código las cumple.
7. **Riesgos.** Zonas sin tests, código muy modificado y grande, dependencias desactualizadas, secretos o alertas de seguridad (`verificar.py seguridad`), documentación ausente.
8. **Plan de tests de caracterización.** Proponer qué comportamientos conviene "fotografiar" primero, ordenados por riesgo (ver `senior-tdd`).
9. **Entregable**: `docs/relevamiento.md` con la parte automática más una sección de interpretación breve (arquitectura en pocas líneas, convenciones, hipótesis de reglas, riesgos, plan). Actualizar `ESTADO.md` y regenerar el índice.

## Documentos externos (ingesta opcional)

Si el usuario aporta documentos (PDF, Word, PowerPoint, Excel, HTML) y son largos o hay que consultarlos varias veces, se pueden convertir a texto para gastar menos tokens, buscar en ellos y dejar una copia rastreable:

```
python <esta-skill>/scripts/convertir_fuentes.py <archivos o carpetas> [--raiz .]
```

Deja `docs/fuentes/<nombre>.md` con el origen y el hash, no reconvierte lo que no cambió y requiere la biblioteca opcional `markitdown` (`pip install "markitdown[all]"`; nunca se instala sin preguntar). Reglas de uso:
- **Las imágenes no se convierten**: se leen directamente, porque se interpretan mejor que cualquier conversión.
- **Un PDF o presentación con muchas figuras, tablas o diagramas se lee directamente**; la conversión pierde esa información. El script avisa cuando sospecha pérdida.
- Es opcional: si el documento es corto o se lee una sola vez, se lee directo.
- Nunca se conecta un modelo externo para describir imágenes sin aprobación del usuario (enviaría el contenido a un servicio de terceros).

## Qué evitar

- Leer todo el código "para tener el panorama": cuesta mucho y diluye la atención. El inventario y el mapa existen para evitarlo.
- Documentar como requisito algo que solo es una hipótesis.
- Relevar a ciegas cuando no hay sistema que leer: si lo que falta es saber qué necesita la gente, se elicita con una consulta por lotes (`senior-docs/references/elicitacion.md`) en lugar de inferir.
- Proponer rediseños: el relevamiento describe, no corrige. Las mejoras van a `docs/pendientes.md` o a una ficha acordada con el usuario.

## Cuánto cuesta (orientativo)

Inventario y mapa: segundos y unos cientos de tokens. Lectura dirigida e interpretación: de unos pocos miles a decenas de miles de tokens según el tamaño del sistema; por eso se hace después del filtro automático.
