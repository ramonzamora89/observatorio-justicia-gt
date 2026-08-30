# Observatorio de Resoluciones Judiciales de Guatemala

Documentación inicial para probar un pipeline automatizado de investigación judicial con Claude Code, Codex u otros agentes de programación.

## Orden de lectura
1. `PROJECT.md`
2. `PRD-1.md`
3. `DATA_MODEL.md`
4. `PIPELINE.md`
5. `CLAUDE.md` o `AGENTS.md`

## Recomendación para comenzar
Abra el directorio como repositorio y entregue al agente esta instrucción:

> Lee PROJECT.md, PRD-1.md, DATA_MODEL.md, PIPELINE.md y CLAUDE.md. Ejecuta únicamente el primer milestone definido en CLAUDE.md. Antes de escribir código, inspecciona la fuente pública y propón el plan técnico. No hagas scraping masivo.

## Importante
El sistema está diseñado para medir patrones objetivos y producir pistas investigativas auditables. No debe convertir automáticamente una correlación, anomalía o resultado judicial en una acusación de corrupción.

---

# Estado: CC discovery spike completado (29-08-2026)

Primer milestone de `CLAUDE.md`. Adquisición reproducible desde el Portal de
Jurisprudencia de la Corte de Constitucionalidad. **Nada de parsing, extracción,
normalización ni análisis todavía.**

## Puesta en marcha

```bash
uv sync                                  # Python 3.12 + dependencias
uv run pytest                            # 188 tests, ninguno toca la red
uv run pytest -m ocr                     # 5 mas: OCR real, lento, opt-in
uv run obsgt cc-ptmp probe               # 2 peticiones: robots.txt + una a la API
uv run obsgt cc-ptmp discover --limit 20 # corrida real, limitada por tasa
uv run obsgt manifest verify data/manifests/cc_ptmp/discovery_manifest.jsonl
uv run obsgt cc-ptmp check-ids           # el id sigue designando el mismo expediente
```

## Resultado de la primera corrida

20 resoluciones, 36 peticiones, ~75 segundos a 0.5 req/s.

- 20/20 registros válidos contra el esquema Pydantic.
- 20/20 sha256 coinciden con el archivo en disco.
- 20/20 expedientes confirmados **contra el texto del propio PDF**.
- 20/20 con `robots.allowed` y el sha256 del `robots.txt` de la corrida.
- 20/20 identificadores consistentes por dos endpoints independientes.
- 0 avisos, 0 documentos no comprobados.
- Los 20 PDF tienen capa de texto nativa (Microsoft Word). Ninguno escaneado.

Salidas: `data/manifests/cc_ptmp/discovery_manifest.jsonl` (versionado) y
`data/raw/cc_ptmp/{año}/{sha256}.pdf` (fuera de git, reconstruible desde el
manifest).

## Lo que este milestone estableció sobre la fuente

`sources/cc/jurisprudencia/FICHA_CC_PTMP.md` tiene la ficha completa con
evidencia fechada en `snapshots/`. Lo esencial:

- **El portal tiene API JSON pública.** No hay `__VIEWSTATE` que replicar ni
  navegador headless que usar. Playwright no se instaló.
- **`robots.txt` permite el acceso genérico y bloquea a los bots de IA.** El
  collector usa un user-agent propio del proyecto, que sí está permitido.
- **`recordsTotal` no es el total** — devuelve el tamaño de página. El universo
  está en `recordsFiltered`.
- **El mismo expediente aparece en dos formatos** (`61-1998` / `61-98`) según
  dónde se lea. El collector no los unifica: eso es normalización.
- `AtributoElastic.aspx` publica **el sentido de la sentencia** y las partes.

## Advertencia

Estas 20 resoluciones **no son una muestra**. Las consultas semilla determinan
qué sale. Sin denominador no hay patrón, y este collector todavía no lo produce.

Problemas conocidos y decisiones pendientes: `KNOWN_ISSUES.md`.

## Base de datos consultable

```bash
uv run obsgt db          # carga todo en data/observatorio.duckdb
```

