# Etiquetas y formularios

Un problema muy frecuente en la interfaz generada por IA: campos sin etiqueta, con etiquetas ambiguas o con varias etiquetas casi iguales que se confunden. Esta política es estricta y la verifica `revisar_diseno.py etiquetas`.

## Contenido
1. Reglas de las etiquetas
2. Ejemplos
3. Inventario de campos
4. Contrato de campos
5. Errores, ayudas y grupos

## 1. Reglas de las etiquetas

1. **Todo campo tiene una etiqueta visible y permanente**, asociada al campo (`<label for>` o el campo dentro del `<label>`). El placeholder **nunca** la reemplaza: solo da un ejemplo ("Ej: 11 2345 6789"). Un `aria-label` sin texto visible no alcanza.
2. **Cada etiqueta es única dentro del formulario.** Dos campos "Nombre" se confunden: pasan a ser "Nombre del titular" y "Nombre del contacto", o se agrupan bajo un título de grupo.
3. **Cada etiqueta es específica.** Se evitan las genéricas ("Dato", "Información", "Texto", "Campo 1", "Otro") y las ambiguas ("Fecha": ¿cuál?, mejor "Fecha de entrega").
4. **Sin etiquetas casi iguales.** "Dirección de envío" y "Dirección de facturación" se distinguen por la palabra que importa, puesta al principio; no por una letra.
5. **Vocabulario de la persona**, en sustantivo corto (de dos a cuatro palabras), con una gramática consistente en todo el formulario.
6. **Tipo y teclado correctos:** `type="email"`, `type="tel"`, `inputmode="numeric"`; y `autocomplete` para lo que el navegador ya sabe (nombre, correo, teléfono, dirección).
7. **Opciones agrupadas:** radios y casillas dentro de un `<fieldset>` con `<legend>` que explique la pregunta.
8. **Obligatorios y opcionales:** marcar la minoría ("(opcional)") para no llenar el formulario de asteriscos.

## 2. Ejemplos

| Mal | Bien | Por qué |
|---|---|---|
| Solo placeholder "Nombre" | Etiqueta "Nombre y apellido" + ejemplo | La etiqueta no desaparece al escribir |
| "Nombre" y "Nombre" | "Nombre del titular" y "Nombre de quien retira" | Dejan de confundirse |
| "Dirección" y "Dirección 2" | "Calle y número" y "Piso y departamento" | Cada uno dice qué dato pide |
| "Fecha" | "Fecha de entrega" | Responde a "¿cuál?" |
| "Dato" | "Código del producto" | Es lo que la persona reconoce |

## 3. Inventario de campos

Se arma **antes de diseñar** cada formulario y lo aprueba el usuario. No se inventa: se deduce, en este orden, de:
1. los requisitos y las reglas de negocio (`docs/requisitos/`),
2. el modelo de datos (esquema, clases de dominio, contratos de API),
3. las respuestas del usuario (¿qué pasa si este dato falta? ¿quién lo usa y cuándo?),
4. el comportamiento del sistema actual.

Cada campo se clasifica: **ahora** (imprescindible), **derivable** (se completa solo), **avanzado** (opcional, en un desplegable), **después** (se pide más adelante) o **descartar** (ninguna regla lo usa). Plantilla: `plantillas/inventario-campos.md`.

## 4. Contrato de campos

Resultado final: `docs/diseno/campos/<formulario>.md` con la **etiqueta final** de cada campo, su tipo, su clasificación y su fuente. Quien implementa usa esas etiquetas **exactamente**, sin reescribirlas: así no reaparecen nombres ambiguos al programar. Si hace falta cambiar una, se pide al diseñador.

## 5. Errores, ayudas y grupos

- **Ayudas** asociadas al campo (`aria-describedby`): formato esperado, unidad ("kg"), límites.
- **Errores** junto al campo, con texto específico que diga qué corregir ("Falta el código postal de 4 dígitos"), nunca solo en rojo.
- **Grupos:** agrupar por cercanía y con título lo que se relaciona; el orden sigue el modelo mental de la persona, no el del esquema de datos.
- **Validar en línea** cuando la persona termina el campo, no mientras escribe.
