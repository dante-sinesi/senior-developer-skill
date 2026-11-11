---
name: cerrar-sesion
description: Cierre ordenado de una sesión de trabajo en un proyecto que usa la metodología senior. Actualiza el estado, regenera el índice, corre el verificador, revisa cambios sin guardar y pendientes, y propone el commit. Usar cuando el usuario escriba /cerrar-sesion o diga que terminó por hoy, que cerramos, que se va o que da por finalizada la sesión.
---

# Cerrar sesión

Cierre opcional y liviano. No es lo único que protege el trabajo (el estado se guarda en cada hito), sino un control de calidad final antes de irse.

## Pasos

1. **Verificar**: ejecutar `python <ruta-de-senior>/scripts/verificar.py` (la skill `senior` está en la misma carpeta que esta). Leer el resumen; no abrir archivos salvo que haya algo marcado.
2. **Estado**: actualizar `docs/ESTADO.md` con tres cosas: dónde quedó el trabajo, el próximo paso concreto y los bloqueos o preguntas abiertas. Marcar en la ficha en curso los pasos que se completaron.
2b. **README**: confirmar que refleja los cambios de la sesión (lo marca `verificar.py readme`); si no, proponer la actualización.
2c. **Portada del repositorio**: si el proyecto está en GitHub, correr `python <ruta-de-senior-git>/scripts/repo_meta.py`; si dice que el proyecto cambió desde la última vez, actualizar la descripción y los Topics (ver `senior-git`) e informarlo en el resumen.
2d. **Escala del proyecto**: correr `python <ruta-de-senior>/scripts/escala.py estado`; si el proyecto creció, la escala sube sola y se menciona en el resumen. No se pregunta nada.
3. **Pendientes**: revisar si hay ítems nuevos en `docs/pendientes.md` o deuda técnica registrada hoy y mencionarlos al usuario en una línea.
4. **Índice**: si se tocó documentación, regenerarlo con `python <ruta-de-senior-memoria>/scripts/indexar_docs.py indexar` e incluir `docs/INDEX.md` en el commit.
5. **Cambios sin guardar**: si hay cambios sin commit, mostrar la lista breve y **proponer** el commit (rama correcta, mensaje convencional en español neutro, **sin Co-Authored-By ni pies de atribución: en GitHub figura solo el usuario**). No commitear ni empujar sin aprobación del usuario.
6. **Resumen final** (máximo cinco líneas): qué se hizo, en qué estado queda, qué sigue.

## Si el proyecto no usa la metodología

Si no existe `docs/ESTADO.md`, no imponerla: resumir lo hecho, mostrar los cambios sin guardar y ofrecer crear la base documental con `senior-docs`.