| Tabla | Filas | Qué es |
|---|---|---|
| `censo` | 66,025 | el universo publicado — el denominador |
| `atributos` | 90,683 | fichas del portal, formato largo |
| `decisions` | 1,992 | resolutivo leído del documento |
| `documents` | 20 | copias inmutables con sha256 |
| `extracciones` | 208 | cada valor con procedencia y evidencia |
| `judicial_officers`, `appeal_links`, `citations` | 0 | **vacías a propósito** |

Las tablas en cero se crean y se declaran vacías: una tabla ausente parece un
olvido, una vacía con su cuenta en cero es un estado del proyecto.

La procedencia viaja con el dato —`portal`, `deterministico`, `llm`— junto a su
página y su cita. En este proyecto tres hallazgos se cayeron por confundir lo que
dice la fuente con lo que dice el documento; la tabla no deja hacerlo.

## El denominador: censo del universo publicado

```bash
uv run obsgt cc-ptmp censo               # ~71 peticiones, ~3 minutos, sin modelo
uv run obsgt cc-ptmp censo --solo-resumen  # rehace el agregado sin red
```

Sin denominador no hay patron: una lista de resoluciones que apuntan en una
direccion no prueba nada sin saber cuantas dicto ese organo y en que sentido.
Este censo es la razon de existir del proyecto.

**Como se enumera.** La busqueda por expediente coincide **por prefijo del
numero**: `5577` devuelve `5577-2015`, `5577-2017`, `5577-2021`... y `1` devuelve
los 14.166 expedientes que empiezan con 1. Como todo numero empieza por un digito
del 1 al 9, nueve prefijos cubren el universo sin solaparse.

### Resultado (29-08-2026)

**66,025 documentos, 68,150 expedientes**, cobertura 1986-2026.

| Tipo de expediente | Documentos | | Decada | Documentos |
|---|---|---|---|---|
| Apelacion de Sentencia de Amparo | 48,168 | | 1980s | 709 |
| Amparo en Unica Instancia | 13,243 | | 1990s | 4,490 |
| Inconstitucionalidad en Caso Concreto | 2,549 | | 2000s | 14,153 |
| Inconstitucionalidad de Caracter General | 1,972 | | 2010s | 28,800 |
| Opinion Consultiva | 66 | | 2020s | 17,912 |

### Lo que este numero NO es

**Es el universo de lo que la Corte publica, no de lo que resuelve.** Se comprobo
que hay numeros de expediente sin resultado (`2-2020` devuelve cero): la CC
publica jurisprudencia seleccionada. Confundir ambas cosas es el sesgo de
seleccion que `PRD-1.md` §19 advierte, y contaminaria cualquier tasa calculada
encima. El resumen lleva esa advertencia dentro del propio archivo.

**Calidad de la fuente, medida:** 43 expedientes de 68,150 (0.06%) tienen
un ano imposible de derivar -- `1298-20158`, `1014-1996a`, `196-69`. **No se
corrigen**: quedan contados aparte. Y 467 documentos aparecian en dos prefijos a
la vez porque acumulan expedientes de numeros distintos; se deduplican por `id`,
sin lo cual el universo saldria inflado.

El censo completo pesa 17 MB y no va a git; el resumen agregado, que es el
denominador, si se versiona.

## Parsing y OCR

```bash
uv run obsgt parse run                   # PDF -> texto, con OCR de respaldo
uv run obsgt parse run --no-ocr          # sin OCR: lo dudoso se marca para revision
```

El texto se conserva **por pagina**, con marcador `===PAGINA n===`: una cita sin
numero de pagina no es verificable, y `evidence_spans` exige la pagina.

### Cuando se hace OCR, y cuando no

El orden de `PIPELINE.md` es texto nativo primero y OCR solo si hace falta.
"Hace falta" no se decide por corazonada, sino por dos comprobaciones:

1. **Quien produjo la capa de texto.** Si viene de un escaner o de un OCR ajeno,
   se descarta sin mirarla. Un PDF con texto no es un PDF con texto usable.
