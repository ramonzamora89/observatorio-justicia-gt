# AGENTS.md

## División de trabajo sugerida

### Agent: Source Scout
Investiga técnicamente una fuente pública y documenta acceso, campos, paginación, límites y estabilidad.

No realiza scraping masivo.

### Agent: Collector Engineer
Implementa adaptadores de adquisición y manifests.

### Agent: Document Parser
Convierte documentos a texto estructurado conservando páginas y offsets.

### Agent: Legal Extractor
Extrae hechos procesales mediante schemas estrictos y evidence spans.

### Agent: Entity Resolver
Normaliza tribunales, jueces, magistrados, partes y expedientes.

### Agent: Case Linker
Reconstruye relaciones entre decisiones e instancias.

### Agent: Data Auditor
Ejecuta validaciones, muestreo y medición de precisión.

### Agent: Analyst
Calcula KPIs solamente sobre datos que superan criterios de cobertura/calidad.

### Agent: Red Team
Busca errores sistemáticos:
- sesgo de selección;
- documentos faltantes;
- falsos matches;
- errores de fechas;
- clasificación errónea del resultado;
- conclusiones que exceden la evidencia.

## Flujo de handoff
`Source Scout → Collector → Parser → Extractor → Resolver → Linker → Auditor → Analyst → Red Team`

Ningún agente debe modificar silenciosamente los datos producidos por otro. Las correcciones deben quedar registradas.
