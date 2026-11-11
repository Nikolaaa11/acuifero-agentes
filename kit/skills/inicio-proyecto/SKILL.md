---
name: inicio-proyecto
description: "Deja lista la carpeta de un proyecto hidrogeológico o ambiental nuevo - estructura de carpetas, archivo CLAUDE.md con país, normativa, sistema de coordenadas, unidades, nombres de pozos y reglas de confidencialidad, y un registro de datos recibidos. Úsala al comenzar un proyecto o cuando una carpeta de trabajo esté desordenada y los agentes no tengan contexto."
---

# Inicio de proyecto

El objetivo es que cualquier agente del kit entienda el proyecto leyendo un solo archivo.

## Pasos

1. **Pregunta lo mínimo, de una vez.** Nombre corto del proyecto, país y región, tipo de estudio, sistema de coordenadas (datum y huso), unidades preferidas y cómo debe nombrarse al cliente en los documentos (nombre real, código o anónimo). Si la usuaria no sabe algo, déjalo como «por confirmar».
2. **Crea la estructura** dentro de la carpeta actual, sin mover ni borrar lo que exista:

   ```
   00-antecedentes/      bases, estudios previos, bibliografía
   01-datos-originales/  tal como llegaron; no se editan
   02-datos-limpios/     CSV ordenados que usan los scripts
   03-analisis/          ensayos, química, monitoreo, piezometría
   04-modelos/           conceptual y numérico
   05-sig/               capas y proyectos de QGIS
   06-informes/          borradores y versiones
   07-revision/          hallazgos y control de calidad
   ```

3. **Escribe `CLAUDE.md`** en la raíz a partir de `plantilla-CLAUDE.md` (está en la carpeta de esta skill). Completa lo conocido y deja visibles los campos por confirmar.
4. **Crea `01-datos-originales/registro.csv`** con las columnas `fecha_recepcion, archivo, origen, descripcion, sistema_coordenadas, observaciones` y registra los archivos que ya existan.
5. **Resume** lo creado y lista lo que quedó por confirmar.

## Reglas

- No sobrescribas un `CLAUDE.md` existente: propón los cambios y espera el visto bueno.
- No renombres ni muevas archivos del cliente sin preguntar.
- La sección de confidencialidad de `CLAUDE.md` no se elimina. Si la usuaria indica que el proyecto no admite subir datos a servicios externos, anótalo ahí con claridad.
