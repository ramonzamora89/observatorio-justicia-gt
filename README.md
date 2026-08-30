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
uv run pytest                            # 140 tests, ninguno toca la red
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
uv run obsgt extract run --limit 5               # con modelo
```

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
