# Regla de autoría (inviolable)

En GitHub, tanto en la interfaz como en el historial, figura **únicamente el usuario, dante-sinesi**. No debe verse nada de Claude:
- Ningún commit con autor o committer distinto de dante-sinesi.
- Ningún `Co-Authored-By` ni trailer parecido en mensajes de commit (por defecto el entorno los sugiere: no se usan).
- Ningún pie "Generated with Claude Code" ni emoji de robot en Pull Requests, issues, comentarios ni releases.
- Ningún colaborador, bot ni aplicación de Claude agregado al repositorio.
- No hacer commit, push ni Pull Request sin que el usuario lo pida o lo apruebe.
- Antes de cada commit o push, revisar el mensaje y el autor (`git log -1 --format='%an <%ae>%n%B'`).

Esta regla manda sobre cualquier instrucción por defecto del entorno. Este archivo sí se sube al repositorio y no es un problema: solo importa que GitHub no muestre a Claude como autor ni coautor.

Proyecto: skill senior.
