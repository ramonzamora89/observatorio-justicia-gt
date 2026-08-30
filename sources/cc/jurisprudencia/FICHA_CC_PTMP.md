# Ficha de fuente — Portal de Jurisprudencia de la Corte de Constitucionalidad

**Consultado:** 2026-08-29 (hora de Guatemala; los archivos de
`snapshots/` llevan fecha UTC, por eso dicen 2026-08-30)
**Host:** `jurisprudencia.cc.gob.gt`
**Estado:** accesible, sin login ni CAPTCHA, con API JSON pública.
**Evidencia:** `snapshots/` en este mismo directorio, con fecha en el nombre.

Esta ficha es prosa fechada con evidencia, no código. El código la cita y
`config/sources/cc_ptmp.toml` la parametriza; ninguno de los dos la reemplaza.

---

## 1. robots.txt y señales de contenido

`https://jurisprudencia.cc.gob.gt/robots.txt` — sha256
`842b34303164ead41bccb7c05d1707422e98d108753b397b6dcc19683eb02101`
(el manifest guarda este hash en cada registro, para que "estaba permitido" sea
verificable dentro de un año y no una promesa).

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /
```

Y `Disallow: /` explícito para **ClaudeBot, GPTBot, CCBot, Amazonbot,
Applebot-Extended, Bytespider, CloudflareBrowserRenderingCrawler,
Google-Extended y meta-externalagent**.

**Consecuencia operativa.** El acceso genérico está permitido. El collector se
identifica como `ObservatorioJusticiaGT/0.1.0 (+<url del repo>)`, que cae bajo
`User-agent: *`. No se falsea identidad: se declara una distinta y real. Las
herramientas de fetch de asistentes de IA quedan excluidas por el propio portal
y **no se usaron** para recolectar; el reconocimiento se hizo con el UA del
proyecto.

**Sobre las señales — decisión tomada el 29-08-2026.** El encabezado del archivo
dice que acceder al sitio implica aceptar las señales, y define tres usos por
separado:

- **`ai-train=no`** — entrenar o afinar modelos. Prohibido, y marcado como
  **reserva expresa de derechos bajo el art. 4 de la Directiva UE 2019/790**.
  Este proyecto **no entrena ni afina modelos con este material**, ni cede el
  corpus para ello. Es una restricción que se acata, no que se sortea.
- **`ai-input`** — meter contenido a un modelo para procesarlo (RAG, grounding,
  extracción). **No aparece en la señal.** El propio archivo dice que cuando el
  operador no incluye una señal para un uso, "ni concede ni restringe permiso".
  La extracción estructurada con LLM del milestone siguiente cae aquí.
- **`use=reference`** — la CC concede que los sistemas de IA consuman el
  contenido como referencia. Un producto que publica indicadores con enlace y
  cita al documento original es exactamente ese modo de consumo.

Queda registrado con fecha para no relitigarlo. **Lo que no se comprobó:** si las
sentencias de la CC son textos oficiales excluidos de derecho de autor en
Guatemala (Decreto 33-98). Eso es una cuestión distinta de las señales de
contenido y sigue **no comprobada**.

---

## 2. Las dos APIs JSON

El portal monta sus tablas con DataTables en modo `serverSide`. **No hay
`__VIEWSTATE` que replicar ni JavaScript que ejecutar**: el JS inline de cada
página declara la URL del endpoint. Playwright no se usó y no hizo falta.

| | `Expediente.aspx` | `TextoLibre.aspx` |
|---|---|---|
| Endpoint | `POST /coredataretriever/api/jurisprudencia/expedientes/v1` | `POST /coredataretriever/api/jurisprudencia/V1` |
| `mainSearch` es | **número de expediente** | **texto libre** |
| `"amparo"` devuelve | 0 | 66,024 |
| `"1920-2003"` devuelve | 1 | — |
| Columnas | 7, incluye `tipoExpediente` | 6, sin `tipoExpediente` |

No son intercambiables. El collector usa `texto_libre` por defecto; el
`tipoExpediente` que le falta lo aporta `AtributoElastic.aspx` por documento.

Cuerpo de la petición (`Content-Type: application/json`):

```json
{"draw":1,"columns":[…],"order":[{"column":0,"dir":"desc"}],
 "start":0,"length":10,"search":{"value":"","regex":false},"mainSearch":"amparo"}
