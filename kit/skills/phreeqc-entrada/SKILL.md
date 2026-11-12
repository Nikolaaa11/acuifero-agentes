---
name: phreeqc-entrada
description: "Genera un archivo de entrada de PHREEQC desde una tabla de laboratorio - un bloque de solución por muestra y la salida seleccionada con pH, fuerza iónica, error de balance de cargas e índices de saturación de los minerales habituales, eligiendo la base de datos termodinámica. Úsala para preparar especiación e índices de saturación de un conjunto de muestras, o como punto de partida de un modelo geoquímico de mezcla, equilibrio o transporte reactivo."
---

# Entrada para PHREEQC

El script escribe el archivo; no ejecuta PHREEQC. Si PHREEQC está instalado en el equipo, córrelo después; si no, deja el archivo listo y dilo.

## Datos que necesitas

CSV con una fila por muestra y concentraciones en **mg/L**:

```
muestra,pH,temp,Ca,Mg,Na,K,HCO3,CO3,Cl,SO4,NO3,SiO2,Fe,As
```

- Obligatoria: `pH`. Recomendadas: iones mayores, `temp` (°C) y alcalinidad.
- La alcalinidad puede venir como `HCO3` (y `CO3`) o como `alcalinidad` en mg/L de CaCO₃.
- Reconoce además `pe`, `densidad`, `F`, `Mn`, `Al`, `Cu`, `Zn`, `Pb`, `Cd`, `Ba`, `Sr`, `Li`, `B`, `Br`, `Mo`, `Se`, `Sb`, `Ni`, `Co`, `Cr` y `U`.
- Los valores bajo el límite de detección (`<0,01`) no se incluyen y quedan anotados como comentario.
- Parte de análisis que ya pasaron el control de calidad de la skill `balance-ionico`.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/phreeqc_entrada.py" muestras.csv --salida muestras.pqi
```

- `--base` elige la base de datos: `phreeqc.dat` (por defecto), `pitzer.dat` para salmueras, o `wateq4f.dat`, `minteq.v4.dat` y `llnl.dat` cuando hay elementos traza como arsénico o molibdeno.
- `--temp 25` y `--pe 4` son los valores supuestos cuando la tabla no los trae; quedan marcados como «supuesto» en el archivo.
- `--balancear Cl` hace que PHREEQC cierre el balance de cargas ajustando ese elemento. Úsalo solo si lo justificas.
- `--json` entrega el resumen.

Para probar: `ejemplos/aguas.csv` (seis muestras ficticias; deben salir seis bloques de solución y el arsénico queda como comentario con la base por defecto).

## Cómo leer lo que entrega

- El archivo `.pqi` trae comentarios con el origen, la base prevista y cada supuesto. Ábrelo y revísalo antes de correrlo.
- Con `phreeqc.dat` y `pitzer.dat`, los elementos que la base no contiene se dejan como comentario y el script lo avisa: cambia de base para modelarlos.
- Si la fuerza iónica estimada supera 1 mol/L, el script recomienda `pitzer.dat`: las bases de actividad estándar no valen para salmueras.
- Los resultados quedan en el archivo `.sel` al correr PHREEQC: pH, pe, temperatura, fuerza iónica, error de balance e índices de saturación.

## Reglas

- Este archivo es un punto de partida. Los bloques de mezcla, equilibrio con fases, cinética, superficie o transporte se agregan a mano y se comentan.
- Un índice de saturación positivo no prueba que el mineral precipite.
- El potencial redox supuesto pesa mucho en hierro, manganeso y arsénico: si no hay dato medido, dilo en el informe.
- No se ha comprobado aquí la corrida en PHREEQC: revisa los avisos del programa la primera vez.
