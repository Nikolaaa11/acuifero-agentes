---
name: calibracion-modelo
description: "Calcula los estadísticos de calibración de un modelo numérico de aguas subterráneas a partir de una tabla de valores observados y simulados - error medio, error medio absoluto, RMSE, RMSE normalizado, R², sesgo y mayores residuales, en total y por capa o zona. Úsala al calibrar un modelo de flujo, al revisar el modelo de un tercero o al documentar la calibración en un informe."
---

# Estadísticos de calibración

Calcula con el script incluido.

## Datos que necesitas

CSV con una fila por punto de control:

```
punto,grupo,observado,simulado
OB-01,capa 1,470.42,470.95
```

- `grupo` es opcional (capa, zona, tipo de dato). Con él se entregan estadísticos separados.
- Observado y simulado en la misma unidad y para la misma fecha o período.
- Acepta separador coma o punto y coma, y coma decimal.
- Para calibración transitoria, usa una fila por punto y fecha, o corre el script por período.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/calibracion.py" calibracion.csv --umbral 10 --unidad m
```

- `--umbral` RMSE normalizado de referencia en porcentaje (10 por defecto).
- `--peores` cuántos residuales mayores listar.
- `--json` para seguir procesando o graficar.

Para probar: `ejemplos/calibracion.csv` (18 puntos ficticios en dos capas; la capa 2 trae un sesgo positivo a propósito).

## Cómo leer el resultado

- **Residual = simulado − observado.** Positivo: el modelo sobreestima.
- **Error medio** cercano a cero indica ausencia de sesgo global; no dice nada del ajuste punto a punto.
- **RMSE normalizado** = RMSE dividido por el rango de los valores observados. El umbral de 10 % es una convención de uso común: aplica el criterio que exija la guía o el cliente del proyecto y cita de dónde sale.
- Un buen estadístico global puede esconder un mal ajuste local. Revisa siempre los mayores residuales, su ubicación y si un grupo calibra peor que el resto.
- Los estadísticos no reemplazan la revisión del balance de masa ni la coherencia de los parámetros calibrados con el modelo conceptual.

## Qué entregar

La tabla de estadísticos (total y por grupo), los mayores residuales, la lectura y, si hay matplotlib, el gráfico de simulado contra observado con la recta 1:1. Indica qué puntos conviene revisar antes de dar la calibración por buena.
