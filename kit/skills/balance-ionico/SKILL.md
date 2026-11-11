---
name: balance-ionico
description: "Hace el control de calidad de análisis de agua - balance iónico en meq/L, clasificación de cada muestra como aceptada, dudosa o rechazada, tipo de agua, sólidos disueltos y conductividad contra la suma de iones, y diagrama de Piper. Úsala cuando lleguen resultados de laboratorio con iones mayores o antes de interpretar la química de un conjunto de muestras."
---

# Balance iónico y Piper

Calcula con el script incluido; no conviertas a meq/L de memoria.

## Datos que necesitas

CSV con una fila por muestra y concentraciones en **mg/L**:

```
muestra,pH,CE,SDT,Ca,Mg,Na,K,HCO3,CO3,Cl,SO4,NO3
```

- Obligatorias: `Ca, Mg, Na, HCO3, Cl, SO4`. Recomendadas: `K, CO3, NO3`.
- Opcionales: `CE` (µS/cm), `SDT` (mg/L), `pH`.
- Valores bajo el límite de detección se escriben como `<0,01`: cuentan como cero y quedan anotados.
- Acepta separador coma o punto y coma, y coma decimal.

Antes de correr, revisa dos trampas frecuentes: alcalinidad informada como CaCO₃ (pasa a HCO₃ multiplicando por 1,22) y nitrato informado como N (pasa a NO₃ multiplicando por 4,43). Anota cada conversión que hagas.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/balance_ionico.py" muestras.csv --piper piper.svg
```

- `--limite 5` cambia el error aceptable (por defecto ±5 %; dudosa hasta el doble).
- `--json` entrega todo el detalle: meq/L por ion, porcentajes para Piper y razones de control.

Para probar: `ejemplos/hidroquimica.csv` (seis muestras ficticias; PZ-05 debe salir rechazada con cerca de +11 %).

## Cómo leer el resultado

- **Error positivo**: sobran cationes. Suele faltar un anión (alcalinidad, nitrato, fluoruro) o el sodio está sobreestimado.
- **Error negativo**: sobran aniones. En aguas ácidas o de mina faltan cationes como Fe, Al, Mn o NH₄, que el script no incluye: súmalos aparte y dilo.
- SDT medido/calculado fuera de 1,0 a 1,2, o 100·Σiones/CE fuera de 0,9 a 1,1, apuntan a un error de laboratorio o de transcripción.
- El tipo de agua usa el catión y el anión que superan 50 % en meq; si ninguno lo supera, nombra los dos mayores.

## Qué entregar

La tabla de control de calidad, las observaciones por muestra, el diagrama de Piper y la lista de muestras que no deben interpretarse sin revisar. No descartes una muestra en silencio: se informa y se explica.
