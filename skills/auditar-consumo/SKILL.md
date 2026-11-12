---
name: auditar-consumo
description: Audita cuánto contexto consumen las skills, los CLAUDE.md, la memoria y el estado del proyecto, y propone qué recortar primero. Distingue lo que se paga en cada sesión (descripciones de skills, instrucciones, índice de la memoria) de lo que se paga al activarse una skill (su cuerpo) y de lo que se lee solo si hace falta (references). Solo lee y no modifica nada. Usar cuando el usuario escriba /auditar-consumo o pida revisar, medir o reducir el consumo de tokens, el peso de las skills o de CLAUDE.md, o saber por qué las sesiones se llenan rápido.
---

# Auditar consumo

Mide dónde se va el contexto y propone qué recortar. No se carga solo: se usa cuando el usuario lo pide, así que no suma nada al consumo fijo.

## Pasos

1. **Medir** (solo lectura, sin gastar tokens del modelo). Si el proyecto es un paquete de skills (tiene una carpeta `skills/`) y se quiere ver el efecto de un recorte antes de reinstalar, agregar `--repo`: mide las skills del repositorio en lugar de las instaladas.
   ```
   python <esta-skill>/scripts/consumo.py --raiz <proyecto> [--salida .temporal/consumo.md]
   ```
   Imprime un resumen corto: el consumo fijo (lo que se paga en cada sesión), las skills que más pesan siempre y al activarse, los ajustes (hooks, permisos, servidores MCP), la memoria y una lista de cosas para revisar. Con `--salida` deja además el informe completo en `.temporal/`, que git ignora.
2. **Leer el resumen, no los archivos.** El script ya los midió. Presentar al usuario en pocas líneas: cuánto es el consumo fijo, qué tres cosas pesan más y qué rinde más por menos esfuerzo.
3. **Proponer, ordenado por rendimiento.** Los recortes habituales, de mayor a menor efecto:
   - descripciones largas de skills (se pagan en cada sesión): dejar solo cuándo se usa y qué hace;
   - cuerpos de `SKILL.md` grandes: mover el detalle a `references/`, que se lee solo si hace falta;
   - `CLAUDE.md` y memoria: dejar lo que se debe cumplir en cada sesión; lo demás, a una skill o a un documento;
   - `ESTADO.md` largo: pasar lo viejo a `docs/historial/`;
   - servidores MCP de más: cada uno suma las definiciones de sus herramientas.
4. **Nada se aplica sin aprobación.** Esta skill solo mide y propone. Cada recorte es un cambio aparte, con las reglas de `senior`, y se vuelve a medir después para comprobar el efecto.

## Cómo leer los números

- Son **estimaciones** (caracteres / 4, margen de ±30 %): sirven para comparar y priorizar, no para facturar.
- Los umbrales son heurísticas. Una skill con un cuerpo grande puede estar bien si casi nunca se activa; lo que importa es lo que se paga siempre.
- **No se mide:** las definiciones de las herramientas de los servidores MCP, las skills de plugins, el prompt de sistema ni el historial de la conversación. Si el consumo fijo medido es bajo y las sesiones igual se llenan, el problema está ahí o en las salidas largas de los comandos (ver `senior/references/tokens.md`).
- Los datos de la máquina del usuario (rutas, memoria, ajustes) quedan en la conversación o en `.temporal/`; no se escriben en el README ni en `docs/`.

## Regla de autoría

En todo lo que se suba a GitHub figura únicamente el usuario; Claude nunca aparece como autor, coautor ni colaborador.
