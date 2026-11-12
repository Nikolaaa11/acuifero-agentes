---
name: balance-aguas
description: "Cierra el balance de aguas de una cuenca o de un componente minero como un depósito de relaves, un botadero, un rajo o una pila - suma entradas, salidas y variación de almacenamiento por período, calcula el error de cierre y muestra el peso de cada término. Úsala al armar o revisar un balance hídrico, cuando pregunten si un balance cierra, o para encontrar el término que explica un descuadre."
---

# Balance de aguas

Calcula con el script incluido.

## Datos que necesitas

CSV con una fila por término del balance, todos en la misma unidad:

```
periodo,componente,tipo,valor
2025-01,Agua con la pulpa,entrada,1200000
2025-01,Evaporación,salida,95000
2025-01,Variación de la laguna,almacenamiento,10000
```

- `tipo`: `entrada`, `salida` o `almacenamiento`. El almacenamiento es positivo cuando aumenta.
- `periodo` es opcional (mes, año, escenario). Sin él, todo se trata como un solo período.
- Acepta separador coma o punto y coma, y coma decimal.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/balance_aguas.py" balance.csv --unidad "m3/mes"
```

- `--tolerancia 5` error de cierre aceptable en porcentaje (5 por defecto).
- `--json` para seguir procesando.

Para probar: `ejemplos/balance-relaves.csv` (tres meses ficticios de un depósito de relaves; enero y marzo cierran y febrero queda para revisar con cerca de +5,6 %).

## Cómo leer el resultado

- **Cierre = entradas − salidas − variación de almacenamiento.** Positivo: sobran entradas o faltan salidas.
- **Error (%)** = 100 × cierre dividido por el mayor entre entradas y salidas.
- **Estado:** cierra (dentro de la tolerancia), revisar (hasta el doble) o no cierra.
- Si el error tiene el mismo signo en todos los períodos, hay un término mal estimado o ausente; si cambia de signo, es más probable que sea ruido de medición.
- La tabla de pesos muestra qué términos dominan: ahí es donde un error de estimación mueve el balance.
- Sin término de almacenamiento, el balance supone régimen permanente. Dilo.

## Reglas

- Un balance que no cierra se investiga. No ajustes un término poco conocido (infiltración, evaporación) solo para que cuadre sin decir que lo hiciste.
- Cada término lleva su fuente: medido, calculado o estimado, y con qué método.
- La tolerancia de 5 % es una convención: usa la que exija el proyecto.
