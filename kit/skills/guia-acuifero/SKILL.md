---
name: guia-acuifero
description: "Índice del kit Acuífero para hidrogeología y geología ambiental en minería - dice qué agente o skill usar para cada tarea (ensayos de bombeo, hidroquímica, salares, drenaje ácido, agua en componentes mineros, modelos, alerta temprana, cierre, tramitación, informes, revisión) y el orden de trabajo de un proyecto, y trae el verificador de instalación. Úsala cuando pregunten qué puede hacer el kit, por dónde partir, qué agente conviene, si la instalación funciona, o cuando un encargo abarque varias etapas."
---

# Guía del kit Acuífero

Veinte agentes y quince skills para el trabajo diario de una hidrogeóloga o geóloga ambiental en consultoría minera. Los agentes piensan y redactan; las skills calculan con scripts probados.

## Qué usar para cada cosa

| Necesidad | Agente | Skill que calcula |
|---|---|---|
| Responder unas bases, planificar horas y cronograma | `hidro-propuestas` | — |
| Recopilar antecedentes públicos de una cuenca | `hidro-bibliografia` | — |
| Saber qué norma o guía aplica y citarla bien | `hidro-normativa` | — |
| Planificar una campaña de niveles o muestreo | `hidro-terreno` | — |
| Interpretar un ensayo de bombeo o recuperación | `hidro-ensayos` | `ensayo-bombeo` |
| Control de calidad e interpretación de química de aguas | `hidro-quimica` | `balance-ionico` |
| Series de niveles o calidad, tendencias, excedencias | `hidro-monitoreo` | `tendencia-niveles` |
| Mapas, coordenadas, cuencas, piezometría | `hidro-sig` | `mapa-piezometrico` |
| Salares, salmueras, evaporación, lagunas y vegas | `hidro-salares` | `salares` |
| Drenaje ácido y lixiviación de metales | `geo-drenaje` | `balance-acido-base` |
| Sitios contaminados y pasivos ambientales | `geo-ambiental` | `balance-ionico` |
| Modelo conceptual hidrogeológico | `hidro-conceptual` | `mapa-piezometrico` |
| Modelo numérico: construir, calibrar, revisar | `hidro-modelo` | `calibracion-modelo` |
| Agua en rajos, relaves, botaderos y pilas | `hidro-mineria` | `balance-aguas` |
| Especiación, saturación y transporte reactivo | `geo-reactivo` | `phreeqc-entrada` |
| Redactar el informe o un capítulo | `hidro-informes` | `informe-hidrogeologico` |
| Responder observaciones de la autoridad | `hidro-seia` | `informe-hidrogeologico` |
| Revisión crítica antes de entregar | `hidro-revisor` | todas |
| Plan de alerta temprana e informes de seguimiento | `hidro-alerta` | `umbrales-alerta` |
| Componente de aguas de un plan de cierre | `hidro-cierre` | `balance-aguas` |
| Pasar unidades sin equivocarse | cualquiera | `unidades-hidro` |
| Ordenar la carpeta y las reglas de un proyecto nuevo | — | `inicio-proyecto` |
| Ocultar nombres y coordenadas antes de usar datos de un cliente | — | `anonimizar-datos` |

## Orden de trabajo de un proyecto

1. **Propuesta y alcance:** `hidro-propuestas`.
2. **Antecedentes y normativa:** `hidro-bibliografia` y `hidro-normativa`, en paralelo.
3. **Terreno y datos:** `hidro-terreno` antes de salir; al volver, datos a tablas ordenadas.
4. **Análisis:** `hidro-ensayos`, `hidro-quimica`, `hidro-monitoreo`, `hidro-sig`, `hidro-salares`, `geo-drenaje`, `geo-ambiental`, según el encargo. Pueden correr en paralelo porque no dependen entre sí.
5. **Modelos:** `hidro-conceptual` primero; después `hidro-modelo`, `hidro-mineria` y `geo-reactivo`.
6. **Informe y tramitación:** `hidro-informes` con los resultados anteriores; `hidro-seia` para las respuestas a la autoridad.
7. **Revisión y entrega:** `hidro-revisor`, y vuelta a quien corresponda para corregir.
8. **Seguimiento y cierre:** `hidro-alerta` en cada campaña; `hidro-cierre` para la condición final de cada componente.

Al empezar un proyecto, corre `inicio-proyecto` para dejar la carpeta ordenada y un `CLAUDE.md` con el país, el sistema de coordenadas, las unidades y las reglas de confidencialidad. Todos los agentes lo leen.

## Comprobar la instalación

Si preguntan si el kit quedó bien instalado o si un cálculo no corre, ejecuta el verificador que está en la carpeta de esta skill y muestra su resultado tal cual:

```
python "<carpeta de la skill>/scripts/comprobar.py"
```

Corre cada script con sus datos de ejemplo y compara con el valor esperado. No modifica nada. En Mac o Linux usa `python3`. En Windows, si `python` no responde, prueba con `py`.

## Cómo delegar

- Un encargo, un agente. Si el pedido abarca varias etapas, divídelo y lanza en paralelo los que no dependen entre sí.
- Entrégale a cada agente la ruta de los archivos, el objetivo y qué debe devolver. No ve la conversación anterior.
- Si los agentes están instalados como plugin, su nombre completo lleva el prefijo `acuifero:` (por ejemplo `acuifero:hidro-ensayos`).

## Reglas del kit

- Ningún dato, parámetro, norma ni referencia se inventa. Lo que no está en un archivo o en una fuente abierta en la sesión se marca como faltante.
- Los cálculos se hacen con los scripts de las skills y se deja el comando usado.
- Los datos de clientes no salen a buscadores ni a servicios externos. Antes de cargar información confidencial a cualquier herramienta de IA, la usuaria debe confirmar que la política de su empresa y el contrato del proyecto lo permiten. Con clientes de la gran minería esto no es un trámite: si no está confirmado, se trabaja con datos públicos, ficticios o anonimizados con `anonimizar-datos`.
- Los agentes preparan; la profesional a cargo revisa, decide y firma.
