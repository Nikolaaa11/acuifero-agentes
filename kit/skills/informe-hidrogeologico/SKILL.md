---
name: informe-hidrogeologico
description: "Entrega la estructura y las reglas de redacción de informes técnicos de hidrogeología y geología ambiental - línea de base hidrogeológica, informe de ensayo de bombeo, informe de monitoreo o seguimiento y minuta técnica, con índice, contenido mínimo de cada capítulo y lista de chequeo final. Úsala al empezar a redactar cualquiera de esos documentos o para ordenar un borrador."
---

# Informes hidrogeológicos

Parte siempre de un índice, no de una página en blanco. Las plantillas están en la carpeta `plantillas/` de esta skill:

| Documento | Plantilla |
|---|---|
| Línea de base o caracterización hidrogeológica | `plantillas/linea-base.md` |
| Informe de ensayo de bombeo | `plantillas/ensayo-bombeo.md` |
| Informe de monitoreo o seguimiento | `plantillas/monitoreo.md` |
| Minuta técnica de dos páginas | `plantillas/minuta.md` |

## Cómo usarlas

1. Copia la plantilla a `06-informes/` del proyecto con un nombre que incluya fecha y versión.
2. Ajusta el índice a lo que exijan las bases, la guía de la autoridad o el formato de la empresa. Si hay conflicto, mandan las bases.
3. Completa cada capítulo solo con resultados que existan en la carpeta del proyecto. Lo que falte queda escrito como **[PENDIENTE: qué falta]**.
4. Arma la tabla de trazabilidad mientras escribes, no al final.

## Reglas de redacción

- Conclusión primero, respaldo después. Un párrafo, una idea.
- Cifras con unidad, separador decimal coma y las cifras significativas que el método permite (una transmisividad de 452,37 m²/d no existe: es 450 m²/d).
- Tablas y figuras numeradas, con título arriba (tablas) o abajo (figuras), fuente, y citadas en el texto antes de aparecer.
- Resultados e interpretación en apartados distintos.
- Nombres de pozos, unidades hidrogeológicas y sistema de coordenadas idénticos en todo el documento.
- Siglas: la primera vez, escritas completas.
- Las referencias se citan como autor y año, y la lista final solo incluye lo citado.

## Lista de chequeo final

- [ ] El resumen ejecutivo responde al objetivo y sus cifras coinciden con las del cuerpo.
- [ ] Cada cifra tiene su fila en la tabla de trazabilidad.
- [ ] Todas las tablas y figuras están citadas y numeradas en orden.
- [ ] Los mapas llevan escala, norte, leyenda, sistema de coordenadas y fuente.
- [ ] Unidades y conversiones revisadas con `unidades-hidro`.
- [ ] Supuestos y limitaciones escritos en su propia sección.
- [ ] No quedan marcas de **[PENDIENTE]** sin informar a la autora.
- [ ] Pasó por `hidro-revisor`.