2. **Si el texto se lee como prosa** — la comprobacion de plausibilidad lexica.

Rutas posibles: `capa_nativa`, `ocr_por_productor`, `ocr_por_ausencia`,
`ocr_por_calidad`, `revision_humana`, `no_comprobado`. Las dos ultimas no
significan que el documento este vacio.

### La comprobacion de plausibilidad lexica

Automatiza el "leer una frase como prosa" que antes se hacia a mano. Mide cuatro
cosas independientes sobre el texto extraido:

| Senal | Que detecta | Corpus real | Umbral |
|---|---|---|---|
| Letras ausentes | una capa que se come letras y se ve completa | ninguna | <15% de lo esperado en espanol |
| Palabras funcionales | texto que no es prosa | 41.7–46.4% | >=18% |
| Fragmentacion | OCR de escaner que parte las palabras | 0.6–2.1% | <=12% |
| Densidad | ausencia de capa de texto | — | >=200 caracteres |

**Limites conocidos, medidos:** una capa que se comiera solo las **w** es
indetectable por frecuencia, porque el espanol la usa un 0.01%. Y la
fragmentacion se detecta desde ~8% de palabras afectadas; por debajo pasa.

### Resultado sobre el corpus

Los 20 documentos: **20/20 por capa nativa**, ninguno necesito OCR. Todos
producidos por Microsoft Word, ninguno escaneado.

Como no habia ningun caso malo con el que probar la red de seguridad, se
fabrico: se rasterizo un documento bueno hasta dejarlo sin capa de texto y se
midio el OCR **contra el texto del original**. Resultado del 29-08-2026:

- el triaje detecto la ausencia de capa;
- `ocrmypdf --force-ocr -l spa` tardo 6.9 s en 5 paginas;
- **99.8% de palabras recuperadas**, 5/5 paginas, numero de expediente intacto;
- el texto recuperado pasa la comprobacion de calidad.

Esa medicion es el test `tests/test_ocr_integracion.py`, reejecutable.

## Extraccion de hechos procesales

```bash
uv run obsgt extract run --solo-deterministico   # sin modelo, sin costo
export ANTHROPIC_API_KEY=...                     # solo para la ultima capa
uv run obsgt extract run                        # con modelo
uv run obsgt extract reprocess                  # rehace la conversion, 0 tokens
```

### La respuesta del modelo se guarda entera

`raw_model_response` conserva el JSON íntegro de cada llamada, por la misma razón
que `raw_api_record` en el discovery: **corregir la conversión de un campo no
debe obligar a volver a pagarle al modelo.**

Esa lección costó una corrida completa. Cuando se arreglaron el parser de fechas
en letras y el mapeo de la cláusula resolutiva, `extract reprocess` subió
`normalized_effect` de 3 a 13 documentos **sin gastar un token**.

### Resultado sobre los 20 documentos

**208 valores extraídos.** 76 del modelo, 68 por regla determinística, 64 del
portal. De los 76 del modelo, **75 con evidencia verificada** contra el texto.

| Campo | Cobertura | | Campo | Cobertura |
|---|---|---|---|---|
| expediente | 20/20 | | literal_outcome | 19/20 |
| fecha_resolucion | 20/20 | | postulante | 14/20 |
| tipo_proceso | 20/20 | | normalized_effect | 13/20 |
| organo_origen | 20/20 | | autoridad_impugnada | 12/20 |
| magistrados | 20/20 | | fecha_ingreso | 7/20 |
| resolucion_impugnada_fecha | 16/20 | | tercero_interesado | 6/20 |
| citas | 16/20 | | ponente | 5/20 |

Los campos bajos **no son fallos**: `ponente` no consta en la mayoría de las
resoluciones de la CC, y `normalized_effect` está deliberadamente incompleto
(ver `KNOWN_ISSUES` §13).

### Tres capas, y cada campo dice de cual salio

| Capa | Que aporta | Cobertura sobre los 20 |
|---|---|---|
| **Portal** | lo que publica `AtributoElastic.aspx` | 64 valores |
| **Deterministica** | fecha, expediente, tipo, organo, por regla | 55 valores |
| **Modelo** | solo lo que esta en el cuerpo | los 6 campos restantes |

