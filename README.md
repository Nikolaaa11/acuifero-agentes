# Acuífero

*Con cariño para Patricia Guerrero, la mejor geóloga de Chile.*

Un equipo de agentes para el agua subterránea: veinte agentes y quince skills con cálculos probados para hidrogeología y geología ambiental en minería. Se instalan en Claude (Claude Code, Cowork o claude.ai) y también en Hermes Agent.

**Sitio, mapa interactivo, calculadoras y manual paso a paso:** https://acuifero-agentes.vercel.app

## Instalar

**Windows** (PowerShell):

```powershell
irm https://acuifero-agentes.vercel.app/instalar.ps1 | iex
```

**Mac o Linux** (Terminal):

```bash
curl -fsSL https://acuifero-agentes.vercel.app/instalar.sh | bash
```

El instalador copia los agentes a `~/.claude/agents` y las skills a `~/.claude/skills`, y al final comprueba que los cálculos funcionen. Si ya existe algo distinto con el mismo nombre, lo guarda antes en `~/.claude/acuifero-respaldo`. No toca nada más.

Para ver el detalle de la comprobación:

```bash
python ~/.claude/skills/guia-acuifero/scripts/comprobar.py
```

**Como plugin de Claude Code:**

```
/plugin marketplace add Nikolaaa11/acuifero-agentes
/plugin install acuifero@acuifero-kit
```

**En Cowork o claude.ai:** Personalizar → Plugins → Agregar marketplace → `Nikolaaa11/acuifero-agentes`.

**En Hermes Agent:** agrega la opción `-Hermes` (Windows) o `--hermes` (Mac y Linux) al instalador. Los agentes se instalan como skills con el mismo nombre.

**A mano:** descarga [el kit en .zip](https://acuifero-agentes.vercel.app/descargas/acuifero-kit.zip) y copia las carpetas `agents` y `skills` dentro de `~/.claude/`.

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
| `hidro-salares` | Salmueras, densidad variable, evaporación, lagunas y vegas |
| `geo-drenaje` | Drenaje ácido de roca y lixiviación de metales |
| `geo-ambiental` | Sitios contaminados y pasivos ambientales |
| `hidro-conceptual` | Modelo conceptual hidrogeológico |
| `hidro-modelo` | Modelo numérico: diseño, calibración y revisión |
| `hidro-mineria` | Agua en rajos, relaves, botaderos y pilas; balance de aguas |
| `geo-reactivo` | Modelación geoquímica y transporte reactivo |
| `hidro-informes` | Redacción con trazabilidad de cada cifra |
| `hidro-seia` | Tramitación ambiental y respuestas a la autoridad |
| `hidro-revisor` | Revisión crítica antes de entregar |
| `hidro-alerta` | Planes de seguimiento y de alerta temprana |
| `hidro-cierre` | Componente de aguas y geoquímica de los planes de cierre |

| Skill | Qué hace |
|---|---|
| `ensayo-bombeo` | Ajusta Cooper-Jacob y Theis; entrega T, S y K, con diagnóstico por derivada |
| `balance-ionico` | Balance iónico, tipo de agua y diagrama de Piper |
| `tendencia-niveles` | Mann-Kendall, pendiente de Sen y valores anómalos |
| `mapa-piezometrico` | Curvas para QGIS, gradiente y dirección de flujo |
| `salares` | Carga equivalente de agua dulce y curva de evaporación |
| `balance-acido-base` | Clasifica residuos mineros por su potencial de generar ácido |
| `calibracion-modelo` | Estadísticos de observado contra simulado |
| `balance-aguas` | Cierre del balance de aguas por período |
| `phreeqc-entrada` | Escribe el archivo de entrada de PHREEQC desde una tabla de laboratorio |
| `umbrales-alerta` | Estado de cada punto de control frente a sus umbrales |
| `anonimizar-datos` | Cambia nombres por códigos y traslada coordenadas; la clave queda en el equipo |
| `unidades-hidro` | Conversión de K, caudal y transmisividad |
| `informe-hidrogeologico` | Índices y reglas de redacción para cuatro informes |
| `inicio-proyecto` | Carpeta ordenada y archivo de contexto del proyecto |
| `guia-acuifero` | Qué agente o skill usar para cada tarea, y el verificador de instalación |

Los scripts usan solo la biblioteca estándar de Python 3.8 o posterior (matplotlib es opcional, para gráficos). Cada skill trae datos de ejemplo ficticios.

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
python tools/probar_scripts.py     # 135 pruebas de los scripts contra valores conocidos
node tools/probar_web.js           # 37 pruebas de las fórmulas de las calculadoras
python tools/construir.py          # valida el kit, corre las pruebas y genera public/datos.js y los .zip
python tools/generar_ejemplos.py   # regenera los datos de ejemplo
```

Después de cambiar un agente, una skill o `catalogo.json`, corre `tools/construir.py`, comprueba que termine con «Listo» y sube los cambios. El sitio se publica solo desde `public/`.

## Avisos

- Kit independiente. No es un producto oficial de Anthropic ni de Nous Research, y no pertenece a ninguna consultora.
- Los agentes preparan; la profesional a cargo revisa, decide y firma. Los resultados son un apoyo y pueden contener errores.
- Antes de cargar datos de clientes a cualquier herramienta de IA, confirma lo que permiten la política de tu empresa y el contrato del proyecto. Anonimizar reduce el riesgo, pero no reemplaza esa autorización.
- El kit escribe archivos de entrada de PHREEQC, pero no incluye ni ejecuta PHREEQC, MODFLOW ni otros programas de modelación.

## Licencia

MIT. Ver [LICENSE](LICENSE).
