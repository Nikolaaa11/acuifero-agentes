---
name: mapa-piezometrico
description: "Genera una vista rápida de la piezometría a partir de pozos con coordenadas y nivel - curvas en GeoJSON para abrir en QGIS, grilla interpolada, vista previa en SVG, gradiente hidráulico regional y dirección de flujo. Úsala para mirar un conjunto de niveles, estimar gradiente y sentido del flujo o preparar la base de un mapa piezométrico."
---

# Mapa piezométrico rápido

Calcula con el script incluido.

## Datos que necesitas

CSV con una fila por pozo y coordenadas proyectadas en metros (por ejemplo UTM), todas en el mismo sistema:

```
punto,x,y,nivel
P-01,500350,7400420,482.15
```

- `nivel` es la cota piezométrica en m s. n. m. Si en cambio hay `cota` y `profundidad`, el script calcula nivel = cota − profundidad.
- Niveles de la misma fecha o campaña y del mismo acuífero. No mezcles pozos de unidades distintas ni pozos en bombeo con pozos en reposo.
- Acepta separador coma o punto y coma, y coma decimal.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/piezometria.py" niveles.csv --intervalo 5 --epsg 32719 --salida piezometria
```

- `--intervalo` equidistancia de las curvas en metros (si no se indica, la elige sola).
- `--epsg` código del sistema de coordenadas, para que QGIS ubique el GeoJSON. Confírmalo con el proyecto; no lo supongas.
- `--celda` tamaño de celda de la grilla; `--potencia` exponente de la distancia inversa (2 por defecto).
- `--salida` carpeta donde deja `curvas.geojson`, `grilla.asc` y `vista.svg`.

Para probar: `ejemplos/piezometria.csv` (14 pozos ficticios; el flujo debe salir hacia el suroeste con gradiente cercano a 0,4 %).

## Cómo leer el resultado

- **Gradiente regional y dirección de flujo** salen de un plano ajustado a todos los puntos. Si el R² del plano es bajo, hay curvatura, bombeo o más de un sistema, y un único gradiente no representa la zona.
- **Las curvas** se interpolan por distancia inversa: tienden a formar «ojos» alrededor de cada pozo y no conocen ríos, bordes impermeables ni conos de bombeo. Son un borrador para mirar los datos.
- Fuera del polígono que encierra los pozos la superficie es extrapolación.

## Qué entregar

El resumen (puntos, rango de niveles, gradiente, dirección de flujo), los tres archivos y una nota que diga con claridad que el mapa final requiere ajuste con criterio hidrogeológico. Para el plano definitivo trabaja con `hidro-sig`.
