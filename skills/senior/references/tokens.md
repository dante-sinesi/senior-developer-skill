# Cuidar el contexto

El contexto de una sesión es finito y todo lo que entra se paga en cada vuelta siguiente. Cuidarlo no es un adorno: una sesión que se llena pierde lo que importa y empieza a olvidar. Las reglas de abajo cuestan nada y se aplican siempre.

## Qué se paga, y cuándo

| Se carga | Ejemplo | Cuándo se paga |
|---|---|---|
| Siempre | nombre y descripción de cada skill, `CLAUDE.md`, índice de la memoria, `docs/ESTADO.md` | en cada sesión, se use o no |
| Al activarse | el cuerpo de un `SKILL.md` | cuando la skill entra en juego |
| Si hace falta | `references/`, documentos, código | solo cuando se abre |

Por eso lo que va en lo primero tiene que ser lo mínimo, y el detalle va en lo último. `/auditar-consumo` mide las tres cosas.

## Salidas de comandos

La salida de un comando entra entera en el contexto, también la que no se lee. Antes de correr algo que puede ser largo:
- **Pedir lo justo:** `git log -n 20 --oneline`, `git diff --stat` antes que `git diff`, `pytest -q`, `npm install --silent`, `grep -c` o `-l` antes que `grep` a secas.
- **Acotar:** `| tail -n 30` o `| head -n 50` cuando solo importa el final o el principio. En un fallo, el final suele tener el error.
- **Un chequeo, un resumen:** los scripts del paquete (`verificar.py`, `repo_meta.py`) ya devuelven pocas líneas; se usan en lugar de leer los archivos que revisan.
- **Guardar si hace falta el detalle:** `comando > .temporal/salida.txt` y leer después solo el tramo que interesa (nunca fuera del proyecto).

## Lecturas

- **Buscar antes de leer:** `Grep` o el índice (`indexar_docs.py consultar`, que indica los tokens de cada resultado) en vez de abrir archivos completos.
- **Leer por partes:** un archivo grande se lee con rango de líneas, no entero.
- **No releer lo que ya está en la conversación**, ni volver a leer un archivo recién editado: la herramienta avisa si la edición falló.
- **Un subagente devuelve un resumen:** sirve para exploraciones amplias, pero cada uno parte de cero y cuesta; se pide siempre un informe corto.

## Lo que se escribe para siempre

- **Descripción de una skill:** cuándo se usa y qué hace, en pocas líneas; se paga en cada sesión.
- **Cuerpo de un `SKILL.md`:** por debajo de las 500 líneas, con el detalle en `references/` y una línea que diga cuándo abrirlo.
- **`CLAUDE.md` y memoria:** solo lo que se debe cumplir en cada sesión, y lo que cuesta volver a averiguar. Lo demás va a una skill o a `docs/`.
- **No modificar `CLAUDE.md` ni las skills a mitad de una sesión larga** si se puede esperar: un cambio en lo que se carga al principio obliga a reprocesarlo. Los cambios del paquete se instalan entre sesiones (`python instalar.py`).

## Medir, no suponer

Las estimaciones (caracteres / 4) sirven para comparar. Antes de recortar algo, `auditar-consumo` dice qué pesa de verdad; después de recortar, se vuelve a medir.
