---
name: senior-relevar
description: Relevamiento de un sistema ajeno, heredado u olvidado antes de tocarlo: inventario automático, mapa de arquitectura, convenciones, zonas de riesgo, reglas de negocio por confirmar y plan de tests de caracterización. Usar al abrir un proyecto que no se conoce, al recibir código de otra persona, al retomar algo que no se toca hace tiempo, o cuando haya que estimar el estado y los riesgos de un sistema antes de modificarlo. La lectura de PDF y de documentos externos la resuelve Token Diet si está instalada; este relevamiento no trae conversor.
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

## PDF y documentos externos: los lee Token Diet

Leer un PDF entero cuesta 4 veces más y convertirlo antes ahorra ~74 % (medido con agentes reales por Token Diet 1.0.2). Esa mecánica es de **Token Diet**, que trae su propio conversor y su hook de lectura: con ella instalada, un PDF se bloquea una sola vez y con el comando exacto. Este paquete **ya no trae** conversor ni hook de lectura. Sin Token Diet no hay protección: un PDF largo se lee entero. Si un PDF o un documento externo llega al proyecto, conviene instalarla (el aviso único al abrir la sesión da el comando) o pedir al usuario el texto.

## Qué evitar

- Leer todo el código "para tener el panorama": cuesta mucho y diluye la atención. El inventario y el mapa existen para evitarlo.
- Documentar como requisito algo que solo es una hipótesis.
- Relevar a ciegas cuando no hay sistema que leer: si lo que falta es saber qué necesita la gente, se elicita con una consulta por lotes (`senior-docs/references/elicitacion.md`) en lugar de inferir.
- Proponer rediseños: el relevamiento describe, no corrige. Las mejoras van a `docs/pendientes.md` o a una ficha acordada con el usuario.

## Cuánto cuesta (orientativo)

Inventario y mapa: segundos y unos cientos de tokens. Lectura dirigida e interpretación: de unos pocos miles a decenas de miles de tokens según el tamaño del sistema; por eso se hace después del filtro automático.
