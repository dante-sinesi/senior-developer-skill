# Mapa de la familia ISO/IEC 27000 para desarrollo

Nota: las normas ISO son propiedad de sus editores y de pago. Este documento solo nombra los controles y resume, con palabras propias, qué mirar en un proyecto de software. Para el texto normativo, consultar la norma.

## Contenido
1. Qué norma sirve para qué
2. Controles tecnológicos de ISO/IEC 27002:2022 relevantes para el código
3. Qué queda fuera del alcance del código
4. Etiquetado de requisitos

## 1. Qué norma sirve para qué

| Norma | Tema | Uso en este paquete |
|---|---|---|
| ISO/IEC 27001 | Sistema de gestión de seguridad de la información (organización) | Contexto: explica por qué existen controles; no se "implementa" desde el código |
| ISO/IEC 27002:2022 | Catálogo de controles | Fuente principal: controles tecnológicos (sección 8) |
| ISO/IEC 27005 | Gestión de riesgos | Base del modo formal (registro de riesgos) |
| ISO/IEC 27034 | Seguridad de aplicaciones | Orientación para requisitos y pruebas de seguridad en el ciclo de vida |
| ISO/IEC 27701 | Privacidad (extensión de 27001/27002) | Referencia cuando hay datos personales |
| ISO/IEC 27017 / 27018 | Nube / datos personales en nube | Referencia si el sistema corre en la nube |

## 2. Controles tecnológicos relevantes (27002:2022)

| N.º | Tema | Qué mirar en un proyecto |
|---|---|---|
| 8.2 | Derechos de acceso privilegiado | Mínimo privilegio en cuentas de base de datos, tokens y servicios |
| 8.3 | Restricción de acceso a la información | Permisos verificados en el servidor para cada acción y dato |
| 8.4 | Acceso al código fuente | Repositorio con acceso controlado; sin secretos versionados |
| 8.5 | Autenticación segura | Sesiones, hash de contraseñas, bloqueo ante intentos repetidos |
| 8.8 | Gestión de vulnerabilidades técnicas | Auditar y actualizar dependencias |
| 8.9 | Gestión de la configuración | Configuración por entorno, sin valores sensibles en el código |
| 8.11 | Enmascaramiento de datos | No mostrar ni registrar datos sensibles completos |
| 8.15 | Registros | Registrar eventos relevantes sin incluir datos sensibles |
| 8.24 | Uso de criptografía | Algoritmos estándar, cifrado en tránsito, claves bien gestionadas |
| 8.25 | Ciclo de vida de desarrollo seguro | El flujo completo de este paquete |
| 8.26 | Requisitos de seguridad de aplicaciones | RNF de seguridad documentados y verificables |
| 8.27 | Arquitectura e ingeniería seguras | Decisiones de diseño registradas (ADR), separación de responsabilidades |
| 8.28 | Codificación segura | Validación de entradas, consultas parametrizadas, escape de salidas |
| 8.29 | Pruebas de seguridad | Tests de reglas de seguridad y chequeos automáticos |
| 8.30 | Desarrollo externalizado | Revisión del código y requisitos si lo escribe un tercero |
| 8.31 | Separación de desarrollo, prueba y producción | Pruebas solo en base de prueba |
| 8.32 | Gestión de cambios | Ramas, PR, revisión y trazabilidad |
| 8.33 | Información de prueba | Datos de prueba ficticios; nunca datos reales sin proteger |
| 5.17 | Información de autenticación | Gestión de contraseñas y claves |
| 5.34 | Privacidad y protección de datos personales | Minimizar datos personales; proponer modo formal |

## 3. Qué queda fuera del alcance del código

Controles organizacionales (políticas, roles, proveedores), de personas (capacitación, acuerdos) y físicos (accesos a instalaciones, equipos). El código no los resuelve: se registran como RNF o RT que dependen de la organización, indicando quién debería encargarse, para que no se den por cubiertos sin estarlo.

## 4. Etiquetado de requisitos

En el encabezado de un requisito: `iso: 8.28` (o varios: `iso: 8.28, 8.26`). El índice usa las etiquetas para mostrar qué controles tienen requisito, test y código asociados.
