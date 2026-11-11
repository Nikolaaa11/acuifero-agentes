# Acuífero

Un equipo de agentes para el agua subterránea: trece agentes y nueve skills con cálculos probados para hidrogeología y geología ambiental. Se instalan en Claude (Claude Code, Cowork o claude.ai) y también en Hermes Agent.

**Sitio, mapa interactivo, calculadoras y manual:** https://acuifero-agentes.vercel.app

## Instalar

**Windows** (PowerShell):

```powershell
irm https://acuifero-agentes.vercel.app/instalar.ps1 | iex
```

**Mac o Linux** (Terminal):

```bash
curl -fsSL https://acuifero-agentes.vercel.app/instalar.sh | bash
```

El instalador copia los agentes a `~/.claude/agents` y las skills a `~/.claude/skills`. Si ya existe algo distinto con el mismo nombre, lo guarda antes en `~/.claude/acuifero-respaldo`. No toca nada más.

**Como plugin de Claude Code:**

```
/plugin marketplace add Nikolaaa11/acuifero-agentes
/plugin install acuifero@acuifero-kit
```

**En Cowork o claude.ai:** Personalizar → Plugins → Agregar marketplace → `Nikolaaa11/acuifero-agentes`.

**En Hermes Agent:** agrega la opción `-Hermes` (Windows) o `--hermes` (Mac y Linux) al instalador. Los agentes se instalan como skills con el mismo nombre.

Opciones del instalador: `-Proyecto` / `--proyecto` (solo en la carpeta actual), `-Quitar` / `--quitar` (desinstala lo instalado), `-Origen` / `--origen` (desde una carpeta local), `-Destino` / `--destino`.

## Qué trae

| Agente | Para qué |
|---|---|
| `hidro-propuestas` | Alcance, horas y cronograma a partir de unas bases |
| `hidro-bibliografia` | Antecedentes públicos de una cuenca, con cada dato atado a su fuente |
| `hidro-normativa` | La norma exacta, vigente y citada desde su fuente oficial |
| `hidro-terreno` | Campañas de niveles y muestreo, protocolos y planillas |
| `hidro-ensayos` | Ensayos de bombeo, recuperación y slug tests |
| `hidro-quimica` | Control de calidad e interpretación hidroquímica |
| `hidro-monitoreo` | Series de niveles y calidad, tendencias y excedencias |
| `hidro-sig` | Coordenadas, capas, cuencas y piezometría |
| `geo-ambiental` | Suelos, residuos mineros, drenaje ácido y cierre |
| `hidro-conceptual` | Modelo conceptual hidrogeológico |
| `hidro-modelo` | Modelo numérico: diseño, calibración y revisión |
| `hidro-informes` | Redacción con trazabilidad de cada cifra |
| `hidro-revisor` | Revisión crítica antes de entregar |

| Skill | Qué hace |
|---|---|
| `ensayo-bombeo` | Ajusta Cooper-Jacob y Theis; entrega T, S y K |
| `balance-ionico` | Balance iónico, tipo de agua y diagrama de Piper |
| `tendencia-niveles` | Mann-Kendall, pendiente de Sen y valores anómalos |
| `mapa-piezometrico` | Curvas para QGIS, gradiente y dirección de flujo |
| `calibracion-modelo` | Estadísticos de observado contra simulado |
| `unidades-hidro` | Conversión de K, caudal y transmisividad |
| `informe-hidrogeologico` | Índices y reglas de redacción para cuatro informes |
| `inicio-proyecto` | Carpeta ordenada y archivo de contexto del proyecto |
| `guia-acuifero` | Qué agente o skill usar para cada tarea |

Los scripts usan solo la biblioteca estándar de Python 3 (matplotlib es opcional, para gráficos). Cada skill trae datos de ejemplo ficticios.

## Carpetas

```
kit/                    el plugin: agentes, skills, scripts y ejemplos
  agents/               un archivo .md por agente
  skills/<nombre>/      SKILL.md, scripts/, ejemplos/, plantillas/
catalogo.json           textos y conexiones que muestra el sitio
public/                 el sitio (estático) y los instaladores
tools/                  pruebas y empaquetado
.claude-plugin/         manifiesto del marketplace
```

## Desarrollo

```bash
python tools/probar_scripts.py     # 64 pruebas de los scripts contra valores conocidos
node tools/probar_web.js           # 29 pruebas de las fórmulas de las calculadoras
python tools/construir.py          # valida el kit, corre las pruebas y genera public/datos.js y los .zip
python tools/generar_ejemplos.py   # regenera los datos de ejemplo
```

Después de cambiar un agente, una skill o `catalogo.json`, corre `tools/construir.py` y sube los cambios. El sitio se publica solo desde `public/`.

## Avisos

- Kit independiente. No es un producto oficial de Anthropic ni de Nous Research, y no pertenece a ninguna consultora.
- Los agentes preparan; la profesional a cargo revisa, decide y firma. Los resultados son un apoyo y pueden contener errores.
- Antes de cargar datos de clientes a cualquier herramienta de IA, confirma lo que permiten la política de tu empresa y el contrato del proyecto.

## Licencia

MIT. Ver [LICENSE](LICENSE).
