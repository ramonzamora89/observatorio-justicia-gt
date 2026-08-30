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
uv run pytest                            # 72 tests, ninguno toca la red
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

## Estabilidad del identificador

`obsgt cc-ptmp check-ids` comprueba que el `id` del portal sigue designando el
mismo expediente, por dos caminos independientes: `id → AtributoElastic →
expediente` y `expediente → API de expedientes → id`.

Línea base del 29-08-2026: **20/20 consistentes, 0 discrepan**. Eso descarta que
el `id` sea un número de sesión. La persistencia en el tiempo exige repetirlo
más adelante contra el mismo manifest; el informe queda en
`data/manifests/cc_ptmp/id_stability_2026-08-29.json`.

## Siguiente tarea recomendada

El **milestone de parsing**: convertir los PDF preservados en texto con
referencia de página, con la comprobación de plausibilidad léxica por documento
que aquí se hizo a mano sobre 2 de 20. Los 20 documentos tienen capa de texto
nativa, así que el camino es `pdftotext`/PyMuPDF, no OCR — pero la comprobación
hay que hacerla igual, porque una capa de texto puede perder letras y verse
completa.

Repetir `check-ids` en unas semanas (KNOWN_ISSUES §5).
