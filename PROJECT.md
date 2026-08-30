# Observatorio de Resoluciones Judiciales de Guatemala

## Visión
Construir un repositorio reproducible y auditable de resoluciones judiciales guatemaltecas que permita estudiar, a través del tiempo, el comportamiento de órganos jurisdiccionales, jueces y magistrados mediante indicadores verificables.

El sistema **no debe inferir corrupción a partir de una resolución aislada**. Su función es identificar patrones medibles —celeridad, revocación, confirmación, criterios, trato procesal y resultados— y conservar la evidencia primaria que permita investigar esos patrones.

## Estado (30-08-2026)

**Fase 1 completa de punta a punta.** El pipeline descubre, adquiere, preserva,
parsea, extrae y analiza resoluciones de la Corte de Constitucionalidad, y
produce el denominador.

| Hito | Estado |
|---|---|
| Censo del universo publicado | **66,025 documentos**, 68,150 expedientes, 1986-2026 |
| Fichas del portal recogidas | 8,594 (muestra estratificada 1996-2023, e=5%) |
| Resolutivo leído del fallo | 1,992 apelaciones, 99,7% por regla determinística |
| Extracción con evidencia | 20 documentos, 208 valores, 75/76 del modelo verificados |
| Base consultable | DuckDB con procedencia y evidencia por campo |
| Gasto de API | **$5.18** en toda la construcción |

**Lo que aún no se puede afirmar:** el clasificador del resolutivo no tiene error
medido. `PRD-1.md` §16 exige >95% de exactitud y la validación está en curso. Sin
ella, la matriz de confirmación/revocación es un número sin barra de error.

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

## Alcance

### Fase 1 — Corte de Constitucionalidad · **hecha**
Pipeline completo sobre el Portal de Jurisprudencia. El portal expone una API
JSON pública: no hizo falta navegador headless ni replicar `__VIEWSTATE`.

### Fases 2, 3 y 4 — CSJ, Salas de Apelaciones y primera instancia · **sin vía**
Comprobado el 30-08-2026: el portal del Organismo Judicial ofrece públicamente
solo consulta de antecedentes penales, y **el resto de servicios requiere ser
abogado y notario colegiado**. Además responde con un desafío anti-bot de
Radware. SICEJ pide expediente y contraseña, y solo lo usan las partes. CENADOJ
publica estadística, no resoluciones, y su serie desagregada se corta en 2011.

No es que cueste automatizarlo: **no está disponible sin credencial
profesional**. Ver `sources/oj/FICHA_OJ_PRIMERA_INSTANCIA.md`.

Quedan vías institucionales, no técnicas: CIDEJ (sin probar) y una solicitud
formal de información, con el problema de que el OJ no tiene ventanilla que la
reciba.

**Vía parcial disponible:** la ficha de la CC identifica al órgano inferior. Con
las 8,594 fichas ya recogidas se ven 164 casos de la Sala Segunda de Apelaciones,
154 de la Primera, 119 de la Tercera. Es una muestra sesgada —solo lo que llegó
en amparo a la CC— y sirve para preguntas acotadas declarando el sesgo.

### Fase 5 — Análisis longitudinal
Comparación entre órganos, cohortes temporales, materias y tipos de litigante.

**Advertencia sobre la pregunta 4.** «¿Qué jueces presentan patrones atípicos?»
probablemente **no tiene respuesta en la CC**: es un tribunal colegiado, todos los
firmantes firman la mayoría, y se comprobó que el voto individual no se publica
—ni en las sentencias ni en la Gaceta Jurisprudencial—. Saber que un magistrado
estuvo en 200 salas que alteraron el 45% no dice nada sobre él. La pregunta se
responde donde un juez decide solo: primera instancia, que hoy no tiene vía.

