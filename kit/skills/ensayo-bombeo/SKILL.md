---
name: ensayo-bombeo
description: "Interpreta un ensayo de bombeo o de recuperación a partir de una planilla de tiempo y descenso - ajusta Cooper-Jacob y Theis, y entrega transmisividad, almacenamiento y conductividad con sus advertencias. Úsala cuando haya datos de un ensayo de bombeo, cuando pidan T, K o S de un pozo, o para comprobar una interpretación existente."
---

# Ensayo de bombeo

Calcula con el script incluido; no hagas el ajuste a mano ni de memoria.

## Datos que necesitas

- CSV con dos columnas: `t_min` (minutos desde el inicio del bombeo) y `s_m` (descenso en metros). Acepta separador coma o punto y coma, y coma decimal.
- Caudal constante en L/s.
- Distancia `r` en metros entre el pozo de bombeo y el de observación. Sin `r` solo se obtiene T.
- Opcional: espesor saturado `b` en metros, para obtener K = T/b.

Si la planilla trae profundidad de nivel en vez de descenso, resta el nivel estático antes. Si trae horas o segundos, pásalo a minutos. Deja el CSV limpio en la carpeta de trabajo del proyecto (por ejemplo `02-datos-limpios/`), nunca dentro de la carpeta de la skill.

## Cómo correrlo

La carpeta de esta skill aparece al cargarla. En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/ensayo_bombeo.py" datos.csv --q 12 --r 35 --b 40
```

Opciones útiles:

- `--tmin 30 --tmax 600` fija a mano el tramo recto de Cooper-Jacob (en minutos).
- `--pozo-bombeo` avisa que los datos son del propio pozo de bombeo (S no es confiable).
- `--recuperacion --tp 1440` interpreta descenso residual; `t_min` sigue contando desde el inicio del bombeo y `--tp` es la duración del bombeo. Usa las lecturas más cercanas al final de la recuperación e informa el tramo. No genera gráfico.
- `--grafico ajuste.png` guarda el gráfico semilogarítmico (requiere matplotlib).
- `--json` entrega los resultados para seguir procesándolos.

Para probar: `ejemplos/ensayo-bombeo.csv` (pozo de observación a r = 35 m, Q = 12 L/s; debe dar T cerca de 450 m²/d y S cerca de 2·10⁻⁴) y `ejemplos/recuperacion.csv` (el mismo pozo; con `--q 12 --recuperacion --tp 1440` debe dar T cerca de 450 m²/d).

## Cómo leer el resultado

- La sección **Diagnóstico** entrega la derivada del descenso, ds/d(ln t). Estable al final: flujo radial, y Theis y Cooper-Jacob valen. Si cae: goteo, recarga o borde de nivel constante. Si sube: borde impermeable o caudal en aumento. El gráfico log-log, si hace falta, se arma aparte con matplotlib.
- Si Theis y Cooper-Jacob coinciden y R² es alto, el acuífero se comporta como confinado ideal en ese tramo.
- Si el script advierte que u supera 0,05, Cooper-Jacob no vale en esos tiempos: usa Theis o tiempos más largos.
- S fuera de 10⁻⁶ a 0,4, o métodos que difieren más de 50 %, indican que el modelo no corresponde (goteo, drenaje diferido, bordes, caudal variable) o que hay un error de unidades o de distancia.
- El script no cubre Hantush, Neuman, ensayos escalonados ni slug tests. Para esos casos escribe el cálculo aparte y dilo.

## Qué entregar

Tabla de resultados por método, el tramo de datos usado, el diagnóstico, las advertencias tal como salen, el comando exacto y una recomendación de T, K y S con su rango y confiabilidad. El rango se arma comparando métodos, tramos y pozos: es la dispersión entre estimaciones, no un intervalo de confianza, y así debe decirse. La elección final es de la profesional a cargo.
