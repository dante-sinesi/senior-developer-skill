# Lista de revisión de seguridad por cambio

Responder solo las que apliquen al cambio. "No aplica" es una respuesta válida; un "no sé" se convierte en una pregunta al usuario o en un pendiente.

1. **Entradas.** ¿Todo dato que llega de afuera (formularios, URL, archivos, APIs) se valida y se trata como no confiable? (8.28)
2. **Consultas.** ¿Las consultas a base de datos son preparadas o parametrizadas, sin concatenar datos? (8.28)
3. **Salidas.** ¿Lo que se muestra en pantalla está escapado según el contexto (HTML, atributos, URL, JS)? (8.28)
4. **Autenticación y sesión.** ¿Las acciones sensibles exigen sesión válida, con permiso verificado en el servidor (no solo ocultando botones) y protección CSRF donde aplique? (8.5, 8.3)
5. **Secretos.** ¿Hay contraseñas, claves o tokens en el código, en el historial o en configuración versionada? ¿Las contraseñas se guardan con hash adecuado? (5.17, 8.24)
6. **Datos hacia el cliente.** ¿Se serializa algo que no debería salir (hashes, tokens, datos de otros usuarios)? (8.28)
7. **Registros.** ¿Los logs incluyen datos sensibles? ¿Se registran los eventos de seguridad relevantes? (8.15)
8. **Dependencias.** ¿Se agregó o actualizó alguna? ¿Se auditó (`--auditar`)? ¿Es de fuente confiable y mantenida? (8.8)
9. **Entornos y pruebas.** ¿Las pruebas usan solo base y datos de prueba ficticios? ¿Hay configuración distinta por entorno? (8.31, 8.33)
10. **Datos personales.** ¿El cambio recolecta o expone datos personales? Si es así, proponer al usuario el modo formal. (5.34)
11. **Mínimo privilegio.** ¿Las cuentas, tokens y permisos nuevos tienen solo lo necesario? (8.2)
12. **Reversión.** ¿Hay forma de volver atrás si el cambio resulta inseguro? (8.32)

Registrar el resultado en la sección "Seguridad" del PR, con los hallazgos y su resolución.
