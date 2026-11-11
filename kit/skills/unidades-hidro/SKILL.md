---
name: unidades-hidro
description: "Convierte unidades de uso diario en hidrogeología sin errores de factor - conductividad hidráulica, caudal, transmisividad, longitud, área y volumen, incluidas unidades anglosajonas. Úsala cada vez que haya que pasar un valor entre unidades en un cálculo, una tabla o una revisión, en vez de convertir de memoria."
---

# Conversor de unidades

Un error de 86 400 arruina un informe. Convierte con el script.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/unidades.py" 1e-5 m/s m/d
python "<carpeta de la skill>/scripts/unidades.py" 12 L/s m3/d
python "<carpeta de la skill>/scripts/unidades.py" --lista
```

## Unidades disponibles

- **Conductividad hidráulica:** m/s, cm/s, mm/s, m/h, m/d, cm/d, mm/d, m/año, mm/año, ft/d, gpd/ft2.
- **Caudal:** m3/s, L/s, L/min, m3/h, m3/d, m3/año, hm3/año (igual a Mm3/año), gpm, ft3/s.
- **Transmisividad:** m2/s, m2/h, m2/d, cm2/s, ft2/d, gpd/ft.
- **Longitud:** m, cm, mm, km, ft, in. **Área:** m2, ha, km2, acre. **Volumen:** m3, L, hm3, Mm3, gal, acre-ft.

Acepta variantes de escritura como `m³/día`, `l/s` o `m3/a`. El año es de 365,25 días y el galón es el de Estados Unidos.

## Reglas

- Si las dos unidades son de magnitudes distintas, el script lo rechaza: no fuerces la conversión.
- Muestra siempre la conversión en el texto o en una nota de la tabla (valor original, factor, resultado).
- Para pasar de T a K divide por el espesor saturado, y di qué espesor usaste.
- Para concentraciones (mg/L a meq/L) usa la skill `balance-ionico`, no esta.