Sin llamar a ningun modelo se llenan **119 valores en 20 documentos**. Al modelo
le queda lo que ninguna otra capa puede dar: fechas procesales, resolucion
impugnada, magistrados firmantes, ponente, citas jurisprudenciales, y el sentido
del fallo en los 8 documentos donde el portal no lo publica.

### Toda cita se coteja contra el documento

Un campo con una cita **parecida** al documento es tan peligroso como uno
inventado, y se ve igual de bien en un JSON. Por eso cada valor de procedencia
`llm` se verifica automaticamente:

- campos simples: la cita debe ser una subcadena **literal** del documento;
- magistrados: se comprueba **cada nombre por separado**, no el bloque unido --
  el pie de firmas viene partido por saltos de pagina, pero un nombre que no
  aparece es una persona que no firmo;
- citas jurisprudenciales: su texto debe estar en el documento.

Lo que no pasa **se marca, no se borra**: saber que el modelo propone valores sin
respaldo, y con que frecuencia, es una medida de su fiabilidad.

Primera corrida real (3 documentos, Opus 5): **8 de 8 valores del modelo con
evidencia verificada**. En la corrida anterior, con el prompt v1, uno fallo
porque el modelo elidio el centro de la cita con puntos suspensivos. El cotejo
lo rechazo, que es lo correcto; el prompt v2 lo pide explicitamente.

### Lo que el esquema hace cumplir

- **`null` es un resultado valido.** Un extractor que nunca devuelve `null`
  esta inventando.
- **Un valor sin cita se descarta.** Si el modelo no puede señalar donde lo
  leyo, no lo leyo.
- **Una capa mas confiable nunca se sobrescribe.** Lo que publica el portal no
  lo pisa el modelo.
- **Version de prompt (con sha256), modelo, commit y tokens** quedan en cada
  registro. La extraccion es reproducible y auditable meses despues.
- **No hay ningun campo donde valorar la conducta de una persona.** Se extraen
  hechos procesales; las clasificaciones analiticas van en otra tabla y con
  revision humana.

### Fechas escritas en letras

«Guatemala, treinta y uno de octubre de dos mil trece» se resuelve por
calendario, no por modelo: es reproducible y gratis. Cotejado contra el portal,
**16 de 16 coinciden** donde el portal publica la fecha, y la regla llena las
**4** en que el portal la trae vacia.

La fecha se ancla al encabezado del propio tribunal. Tomar la primera fecha del
texto daba, en 3 de 20 documentos, la de la sentencia **recurrida** -- otro
tribunal, otro año. Con la latencia como indicador central, eso no es un detalle
de formato.

## Estabilidad del identificador

`obsgt cc-ptmp check-ids` comprueba que el `id` del portal sigue designando el
mismo expediente, por dos caminos independientes: `id → AtributoElastic →
expediente` y `expediente → API de expedientes → id`.

Línea base del 29-08-2026: **20/20 consistentes, 0 discrepan**. Eso descarta que
el `id` sea un número de sesión. La persistencia en el tiempo exige repetirlo
más adelante contra el mismo manifest; el informe queda en
`data/manifests/cc_ptmp/id_stability_2026-08-29.json`.

## Siguiente tarea recomendada

El **extractor**: convertir el texto por página en JSON validado por Pydantic,
con `evidence_span` y `confidence` por campo, según MVP-2 de `PRD-1.md`.

Buena parte ya viene servida por la fuente y no hay que pedírsela a un modelo:
`AtributoElastic.aspx` publica el sentido de la sentencia, el postulante, el
tercero interesado, la autoridad impugnada y el tipo de expediente. El LLM debe
encargarse de lo que solo está en el cuerpo del documento —fechas procesales,
resolución impugnada, magistrados firmantes, ponente, citas jurisprudenciales— y
devolver `null` cuando no conste.

Repetir `check-ids` en unas semanas (KNOWN_ISSUES §5).
