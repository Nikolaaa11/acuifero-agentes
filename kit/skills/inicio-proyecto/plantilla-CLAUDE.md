# Proyecto: [nombre corto]

Este archivo lo leen todos los agentes del kit Acuífero antes de trabajar. Mantenlo al día.

## Contexto

- **Tipo de estudio:** [línea de base hidrogeológica / ensayo de bombeo / seguimiento / modelo numérico / estabilidad química / otro]
- **Objetivo:** [qué pregunta debe responder el estudio]
- **País y región:** [por confirmar]
- **Cliente en los documentos:** [nombre real / código / «el Titular»]
- **Entregables y fechas:** [lista]

## Normativa y guías

- **Autoridad y marco aplicable:** [por confirmar con `hidro-normativa`]
- **Guías técnicas exigidas:** [por confirmar]
- Toda norma se cita con número, año, enlace oficial y fecha de consulta.

## Datos y convenciones

- **Sistema de coordenadas:** [datum, huso y código EPSG; por confirmar]
- **Cota de referencia de niveles:** [brocal / terreno / otra]
- **Unidades:** longitud en m; tiempo en d; caudal en L/s; K en m/d; T en m²/d; concentración en mg/L.
- **Nombres de pozos y puntos:** [regla, por ejemplo PZ-01, PM-01, VT-01]
- **Separador decimal en informes:** coma.
- **Idioma:** español.

## Carpetas

- `01-datos-originales/` no se edita. Todo archivo recibido se anota en `registro.csv`.
- Los scripts trabajan sobre `02-datos-limpios/`.
- Cada resultado guarda junto a él el comando o script que lo produjo.

## Confidencialidad

- Los datos de este proyecto no se pegan en buscadores ni en servicios externos.
- En búsquedas web se usan términos genéricos, sin nombre del cliente ni coordenadas.
- **¿Está permitido procesar datos de este proyecto con herramientas de IA?** [sí / no / solo datos anonimizados; confirmar con la empresa y el contrato]
- Si la respuesta es «no» o no está confirmada, los agentes trabajan solo con datos públicos o ficticios.

## Forma de trabajo

- Ningún dato, parámetro ni referencia se inventa. Lo que falta se marca como «faltante».
- Los cálculos se hacen con las skills del kit y se revisan con `hidro-revisor` antes de entregar.
- Los agentes preparan; la profesional a cargo revisa, decide y firma.

## Pendientes y decisiones

- [fecha] [decisión o pendiente]
