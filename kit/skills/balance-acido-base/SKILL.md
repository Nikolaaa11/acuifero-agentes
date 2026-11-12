---
name: balance-acido-base
description: "Calcula el balance ácido-base de ensayos estáticos de residuos mineros y clasifica cada muestra como generadora de ácido, incierta o no generadora - potencial de acidez desde el azufre, potencial neto de neutralización, razón entre ambos, pH en pasta y pH de generación neta de ácido, con resumen por unidad geoambiental. Úsala cuando lleguen resultados de caracterización geoquímica de roca estéril, relaves o material de botadero."
---

# Balance ácido-base

Calcula con el script incluido; no clasifiques a mano.

## Datos que necesitas

CSV con una fila por muestra:

```
muestra,grupo,S_total,S_sulfuro,PN,pH_pasta,pH_NAG
MR-01,andesita,0.12,0.08,62,8.4,7.9
```

- `S_sulfuro` y `S_total` en % en peso. Si falta el azufre como sulfuro, el script usa el total y lo avisa: es conservador.
- `PN`, potencial de neutralización, en kg CaCO₃/t. Si el laboratorio lo informa en otra unidad, conviértelo antes y anótalo.
- `grupo` (unidad geoambiental), `pH_pasta` y `pH_NAG` son opcionales pero mejoran mucho la lectura.
- Acepta separador coma o punto y coma, y coma decimal.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/aba.py" ensayos.csv
```

- `--razon-generador 1 --razon-no-generador 2` cambia los cortes de la razón PN/PA.
- `--pnn-limite 20` cambia la banda de incertidumbre del potencial neto (kg CaCO₃/t).
- `--ph-nag 4.5` cambia el corte del pH de generación neta de ácido.
- `--json` entrega todo el detalle.

Para probar: `ejemplos/ensayos-estaticos.csv` (doce muestras ficticias en tres unidades; deben salir 4 generadoras, 4 inciertas y 4 no generadoras).

## Cómo leer el resultado

- **PA = 31,25 × S (%)**, **PNN = PN − PA** y **razón PN/PA**, todo en kg CaCO₃/t.
- Una muestra queda como generadora o no generadora solo cuando la razón y el potencial neto coinciden. Si no coinciden, es **incierta** y el script lo dice.
- Los cortes por defecto (razón 1 y 2; potencial neto ±20) son de uso común, no una norma. Usa los que exija la guía del proyecto y cita su fuente. Si el proyecto aún no define una guía, usa los cortes por defecto, decláralos así y marca la clasificación como preliminar.
- Si el pH de generación neta contradice el balance, hace falta mineralogía o ensayo cinético antes de concluir.
- pH en pasta bajo 5 indica que el material ya tiene acidez almacenada.
- Con menos de tres muestras por unidad, la clasificación de esa unidad es preliminar.
- El script lista las muestras que piden mineralogía o ensayo cinético: las inciertas y aquellas donde el pH de generación neta contradice el balance.
- El resumen por grupo cuenta muestras; no clasifica la unidad completa. No hay una regla universal para pasar de muestras a unidad: informa la proporción de cada clase y, si hay que dar una sola postura, usa la más desfavorable y dilo.

## Qué entregar

La tabla por muestra, el resumen por unidad, las observaciones tal como salen, los criterios usados con su fuente y la lista de unidades que necesitan ensayos cinéticos. La clasificación final de los materiales es de la profesional a cargo.
