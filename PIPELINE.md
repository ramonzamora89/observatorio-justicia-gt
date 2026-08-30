# PIPELINE.md

## Pipeline reproducible

### 0. Discovery
Generar una lista de URLs/IDs de documentos potenciales.

Salida: `discovery_manifest.jsonl`

### 1. Acquisition
Descargar únicamente contenido públicamente accesible y permitido.

- rate limiting
- retries
- cache
- user-agent identificable
- logs
- SHA-256

Nunca evadir autenticación, CAPTCHA o controles técnicos.

### 2. Raw preservation
Los documentos originales son inmutables:

`data/raw/{source}/{year}/{sha256}.{ext}`

### 3. Parsing
Extraer texto y estructura.

Preferencia:
1. HTML/texto nativo
2. PDF con text layer
3. OCR únicamente cuando sea necesario

### 4. Structured extraction
Salida JSON validada por Pydantic.

Reglas:
- no inventar;
- `null` si no consta;
- evidence span para campos críticos;
- confidence por campo.

### 5. Normalization
Normalización determinística antes de LLM cuando sea posible.

### 6. Entity resolution
Matching conservador. Los matches ambiguos quedan pendientes de revisión.

### 7. Procedural linking
Prioridad de señales:
1. referencia explícita a expediente;
2. referencia explícita a resolución;
3. mismas partes + tribunal + fechas;
4. similitud textual/semántica.

Nunca aceptar automáticamente vínculos débiles.

### 8. Validation
Tests de consistencia:
- resolución no puede preceder ingreso;
- órgano inferior/superior compatible;
- expediente con formato válido;
- magistrado asignado al órgano en período compatible, cuando la información exista.

### 9. Analytics
Solo usar registros que superen umbral de calidad configurado.

### 10. Publication
Cada métrica debe permitir drill-down hasta casos y documentos.

## Actualización incremental
El collector mantiene un `source_cursor` por fuente y fecha.

Flujo programado:
`discover_new → compare manifest → acquire new → parse → extract → validate → recompute aggregates`

## QA sampling
En cada ejecución:
- muestra aleatoria;
- muestra de baja confianza;
- muestra de anomalías;
- muestra de documentos nuevos.

## Human-in-the-loop
Revisión obligatoria antes de publicar:
- acusaciones/etiquetas sensibles;
- identidad ambigua;
- anomalías de alto impacto;
- resultados jurídicos con confianza baja.
