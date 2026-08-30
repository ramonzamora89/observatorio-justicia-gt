# Ficha de fuente — Gaceta Jurisprudencial

**Consultado:** 2026-08-30
**Índice:** `https://cc.gob.gt/index.php/gaceta-jurisprudencial/`
**Documentos:** `https://cc.gob.gt/wp-content/uploads/…`

## Acceso: el índice y los documentos se comportan distinto

| Recurso | Con el user-agent del proyecto |
|---|---|
| `robots.txt` | **200** — `User-agent: *` → `Allow: /`, solo `/wp-admin/` bloqueado |
| PDFs en `/wp-content/uploads/` | **200** |
| Página índice `/index.php/gaceta-jurisprudencial/` | **403** |

El 403 es del WAF del CMS y afecta **solo a la página HTML**. Los documentos se
sirven sin problema. La división que quedó: **el índice se leyó con un navegador
—una visita, a ritmo humano— y los documentos los baja el collector**, con su
límite de tasa, su hash y su manifest. No se evadió ningún control: `robots.txt`
permite el acceso, no hay login ni CAPTCHA, y las peticiones van con la identidad
del proyecto.

Existe además `https://cc.gob.gt/wp-sitemap.xml`, que probablemente evite tener
que abrir el navegador la próxima vez. **No comprobado.**

## Qué contiene, y qué NO

38 PDFs enlazados. Las gacetas 153-156 aparecen íntegras; el resto de las
entradas son `SUMARIO-128` a `SUMARIO-152`.

**No son las sentencias.** Son compilaciones de fichas por expediente:

```
EXPEDIENTE 4239-2024
Sentencia 12 de febrero de 2025
CON LUGAR
Acción constitucional de amparo en única instancia promovida por … contra la
Corte Suprema de Justicia, Cámara Penal. Acto reclamado: …
```

Expediente, fecha, **sentido**, y un resumen del acto reclamado. Sin bloque de
firmas, sin considerandos, sin votos.

## El voto razonado NO está aquí — comprobado

Se fue a la gaceta buscando los votos razonados, porque `KNOWN_ISSUES` §18 la
señalaba como la vía para medir disidencia. **No los tiene.**

Gaceta 155 (enero-marzo 2025), 345 páginas:

| Término | Apariciones |
|---|---|
| `amparo` | 982 |
| `voto` | 4 |
| `disidente` | **0** |
| `razonado` | **0** |

Y es un negativo **comprobado**, no un fallo de lectura: la extracción da
1.081.385 caracteres y 132.262 palabras, con veredicto `usable` (39,7% de
palabras funcionales, 1,0% de fragmentación). El PDF no viene de escáner.

Igual en `SUMARIO-149`, 250 páginas: cero menciones.

**Consecuencia:** la vía que §18 proponía para medir cohesión de la Corte queda
descartada. Si los votos razonados se publican en algún lado, no es aquí.

## Para qué sí sirve

El sentido por expediente en formato compacto, y **cubre 2024-2025**, que está
fuera de la ventana 1996-2023 del estudio actual. Con la misma advertencia de
§16: ese «CON LUGAR / SIN LUGAR» es la etiqueta del amparo, no la matriz de
confirmación/revocación, y subestima la alteración entre 9 y 19 puntos.

## Preservado

`data/raw/cc_gaceta/gaceta-155.pdf`
sha256 `d0dde349026d453d53f1088f8d15f739e785d126abe241420c5096a801bb0c21`
