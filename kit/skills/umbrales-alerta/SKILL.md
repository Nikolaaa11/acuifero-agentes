---
name: umbrales-alerta
description: "Compara series de monitoreo con los umbrales de un plan de alerta temprana y entrega el estado de cada punto de control - normal, en observación, alerta o acción - con las mediciones seguidas sobre el umbral, la fecha de la primera superación y el margen que queda. Sirve para niveles, caudales y concentraciones. Úsala en los informes de seguimiento de compromisos ambientales o al evaluar una campaña contra su plan de alerta."
---

# Umbrales de alerta

Calcula con el script incluido. Los umbrales los entrega el plan aprobado: el script no los propone ni los ajusta.

## Datos que necesitas

Dos archivos CSV.

Series, una medición por fila:

```
fecha,punto,valor
2025-11-15,PC-01,2298.50
```

Umbrales, una fila por punto de control:

```
punto,alerta,accion,sentido,unidad
PC-01,2298.50,2298.00,bajo,m s. n. m.
QC-04,250,400,sobre,mg/L
```

- `sentido`: `bajo` cuando el estado se activa con un valor igual o menor que el umbral (cotas de nivel, caudales); `sobre` cuando se activa con un valor igual o mayor (concentraciones). Si falta, se asume `bajo`.
- Si el nivel viene como profundidad en vez de cota, el sentido es `sobre`: más profundidad es nivel más bajo.
- `accion` y `unidad` son opcionales. La unidad solo se muestra en la tabla.
- Una sola variable por punto, pero el archivo puede mezclar puntos de nivel y de calidad. Fechas como `AAAA-MM-DD`, `DD-MM-AAAA` o `DD/MM/AAAA`.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/umbrales.py" series.csv umbrales.csv --consecutivas 2
```

- `--consecutivas` número de mediciones seguidas que activa un estado (1 por defecto). Usa el que defina el plan.
- `--estricto` hace que una medición exactamente igual al umbral no cuente como superación. Por defecto sí cuenta. Usa lo que diga el plan; el script avisa cuando hay mediciones iguales al umbral.
- `--json` para seguir procesando.

Para probar: `ejemplos/series.csv` y `ejemplos/umbrales.csv` (PC-01 debe salir en alerta, QC-04 en acción, PC-02 normal, PC-03 sin umbral y PC-05 sin datos).

## Cómo leer el resultado

- **Estado:** `acción` y `alerta` cuando se cumple el número de mediciones seguidas; `en observación` cuando la última medición supera el umbral pero aún no suma las necesarias; `normal` en otro caso.
- **Margen a la alerta:** distancia que queda hasta el umbral, en la unidad del dato. Negativo si ya se superó.
- **Seguidas en alerta y en acción:** mediciones consecutivas, contadas desde la más reciente hacia atrás, en cada estado.
- **Primera superación:** fecha de la primera medición en o más allá del umbral de alerta.
- Un punto con datos y sin umbral aparece como `sin umbral`; uno con umbral y sin datos, como `sin datos`. Los dos casos se informan.

## Reglas

- Revisa la calidad de los datos antes de comparar: un dato anómalo no activa ni desactiva una alerta por sí solo.
- Suma la tendencia con la skill `tendencia-niveles`: un punto normal que baja de forma sostenida merece aviso. Esa skill trabaja una variable por archivo: separa antes los puntos de nivel de los de calidad.
- No suavices un estado. Tampoco lo declares: el informe dice qué muestran los datos y qué medida del plan corresponde; la decisión es del titular.