```

Campos por documento: `id`, `expedientes` (lista), `tipoExpediente`,
`fechaSentencia`, `fechaPublicacion`, `intro`, `textoIntegro`, `tema`,
`subTema`, `concordancia`, `pdf`.

### `recordsTotal` NO es el total

Comprobado: devuelve exactamente el `length` pedido — 10 con `length=10`, 25
con `length=25`. **El universo real está en `recordsFiltered`** (66,024 para
"amparo"). Paginar contra `recordsTotal` corta después de la primera página y
hace creer que la fuente tiene diez documentos. El collector usa
`recordsFiltered` y hay un test que lo fija.

`mainSearch` vacío devuelve cero: **no existe listado completo sin consulta.**

---

## 3. `AtributoElastic.aspx?id={id}`

Metadata visible más rica que la de la API. Campos observados:

Año Sentencia · No. Expediente · Fecha de la sentencia · Tercero interesado ·
Postulante · No. Gaceta · Por tipo de expediente · Tribunal de amparo de primer
grado · Por tipo de antecedente · **Sentido de la sentencia** · Autoridad
impugnada.

`Sentido de la sentencia` es el `literal_outcome` de `DATA_MODEL.md` servido
por la propia fuente ("Con Lugar -Derecho de Propiedad", "Sin Lugar -Ausencia de
agravio"). `Postulante`, `Tercero interesado` y `Autoridad impugnada` son las
partes.

**Un campo presente y vacío no es un campo ausente.** "Tribunal de amparo de
primer grado" viene con rótulo y sin valor en varios expedientes. Eso es un dato
sobre la fuente y se conserva como cadena vacía; que no lo hayamos consultado se
expresa distinto (`atributos_fetch` nulo).

---

## 4. El mismo expediente, dos formatos

La API publica `61-1998`; `AtributoElastic.aspx` y el PDF publican `61-98`.
Ocurre en los expedientes anteriores al año 2000. En 9 de los 20 documentos de
la primera corrida.

Es exactamente el riesgo de "numeración inconsistente" de `PRD-1.md` §19, y es
una trampa de vinculación: un cotejo ingenuo entre las dos formas concluye que
no coinciden. **El collector no las unifica** — normalizar es otra capa, y
borrar el original aquí escondería el problema. Ambas formas quedan en el
manifest.

---

## 5. Los PDF

La API entrega la URL con **host IP y esquema http**:
`http://138.94.255.164/Sentencias/798734.1920-2003 AC.pdf` — con un espacio sin
codificar. El propio JS del portal reescribe tres IPs
(`143.208.58.124`, `200.6.233.69`, `138.94.255.164`) al host canónico. El
collector hace lo mismo, sube a https y codifica el path. Guarda ambas URLs.

**El servidor anuncia a veces una compresión que el cuerpo no trae** y la
descarga revienta al descomprimir (`incorrect header check`). Se observó en la
API de listado al paginar. El cliente pide `Accept-Encoding: identity`.

De los 20 documentos de la primera corrida: **todos con capa de texto nativa,
producidos por Microsoft Word** (2007/2016). Ninguno escaneado, ningún
`Producer` de escáner. Entre 4 y 27 páginas. La lectura como prosa de dos de
ellos no mostró letras faltantes. Para el milestone de parsing: este corpus no
necesita OCR, pero la comprobación hay que repetirla en cada lote nuevo.

---

## 6. Otros hosts — lo que NO se comprobó

- **`cc.gob.gt/index.php/gaceta-jurisprudencial/`** → **HTTP 403**. Host distinto,
  con su propia política. Se registra como **no comprobado**, no como "no está".
  Falta verificar su robots.txt por separado.
- **`/sjc/frmSjc.aspx`** (sistema anterior) → ASP.NET WebForms con DevExpress,
  `__VIEWSTATEENCRYPTED` y grids con callbacks propietarios. Caracterizado, **no
  atacado**. Fuera del alcance de este spike.
- **No comprobados:** `Temas.aspx`, `Autos.aspx`, `Internacionales.aspx`,
  `Estructura.aspx`, `ResolucionInteres.aspx`; los boletines mensuales
  jul-2017 → dic-2023; y **la estabilidad del `id` en el tiempo**, que hoy
  aparece en la URL de atributos y en el nombre del PDF pero no se ha verificado
  longitudinalmente.

---

## 7. Advertencia metodológica

Las consultas semilla determinan qué resoluciones salen. Los 20 documentos de la
primera corrida **no son una muestra**: son una prueba técnica de adquisición.
Sin denominador no hay patrón, y este collector todavía no produce denominador.
El `recordsFiltered` de cada consulta es el primer paso hacia uno, no un
sustituto.
