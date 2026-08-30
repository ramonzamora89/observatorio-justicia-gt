# PRD-1 — Observatorio Automatizado de Resoluciones Judiciales

**Estado:** borrador para prueba técnica  
**Versión:** 0.1  
**Fecha:** 2026-08-29

## 1. Problema
La información judicial guatemalteca está distribuida entre distintos portales, formatos y niveles jurisdiccionales. Esto dificulta reconstruir longitudinalmente el comportamiento de un expediente y comparar de forma sistemática el desempeño de jueces, magistrados y órganos.

El proyecto busca transformar documentación judicial pública en datos estructurados, verificables y reproducibles.

## 2. Objetivo del producto
Crear un pipeline que:

`descubre → adquiere → conserva → extrae → normaliza → vincula → valida → analiza → publica`

Cada conclusión debe poder regresar al documento y fragmento que la sustenta.

## 3. Usuario inicial
Investigador que necesita:
- reconstruir expedientes;
- investigar jueces/magistrados;
- comparar resoluciones;
- medir tiempos;
- estudiar apelaciones, casaciones y amparos;
- detectar patrones atípicos que ameriten investigación cualitativa.

## 4. MVP
Empezar por la Corte de Constitucionalidad porque dispone de un sistema público de jurisprudencia con búsquedas por texto libre, expediente, período y tipo de proceso.

### MVP-1
Recolectar una muestra reproducible de resoluciones de la CC.

### MVP-2
Extraer:
- expediente;
- fecha;
- tipo de proceso;
- asunto;
- tribunal de origen;
- partes cuando sean públicas;
- magistrados firmantes;
- ponente si consta;
- resultado;
- resolución impugnada;
- fechas procesales;
- citas jurisprudenciales.

### MVP-3
Vincular resoluciones pertenecientes al mismo ciclo procesal.

### MVP-4
Calcular KPIs.

## 5. Arquitectura

```text
sources/
   ↓
collectors/
   ↓
raw_documents/       ← copia inmutable + hash
   ↓
parsers/
   ↓
extractions/         ← salida estructurada + evidencia
   ↓
normalization/
   ↓
entity_resolution/   ← personas, tribunales, expedientes
   ↓
database/
   ↓
analytics/
   ↓
api + dashboard + exports
```

## 6. Componentes
### Collector
Un adaptador por fuente. Nunca mezclar scraping con lógica analítica.

Debe guardar:
- URL;
- timestamp;
- status HTTP;
- método de adquisición;
- archivo;
- SHA-256;
- MIME type;
- metadata visible.

### Parser
Convierte HTML/PDF/documento a texto conservando referencias a página/sección cuando sea posible.

### Extractor
Modelo determinístico + LLM para producir JSON según esquema.

El LLM no puede completar campos ausentes mediante conocimiento externo. Valor desconocido = `null`.

### Normalizer
Normaliza:
- nombres;
- fechas;
- expedientes;
- tribunales;
- delitos;
- tipos de resolución;
- resultados.

### Entity resolution
Evitar que variaciones de nombre creen personas diferentes.

Ejemplo:
`Juan Pérez López`, `Juan P. Pérez`, `Pérez López, Juan` → misma entidad solamente cuando exista evidencia suficiente.

### Linker
Relaciona:
`primera instancia → apelación → casación → amparo → CC`

La relación debe tener `confidence_score` y evidencia.

### QA
Validación automática y humana.

## 7. Taxonomía de resultados
No usar solamente `a favor/en contra`, porque puede inducir errores.

Guardar dos niveles:

**Resultado jurídico literal**
- otorgado
- denegado
- confirmado
- revocado
- modificado
- anulado
- rechazado
- inadmitido
- suspendido
- con lugar
- sin lugar
- archivo/sobreseimiento
- otro

**Efecto procesal normalizado**
- mantiene decisión inferior
- altera decisión inferior
- devuelve/reenvía
- termina proceso
- permite continuación
- suspende actuación
- no entra al fondo
- indeterminado

## 8. KPIs
### Celeridad
`decision_latency = fecha_resolucion - fecha_ingreso`

- mediana de días para resolver;
- P25/P50/P75/P90;
- tiempo por tipo de recurso;
- tiempo por órgano;
- tiempo por juez/magistrado;
- tiempo hasta decisión firme.

### Revisión
- tasa de confirmación;
- tasa de revocación;
- tasa de modificación;
- tasa de reenvío;
- tasa de inadmisión;
- proporción de decisiones que llegan a instancia superior.

### Estabilidad
`stability_rate = decisiones_mantenidas / decisiones_revisadas`

Debe ajustarse por materia y tipo de decisión antes de comparar jueces.

