---
name: senior-seguridad
description: Seguridad aplicada al desarrollo bajo la familia ISO/IEC 27000 (27002:2022 controles tecnológicos, 27005 riesgos, 27034 seguridad de aplicaciones). Lente liviana por defecto (lista de revisión por cambio, chequeos automáticos de código, secretos, registros y dependencias) y modo formal con registro de riesgos cuando el proyecto maneja datos personales o sensibles. Usar en cada cambio que toque entradas de usuario, autenticación, datos, bases de datos, archivos, configuración, dependencias o comunicación externa, y antes de abrir un Pull Request. Usar también al registrar requisitos de seguridad.
---

# Seguridad bajo ISO/IEC 27000

La seguridad no es una fase final: es una lente que se aplica a cada cambio. Se usa la familia ISO/IEC 27000 como marco de referencia técnico. Dos advertencias de honestidad:
- Las normas son de pago y tienen derechos de autor: aquí se cita **número y tema** de cada control, parafraseado, nunca el texto.
- Los controles de políticas, personas y seguridad física no se resuelven programando. Se registran como requisitos no funcionales (RNF) o de transición (RT) y se informa al usuario que dependen de la organización.

## Modo liviano (por defecto)

Para cada cambio:
1. **Lista de revisión** (`references/lista-de-revision.md`): unas diez preguntas sobre entradas, autenticación, secretos, datos, registros, dependencias y entornos.
2. **Chequeos automáticos, sin tokens**:
   ```
   python <ruta-de-senior>/scripts/verificar.py seguridad            # alertas de código, secretos, logs
   python <ruta-de-senior>/scripts/verificar.py seguridad --auditar  # suma dependencias (usa la red)
   ```
   Las alertas son heurísticas: se leen como "revisar". Un falso positivo se descarta con `senior-ignore: ID` en la línea.
3. **Trazabilidad**: los requisitos de seguridad son RNF con etiqueta `iso:` (ver `senior-docs`).

## Mapa de controles que ya cubre el flujo

| Control ISO/IEC 27002:2022 | Cómo se cubre en este paquete |
|---|---|
| 8.25 Ciclo de vida de desarrollo seguro | Todo el flujo: tests primero, documentación, revisión, PR |
| 8.26 Requisitos de seguridad de aplicaciones | RNF de seguridad con etiqueta `iso:` |
| 8.27 Arquitectura segura | ADR y diagramas legibles |
| 8.28 Codificación segura | Alertas por lenguaje (perfiles) y lista de revisión |
| 8.29 Pruebas de seguridad | Tests derivados de requisitos y chequeos automáticos |
| 8.31 Separación de entornos | Tests solo contra base de prueba (guardia) |
| 8.33 Información de prueba | Datos de prueba ficticios |
| 8.32 Gestión de cambios | Ramas, commits convencionales, PR |
| 8.8 Vulnerabilidades técnicas | Auditoría de dependencias |
| 8.15 Registros | Alerta de datos sensibles en logs |

El mapeo completo, con qué mirar en cada control, está en `references/mapa-iso-27000.md`.

## Alertas de código (las cinco centrales)

1. SQL armado con datos concatenados (en vez de consultas preparadas).
2. Datos sin escapar al mostrarlos (XSS).
3. Secretos (contraseñas, hashes, tokens) que viajan al cliente.
4. Acciones de servidor sin chequeo de sesión o CSRF.
5. Ejecución dinámica sin lista blanca.

Además: secretos escritos en el código, datos sensibles en logs y dependencias vulnerables. Las reglas viven en los perfiles de `senior/perfiles/`. Los secretos y los datos personales **no se limitan a avisar**: `senior/scripts/secretos.py` los frena al commitear y al subir, y el hook de Claude antes de escribirlos (principio 18 de `senior`, `senior/references/secretos.md`).

## Modo formal con riesgos

Por defecto no se usa. **La skill lo propone** (y el usuario decide) cuando detecta: datos personales o sensibles reales (salud, finanzas, documentos de identidad, menores), exigencias legales o de clientes, o sistemas cuya caída o filtración tendría impacto grave. Incluye todo lo del modo liviano más un **registro de riesgos** por proyecto al estilo ISO/IEC 27005, en `docs/seguridad/riesgos.md` (plantilla en `references/plantilla-riesgos.md`): activo, amenaza, control, nivel de riesgo residual y responsable.

## Excusas frecuentes y qué se responde

Atajos que se ofrecen solos cuando el trabajo aprieta. Si aparece uno de estos pensamientos, es la señal para frenar.

| Excusa | Respuesta |
|---|---|
| «Es una herramienta interna, no hace falta» | Lo interno se filtra y se expone con el tiempo. La lista de revisión se aplica igual; solo se le pone proporción. |
| «Valido en el cliente y listo» | El cliente lo controla quien ataca. Toda entrada se valida en el servidor. |
| «Dejo la clave en el código y la saco después» | Un secreto commiteado se considera comprometido aunque se borre. Va en el entorno desde la primera línea. |
| «Es solo un log, no pasa nada» | Los registros se copian, se envían y se leen. Nunca llevan contraseñas, tokens ni datos personales. |
| «La dependencia la mantiene mucha gente, debe estar bien» | Se audita con `verificar.py seguridad --auditar`; la popularidad no es una revisión. |
| «La alerta del script es un falso positivo» | Puede serlo, pero se confirma leyendo la línea y se deja `senior-ignore: ID` con el motivo, no se ignora en silencio. |

## Cuánto cuesta (orientativo)

Chequeos automáticos: 1 a 5 s y 200 a 1.000 tokens de lectura (la auditoría de dependencias suma unos segundos de red). Revisión con la lista: 500 a 1.500 tokens por cambio. Modo formal: unos 2.000 a 5.000 tokens para armar el registro inicial.
