---
name: salares
description: "Hace dos cálculos frecuentes en salares y cuencas cerradas - convierte niveles medidos en salmueras a carga equivalente de agua dulce usando la densidad y la cota del tramo captado, y ajusta la curva de evaporación contra profundidad del nivel freático desde mediciones de terreno. Úsala cuando haya que comparar niveles entre pozos con aguas de distinta densidad o procesar una campaña de evaporación."
---

# Salares: carga equivalente y evaporación

Calcula con el script incluido. Tiene dos órdenes: `carga` y `evaporacion`.

## Carga equivalente de agua dulce

CSV con una fila por pozo:

```
punto,nivel,cota_filtro,densidad
SB-01,2300.50,2280.00,1205
```

- `nivel`: cota del nivel medido en el pozo, en m s. n. m.
- `cota_filtro`: cota del punto medio del tramo captado, en m s. n. m.
- `densidad`: del agua del pozo, en kg/m³ o en g/cm³. Un valor menor que 5 se lee como g/cm³ y el script lo avisa.
- Niveles de la misma campaña. Anota la fecha en el informe; el script no la usa.

```
python "<carpeta de la skill>/scripts/salares.py" carga niveles.csv
```

Usa h_dulce = z + (ρ/ρ_dulce) × (h − z). Con `--densidad-dulce` cambias la densidad de referencia (1000 kg/m³ por defecto).

Para probar: `ejemplos/niveles-densidad.csv` (SB-01 debe dar 2304,70 m s. n. m.).

**Cómo leerlo.** La carga equivalente sirve para comparar niveles en horizontal entre pozos de distinta densidad y trazar la piezometría, siempre que los pozos capten a cota similar: si los tramos captados difieren más de 10 m, el script lo avisa, porque entre esos pozos queda un término de flotación sin corregir (el aviso se ajusta con `--tolerancia-cota`). El cálculo supone densidad uniforme en la columna de agua del pozo. No sirve tal cual para gradientes verticales: para eso hace falta otro tratamiento, y hay que decirlo. Sin densidad medida en el pozo no hay carga equivalente.

## Curva de evaporación

CSV con una fila por medición:

```
punto,superficie,profundidad,evaporacion
EV-01,costra,0.05,5.3
```

- `profundidad`: del nivel freático bajo la superficie, en metros.
- `evaporacion`: medida, en mm/d.
- `superficie` es opcional (costra, suelo, vegetación, agua libre). Si viene, el script ajusta además una curva por cada tipo con tres o más mediciones.

```
python "<carpeta de la skill>/scripts/salares.py" evaporacion evaporacion.csv
```

Ajusta E = E₀ × exp(−k × z) y entrega la evaporación en superficie, el coeficiente de decaimiento, el R² y la profundidad a la que la evaporación cae al 1 %.

Para probar: `ejemplos/evaporacion.csv` (debe dar E₀ cerca de 6 mm/d y k cerca de 2,5 por metro).

**Cómo leerlo.** Con más de un tipo de superficie, usa la tabla por tipo: el ajuste global mezcla superficies y solo sirve de referencia. Si el archivo no trae la columna, el script lo avisa. También avisa cuando la profundidad de extinción queda fuera del rango medido, porque entonces es una extrapolación.

## Reglas

- Ambas órdenes aceptan `--json`, separador coma o punto y coma, y coma decimal.
- Las densidades y las tasas se miden; no se suponen. Lo que falte se informa como faltante.
