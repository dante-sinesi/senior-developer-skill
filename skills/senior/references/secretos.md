# Secretos y datos personales: que nunca lleguen a GitHub

Detalle del principio 18 de `SKILL.md`. Se lee cuando se configura la protección, cuando un hook bloquea algo o cuando hay que decidir qué hacer con una clave.

## La regla

Las claves, contraseñas, tokens, certificados y los datos personales (tarjetas, documentos de identidad, listas de clientes) **no se escriben nunca en el código ni en ningún archivo que vaya a git**. Viven en `.env` (que `.gitignore` excluye), el código los lee de una variable de entorno (`os.environ`, `process.env`, `getenv`) y `.env.example` documenta cuáles existen, con valores falsos.

## Cuatro capas, de la más temprana a la que no se saltea

| Capa | Dónde actúa | Qué hace | Se puede saltear |
|---|---|---|---|
| 1. Convención | `.gitignore` y `.env.example` | `secretos.py gitignore --aplicar` completa el `.gitignore`; `verificar.py secretos` avisa si falta o si un `.env` ya está versionado. | Sí: no impide nada por sí sola. |
| 2. Hook de Claude | Antes de cada acción de Claude | Frena escribir una clave en el código, leer o editar `.env` sin permiso, `git add -f` y claves en mensajes de commit o de Pull Request. | Solo con un cambio de configuración, que Claude no puede hacer. |
| 3. Hooks de git | `pre-commit` y `pre-push` | Revisan lo preparado y **todo el historial que se va a subir**, commit por commit (una clave agregada y borrada después igual viaja). Valen también cuando commitea el usuario a mano. | Con `--no-verify`. |
| 4. GitHub | Servidor | Escaneo de secretos y protección de subida (`secretos.py github` comprueba si están activos). | No. Gratis en repositorios públicos. |

## `.env` con permiso del usuario

`.env` se puede leer y modificar, pero **con permiso** y **proponiéndolo**:

1. **Sin permiso**, Claude trabaja con `env_gestion.py`: `estructura` muestra los nombres de las variables con los valores ocultos (qué hay y qué falta) y `declarar NOMBRE --comentario "para qué sirve"` agrega la variable a `.env.example` con un valor falso. Con eso alcanza para casi todo.
2. Cuando hace falta algo en `.env` (declarar variables nuevas, darle estructura), Claude **se lo propone al usuario**: qué variables y para qué, y que puede autorizarlo escribiendo en el chat `/permitir .env`. Si trabaja sin supervisión, lo anota en `docs/pendientes.md` y sigue leyendo la variable de entorno.
3. **Con `/permitir .env`**, Claude puede leerlo y editarlo directamente, y `declarar` también agrega las variables a `.env` (sin valor: el valor real lo completa el usuario). El permiso vale para ese archivo, no para las demás claves.
4. Leerlo es una forma de filtrarlo: lo que Claude lee queda en el contexto y en el historial de la sesión. Por eso el permiso de lectura es explícito.

## Cuando un hook bloquea algo

- **Una clave en el código:** pasarla a `.env`, leerla de la variable de entorno y declararla con `env_gestion.py declarar`.
- **Un falso positivo** (un ejemplo de la documentación, un dato de prueba): comentario `senior-ignore: <ID> motivo` en la misma línea o en la anterior. El motivo es obligatorio en la práctica: sin él nadie sabe por qué se ignoró.
- **Una clave que ya se subió:** borrarla no alcanza, porque queda en el historial y en las copias. Hay que **rotarla** (generar una nueva y dar de baja la vieja) y recién después limpiar el historial si hace falta.
- **Un archivo secreto ya versionado:** `git rm --cached <archivo>`, agregarlo a `.gitignore` y rotar lo que contenía.

## Límites

- Se detectan formatos conocidos y asignaciones literales; una clave partida, codificada o con un formato que no está en la lista pasa. Por eso existe la capa 4.
- En un **frontend** (Vite, Next, Create React App) las variables de entorno se incrustan en lo que baja el navegador: ahí no hay secretos posibles. Una clave que importa va en un servidor.
- `.env` queda en texto plano en el disco. Para producción hace falta un gestor de secretos del proveedor; esta capa no lo reemplaza.
- No se ve lo que lee o escribe un script que está en un archivo, solo el código que viaja dentro del comando.