## Fuentes públicas iniciales verificadas (29-08-2026)
- Corte de Constitucionalidad — Sistema de Consulta de Jurisprudencia Constitucional: https://jurisprudencia.cc.gob.gt/sjc/
- CC — Portal de Jurisprudencia: https://jurisprudencia.cc.gob.gt/ptmp/
- CC — Gaceta Jurisprudencial: https://cc.gob.gt/index.php/gaceta-jurisprudencial/
- CC — servicios y consulta de expedientes: https://cc.gob.gt/index.php/servicios/
- Organismo Judicial — Portal de Servicios Electrónicos: https://portal.oj.gob.gt/
- OJ — Consultas Externas: https://portal.oj.gob.gt/?page_id=6577
- CENADOJ — normativa, jurisprudencia y compilaciones del Organismo Judicial.

### Estado de acceso, comprobado el 30-08-2026

| Fuente | Estado |
|---|---|
| CC — Portal de Jurisprudencia `/ptmp/` | **abierto**, API JSON pública, `robots.txt` permite |
| CC — Gaceta Jurisprudencial | **abierta**: los PDF responden a nuestro UA; solo la página índice da 403 por WAF |
| CC — sistema anterior `/sjc/` | ASP.NET con callbacks DevExpress. Caracterizado, **no atacado** |
| CC — `consultajur.cc.gob.gt` | **403 con desafío Cloudflare**. Control de acceso: no se evade |
| OJ — Portal de Servicios Electrónicos | **cerrado**: antecedentes penales al público; el resto exige abogado y notario colegiado, más desafío anti-bot Radware |
| OJ — SICEJ | **cerrado**: expediente + contraseña, solo partes |
| CENADOJ | accesible, pero publica **estadística, no resoluciones**; serie desagregada cortada en 2011 |

**Nota:** el acceso y la estructura de estos portales puede cambiar. Los conectores deben respetar robots.txt, términos de servicio, límites técnicos y controles de acceso. No evadir CAPTCHAs ni autenticación.

### Señales de contenido
`jurisprudencia.cc.gob.gt` y `cc.gob.gt` sirven
`Content-Signal: search=yes, ai-train=no, use=reference`. El proyecto **no
entrena ni afina modelos** con este material. La extracción cae en `ai-input`,
que el propio archivo declara ni concedido ni restringido. Decidido y fechado el
29-08-2026.

## Productos
Estado: ✅ hecho · 🟡 parcial · ⬜ pendiente

1. ✅ Base estructurada de casos y resoluciones (DuckDB).
2. 🟡 Buscador — la base permite consultar por expediente, órgano y parte; falta interfaz.
3. ⬜ Línea de tiempo procesal por expediente.
4. ⬜ Perfil por juez/magistrado — ver advertencia sobre la pregunta 4.
5. 🟡 Matriz de confirmación/revocación — calculada por período; **falta medir su error**.
6. ⬜ Dashboard de celeridad — falta `fecha_ingreso`, que consta en pocos documentos.
7. ⬜ Grafo de precedentes — las citas se extraen, sobre 20 documentos.
8. ⬜ Detector de patrones atípicos.
9. 🟡 Exportaciones — DuckDB exporta; falta comando.
10. ✅ Fichas de evidencia con enlace y sha256 del documento.

## Definición de éxito del MVP
El MVP estará completo cuando pueda tomar un conjunto de expedientes de la CC, descargar/registrar las resoluciones públicas, extraer sus metadatos, reconstruir su cronología y calcular automáticamente indicadores básicos con trazabilidad documental.


## Lo que esta construcción enseñó, y no estaba en el plan

**Tres series temporales que parecían conducta de la Corte resultaron ser cómo la
fuente registra las cosas.** La etiqueta «Sentido de la sentencia», que subía
porque se volvió más fiel; la cola creciente del resolutivo, que era la firma
electrónica; y el voto razonado, que medía una práctica de anotación abandonada
en 2010. Las tres están documentadas en `KNOWN_ISSUES.md`, con la retractación
donde corresponde.

De ahí la regla que este proyecto añade a las heredadas: **antes de publicar
cualquier serie temporal, preguntar qué más cambió en el documento durante ese
período.**

Y la que la confirmó desde fuera: una revisión manual de tres PDF tumbó un
hallazgo medido sobre 1,992 documentos y publicado con intervalos de confianza.
Ninguna suite de tests sustituye abrir el documento.
