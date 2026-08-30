# Observatorio de Resoluciones Judiciales de Guatemala

## Visión
Construir un repositorio reproducible y auditable de resoluciones judiciales guatemaltecas que permita estudiar, a través del tiempo, el comportamiento de órganos jurisdiccionales, jueces y magistrados mediante indicadores verificables.

El sistema **no debe inferir corrupción a partir de una resolución aislada**. Su función es identificar patrones medibles —celeridad, revocación, confirmación, criterios, trato procesal y resultados— y conservar la evidencia primaria que permita investigar esos patrones.

## Por qué existe

Este proyecto nace de un hueco concreto de otro trabajo de investigación
periodística: se pudieron documentar resoluciones que apuntan en una dirección,
y **no se pudo obtener el universo comparable** —cuántos casos vio cada juez y
cómo resolvió los demás—. Sin eso, una lista de fallos no prueba nada.

**El observatorio se mantiene separado de cualquier investigación concreta, y la
razón es metodológica antes que organizativa.** Un observatorio construido
dentro de la investigación que quiere una respuesta produce números sospechosos
aunque el código sea impecable. La independencia es parte del instrumento: los
indicadores se calculan para toda la judicatura, no para el órgano que interesa.

Lo que este proyecto aporta es **el denominador**, y con él la posibilidad de
decir si un patrón judicial existe o no.

Las reglas al final de `CLAUDE.md` se heredan de trabajo previo con documentos
judiciales. Cada una produjo un resultado falso que se descubrió después.

## Preguntas de investigación
1. ¿Cuánto tarda cada órgano jurisdiccional en resolver asuntos comparables?
2. ¿Con qué frecuencia una decisión es confirmada, modificada o revocada por una instancia superior?
3. ¿Existen diferencias estadísticamente relevantes según materia, delito, tipo de actor, defensa, fiscalía o etapa procesal?
4. ¿Qué jueces o magistrados presentan patrones atípicos frente a pares comparables?
5. ¿Cómo viaja un expediente entre primera instancia, Salas de Apelaciones, Corte Suprema de Justicia y Corte de Constitucionalidad?
6. ¿Qué precedentes se citan y cómo evolucionan los criterios?
7. En casos vinculados con corrupción, narcotráfico, lavado de dinero y crimen organizado, ¿existen patrones de resolución significativamente diferentes del universo comparable?

## Principios
- Evidencia antes que interpretación.
- Cada dato debe ser trazable a una fuente.
- Separar hechos extraídos de clasificaciones analíticas.
- No etiquetar a una persona como corrupta únicamente por resultados judiciales.
- Mantener documentos originales y hashes.
- Extracciones de IA siempre auditables.
- Revisión humana para variables sensibles.
- Versionar taxonomías, prompts y transformaciones.

## Unidad de análisis
La unidad primaria es el **expediente/caso**, conectado a una secuencia de actuaciones y resoluciones.

Entidades principales:
- Caso / expediente
- Resolución
- Actuación procesal
- Órgano jurisdiccional
- Juez / magistrado
- Persona / organización procesal
- Delito / materia
- Recurso
- Fuente documental
- Cita jurisprudencial

## Alcance inicial
### Fase 1 — Corte de Constitucionalidad
Construir el pipeline usando el Sistema de Consulta de Jurisprudencia Constitucional, gacetas y expedientes públicamente consultables.

### Fase 2 — CSJ / Casación
Incorporar resoluciones de casación, amparo, conflictos de competencia y otras colecciones disponibles por CENADOJ/OJ.

### Fase 3 — Salas de Apelaciones
Reconstruir decisiones de segunda instancia y vincularlas con los expedientes de origen.

### Fase 4 — Primera instancia
Crear historiales de jueces y órganos priorizados, comenzando con una muestra de casos de alto interés público y ampliando después el universo.

### Fase 5 — Análisis longitudinal
Comparación entre jueces, órganos, cohortes temporales, delitos y tipos de litigante.

## Fuentes públicas iniciales verificadas (29-08-2026)
- Corte de Constitucionalidad — Sistema de Consulta de Jurisprudencia Constitucional: https://jurisprudencia.cc.gob.gt/sjc/
- CC — Portal de Jurisprudencia: https://jurisprudencia.cc.gob.gt/ptmp/
- CC — Gaceta Jurisprudencial: https://cc.gob.gt/index.php/gaceta-jurisprudencial/
- CC — servicios y consulta de expedientes: https://cc.gob.gt/index.php/servicios/
- Organismo Judicial — Portal de Servicios Electrónicos: https://portal.oj.gob.gt/
- OJ — Consultas Externas: https://portal.oj.gob.gt/?page_id=6577
- CENADOJ — normativa, jurisprudencia y compilaciones del Organismo Judicial.

**Nota:** el acceso y la estructura de estos portales puede cambiar. Los conectores deben respetar robots.txt, términos de servicio, límites técnicos y controles de acceso. No evadir CAPTCHAs ni autenticación.

## Productos
1. Base estructurada de casos y resoluciones.
2. Buscador por juez, magistrado, órgano, expediente, delito y actor.
3. Línea de tiempo procesal por expediente.
4. Perfil estadístico por juez/magistrado.
5. Matriz de confirmación/revocación entre instancias.
6. Dashboard de celeridad.
7. Grafo de precedentes y citas.
8. Detector de patrones atípicos para revisión humana.
9. Exportaciones CSV/JSON/Parquet.
10. Fichas de evidencia con enlace al documento original.

## Definición de éxito del MVP
El MVP estará completo cuando pueda tomar un conjunto de expedientes de la CC, descargar/registrar las resoluciones públicas, extraer sus metadatos, reconstruir su cronología y calcular automáticamente indicadores básicos con trazabilidad documental.
