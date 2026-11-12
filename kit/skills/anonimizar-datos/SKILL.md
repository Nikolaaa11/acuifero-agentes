---
name: anonimizar-datos
description: "Anonimiza una tabla antes de trabajarla con una IA y revierte los resultados después - reemplaza nombres de pozos, puntos, faenas o clientes por códigos, traslada las coordenadas a un origen local conservando distancias, y guarda la equivalencia en un archivo de clave que queda solo en el equipo. Úsala cuando los datos sean de un cliente y haya que reducir lo que se expone, o para devolver los nombres reales a un informe ya procesado."
---

# Anonimizar datos

Calcula con el script incluido. Anonimizar reduce el riesgo; no reemplaza la autorización de la empresa y del contrato para usar una IA con datos de un cliente. Confirma eso primero.

## Qué hace y qué no

- Reemplaza nombres por códigos (`P-001`, `P-002`…), de forma consistente entre archivos mientras uses la misma clave.
- Traslada las coordenadas a un origen local: se conservan distancias, direcciones y geometría, no la ubicación real.
- No altera los valores medidos (niveles, concentraciones, fechas). Esos valores pueden bastar para reconocer un sitio: tenlo presente.
- No revisa el texto libre de otras columnas. Si una columna de observaciones nombra al cliente, inclúyela en `--nombres` o quítala.

## Cómo anonimizar

En Windows usa `python`; en Mac o Linux, `python3`.

```
python "<carpeta de la skill>/scripts/anonimizar.py" niveles.csv --nombres punto --x este --y norte --clave clave-proyecto.json
```

- `--nombres` una o más columnas cuyos valores se reemplazan por códigos.
- `--x` y `--y` columnas de coordenadas (van de a pares).
- `--clave` archivo donde se guarda la equivalencia. Usa la misma clave para todos los archivos del proyecto.
- `--prefijo P`, `--decimales 2`, `--salida archivo` y `--json` son opcionales.

Queda un archivo `-anon` junto al original. Trabaja solo con ese.

## Cómo revertir

```
python "<carpeta de la skill>/scripts/anonimizar.py" informe-anon.md --revertir --clave clave-proyecto.json --salida informe.md
```

Devuelve los nombres reales en cualquier archivo de texto (Markdown, CSV, texto). Para restaurar coordenadas en un CSV, agrega `--x` y `--y`.

Para probar: `ejemplos/pozos.csv` (cinco pozos ficticios).

## Reglas

- **La clave no sale del equipo.** No la subas, no la pegues en un chat y no la dejes en una carpeta compartida con el archivo anonimizado. Agrégala al `.gitignore` si el proyecto usa control de versiones.
- No leas ni muestres el contenido de la clave en la conversación: basta con saber que existe.
- Guarda el original sin tocar en `01-datos-originales/` y el anonimizado en `02-datos-limpios/`.
- Después de revertir, revisa el resultado: si un código quedó abreviado o cambiado, no se revierte solo.
- Si la autorización de la empresa no está confirmada, trabaja con datos públicos o ficticios y dilo.