### Carga y producción
- resoluciones por período;
- casos activos conocidos;
- decisiones por mes;
- duración de backlog cuando pueda estimarse.

### Amparo/constitucional
- amparos provisionales otorgados/denegados;
- amparos definitivos otorgados/denegados;
- tiempo provisional → definitivo;
- tasa de decisiones inferiores alteradas por la CC.

### Casos de interés
Para corrupción, lavado, narcotráfico/crimen organizado:
- medidas sustitutivas/prisión;
- sobreseimientos;
- falta de mérito;
- clausura provisional;
- aceptación/rechazo de prueba;
- recusaciones;
- separaciones/acumulaciones;
- apelaciones especiales;
- casaciones;
- amparos.

## 9. Comparación justa
Nunca comparar tasas crudas sin controlar al menos:
- materia;
- delito;
- etapa;
- tipo de petición;
- período;
- órgano;
- volumen de casos;
- disponibilidad documental.

Para cada juez crear un grupo de pares.

## 10. Detección de anomalías
El sistema puede generar una **señal de revisión**, no una acusación.

Ejemplos:
- latencia muy inferior/superior a pares;
- tasa de revocación extrema;
- patrón excepcional de medidas procesales;
- divergencia persistente frente al órgano;
- tratamiento temporal diferencial de categorías comparables.

Cada alerta debe incluir:
- N de casos;
- baseline;
- diferencia;
- intervalo de confianza cuando proceda;
- lista de casos;
- calidad de datos.

## 11. Índice de calidad del dato
Cada observación tendrá `data_confidence` de 0–1.

Factores:
- documento oficial disponible;
- texto completo;
- extracción validada;
- identidad confirmada;
- fechas completas;
- vínculo entre instancias confirmado.

No publicar comparaciones agregadas cuando el coverage sea insuficiente.

## 12. Evidencia
Todo campo sensible debe soportar:

```json
{
  "value": "revoca",
  "confidence": 0.97,
  "source_document_id": "...",
  "page": 12,
  "quote": "fragmento breve de evidencia"
}
```

## 13. Auditoría
Guardar:
- versión del extractor;
- prompt/version;
- modelo;
- fecha;
- código Git commit;
- documento fuente/hash;
- correcciones humanas.

## 14. Stack sugerido
- Python 3.12+
- uv
- PostgreSQL
- SQLAlchemy
- Pydantic
- httpx
- BeautifulSoup/lxml
- Playwright solo cuando sea necesario
- PyMuPDF/pdfplumber
- DuckDB para análisis local
- Polars o pandas
- pytest
- Ruff
- mypy
- Alembic

Para el MVP puede utilizarse SQLite/DuckDB y migrar a PostgreSQL posteriormente.

## 15. Estructura del repositorio
```text
judicial-observatory-gt/
├── PROJECT.md
├── PRD-1.md
├── DATA_MODEL.md
├── PIPELINE.md
├── CLAUDE.md
├── AGENTS.md
├── README.md
├── pyproject.toml
├── config/
├── data/
│   ├── raw/
│   ├── parsed/
│   ├── processed/
│   └── exports/
├── src/
│   ├── collectors/
│   ├── parsers/
│   ├── extractors/
│   ├── normalization/
│   ├── linking/
│   ├── analytics/
│   ├── db/
│   └── cli/
├── schemas/
├── tests/
└── notebooks/
```

## 16. Primera prueba
Objetivo: 100 resoluciones CC.

1. Descubrir 100 documentos.
2. Registrar metadata y URL.
3. Descargar documentos permitidos.
4. Hash SHA-256.
5. Parsear texto.
6. Extraer JSON.
7. Validar 20 manualmente.
8. Corregir esquema/prompts.
9. Ejecutar nuevamente.
10. Obtener precisión por campo.

### Criterio de aceptación
- >98% expediente correcto
- >98% fecha correcta
- >95% tipo de proceso
- >95% resultado principal
- >90% identificación de órgano inferior cuando conste
- 100% de datos analíticos con `source_document_id`

## 17. Segunda prueba
Elegir 20 expedientes con decisiones en múltiples instancias y reconstruir el grafo procesal.

## 18. Backlog posterior
- CENADOJ/CSJ collector
- Salas de Apelaciones
- índice de jueces/magistrados
- buscador full-text
- embeddings semánticos
- citation graph
- dashboard
- API
- cron scheduler
- alertas por nuevas resoluciones

## 19. Riesgos
- cobertura pública incompleta;
- cambios de portales;
- PDFs escaneados;
- homónimos;
- numeración inconsistente;
- selección sesgada de jurisprudencia publicada;
- resoluciones no publicadas;
- confundir resultado procesal con mérito sustantivo.

Estos riesgos deben mostrarse en el producto, no ocultarse.
