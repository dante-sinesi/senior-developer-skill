---
name: documentar-proyecto
description: Genera la documentación que le falta a un proyecto existente a partir de su código (PHP, JavaScript o TypeScript y Python): diagramas de módulos, de clases y entidad-relación, requisitos de interfaz y de dominio, decisiones de arquitectura y una consulta con reglas de negocio candidatas; después, con el modelo, requisitos funcionales por módulo y diagramas de secuencia. Todo queda provisorio y con evidencia (archivo:línea), y nada pisa lo confirmado. Usar cuando el usuario escriba /documentar-proyecto o pida generar, completar o reconstruir la documentación, los diagramas o los requisitos de un proyecto que ya existe.
---

# Documentar un proyecto existente

Reconstruye la documentación que falta a partir del código. **Lo que el código hace hoy no es necesariamente lo que debería hacer:** por eso todo lo generado queda **provisorio**, cita su evidencia y no alimenta ningún test hasta que el usuario lo confirme. Las reglas de negocio no se infieren: salen como una consulta para que las confirme.

Requiere que el proyecto ya esté adoptado (`/adoptar-proyecto`: crea `docs/`, el README y el relevamiento). Los scripts están en `<esta-skill>/scripts/documentar.py`.

## Etapas

| Etapa | Qué hace | Cuesta |
|---|---|---|
| `estructura` | Diagramas Mermaid: módulos y dependencias, clases por módulo, entidad-relación | script, sin tokens |
| `interfaces` | Requisitos de interfaz (RI): rutas HTTP y variables de entorno | script |
| `dominio` | Requisitos de dominio (RD): una entidad por tabla o modelo | script |
| `adr` | Decisiones de arquitectura (ADR) visibles en el stack | script |
| `reglas` | Una consulta por lotes con reglas de negocio candidatas (umbrales, validaciones, permisos, estados) | script |
| `requisitos` | Requisitos funcionales (RF) por módulo | modelo, por módulo |
| `secuencias` | Diagramas de secuencia de los flujos principales | modelo, por flujo |

## Pasos

1. **Plan (solo lectura).** `python <esta-skill>/scripts/documentar.py plan --raiz <proyecto>` muestra qué se detectó (módulos, clases, tablas, rutas…), qué generaría cada etapa y cuántos tokens cuestan las del modelo. Si no hay código de PHP, JavaScript, TypeScript o Python, lo dice y no hay nada que generar con este paquete.
2. **Mostrar el plan y esperar la aprobación.** El usuario puede pedir solo algunas etapas.
3. **Etapas por script.** Primero sin `--aplicar` (muestra qué crearía), después con `--aplicar`: `python <esta-skill>/scripts/documentar.py todo --raiz <proyecto> --aplicar` (o una etapa suelta). No pisa nada que el usuario haya editado o confirmado; `--refrescar` vuelve a escribir solo lo que sigue provisorio.
4. **Comprobar.** `documentar.py evidencia` (cada cita archivo:línea existe), `verificar.py requisitos diagramas docs` y regenerar el índice (`indexar_docs.py indexar`). Mirar uno o dos diagramas: si algo no tiene sentido, se corrige a mano o se aclara que el análisis no lo ve.
5. **Requisitos funcionales, con el modelo y por módulo.** `documentar.py progreso` lista los módulos y cuáles faltan. Con la aprobación del usuario para cada grupo de módulos, se leen los archivos centrales de cada uno y se escribe cada RF con `documentar.py requisito` (guía en `references/protocolo.md`). Nunca RN.
6. **Secuencias, con el modelo y por flujo.** `documentar.py secuencias` propone los puntos de entrada; se eligen cuatro o cinco, se lee la cadena de llamadas de cada uno, se escribe el diagrama en `.temporal/` y se guarda con `documentar.py secuencia` (rechaza lo que no es legible: máximo 8 participantes y 20 mensajes).
7. **Reglas de negocio.** Mostrarle al usuario `docs/consultas/NN-reglas-candidatas.md` y pedirle que la responda cuando pueda. Lo que confirme se convierte en requisito de negocio vigente, con ejemplos verificables y origen «lo confirmó el usuario», siguiendo `senior-docs`; recién ahí puede tener tests.
8. **Cierre.** Proponer mostrar en el README la arquitectura y los flujos principales (`senior-docs/scripts/readme_diagramas.py listar`; entran con la nota «sin confirmar» mientras sean provisorios, y el usuario los confirma con `documentar.py confirmar-diagrama`). Regenerar el índice, actualizar `docs/ESTADO.md` (qué se generó y qué falta confirmar) y resumir en cinco líneas: cuántos documentos, cuántos provisorios, qué consulta espera respuesta.

## Reglas

- **Provisorio y con evidencia.** Nada se escribe como verdad: estado `provisorio`, origen «inferido del código» y una línea `Evidencia: archivo:línea` que `documentar.py evidencia` comprueba. Un requisito sin evidencia se rechaza.
- **No se infieren reglas de negocio.** Un valor o una condición del código puede ser un error. Van a la consulta, no a requisitos.
- **Nunca se pisa lo confirmado o editado a mano.** Los diagramas generados llevan una marca en la primera línea; sin ella se consideran editados.
- **Por etapas y con costo declarado.** Las etapas del modelo se aprueban una por una; si el proyecto es grande, se retoma en otra sesión con `documentar.py progreso`.
- **El análisis es aproximado.** Usa patrones y no ejecuta nada: puede no ver código dinámico, rutas generadas o relaciones que no están en las importaciones. Dice lo que no cubre, no lo inventa.

## Regla de autoría

En todo lo que se suba a GitHub figura únicamente el usuario; Claude nunca aparece como autor, coautor ni colaborador.
