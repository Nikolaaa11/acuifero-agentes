---
name: tendencia-niveles
description: "Analiza series de monitoreo por punto - estadísticos, prueba de tendencia de Mann-Kendall, pendiente de Sen por año y valores anómalos. Sirve para niveles de agua, caudales o concentraciones. Úsala en informes de seguimiento, cuando pregunten si un nivel o un parámetro está subiendo o bajando, o para revisar una serie antes de graficarla."
---

# Tendencias en series de monitoreo

Calcula con el script incluido.

## Datos que necesitas

CSV en formato largo, una medición por fila:

```
fecha,punto,valor
2024-03-15,PM-01,512.31
```

- Fechas como `AAAA-MM-DD`, `DD-MM-AAAA` o `DD/MM/AAAA`.
- Acepta separador coma o punto y coma, y coma decimal.
- Una sola variable por archivo. Si la planilla viene ancha (una columna por pozo), pásala a formato largo antes y guarda esa versión.
- Decide antes si el valor es cota piezométrica o profundidad: con profundidad, una tendencia creciente significa que el nivel baja. Dilo en el informe.

## Cómo correrlo

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/tendencia.py" niveles.csv --unidad m
```

- `--alfa 0.05` nivel de significancia (por defecto 0,05).
- `--json` para seguir procesando.

Para probar: `ejemplos/niveles-monitoreo.csv` (tres pozos ficticios, cinco años: PM-01 baja cerca de 0,42 m/año, PM-02 no tiene tendencia, PM-03 sube y trae una lectura anómala en julio de 2023).

## Cómo leer el resultado

- **Tendencia** creciente o decreciente solo cuando p es menor que alfa. «Sin tendencia» no prueba estabilidad: puede faltar potencia con pocos datos.
- **Pendiente de Sen** en unidades por año. Es robusta frente a valores anómalos.
- **Valores anómalos**: lecturas alejadas de la mediana más de 3,5 desviaciones robustas. Se revisan contra la bitácora; no se eliminan sin justificación escrita.
- La prueba no corrige estacionalidad ni autocorrelación. Con datos mensuales y ciclo anual marcado, compara además el mismo mes entre años o agrega por año antes de concluir.
- Los valores bajo el límite de detección (`<x`) se descartan del cálculo y el script lo informa.

## Qué entregar

La tabla por punto, las observaciones, un hidrograma por grupo de pozos (con matplotlib si está disponible) y una frase por punto que diga qué pasa y con qué confianza.
