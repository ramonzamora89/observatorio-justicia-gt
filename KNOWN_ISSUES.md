# Problemas conocidos

Estado al cierre del **CC discovery spike** (29-08-2026).

## Resueltos el 29-08-2026

### 1. ~~El user-agent apunta a una URL que no existe~~
Resuelto: el repositorio es público y la URL del `contact_url` en
`config/sources/cc_ptmp.toml` resuelve.

### 2. ~~`ai-input` sin decidir~~
Resuelto y documentado en la ficha de fuente. `ai-train=no` se acata: el
proyecto no entrena ni afina modelos con este material. `ai-input` no está
señalizado, y el propio `robots.txt` dice que en ese caso el operador "ni
concede ni restringe". La extracción con LLM procede.

**Sigue sin comprobar**, y es cuestión aparte: si las sentencias de la CC son
textos oficiales excluidos de derecho de autor en Guatemala (Decreto 33-98).

## Límites del dato

### 3. Los 20 documentos no son una muestra
Las consultas semilla determinan qué sale. Es una prueba técnica de adquisición.
Sin denominador no hay patrón, y este collector todavía no lo produce —
`recordsFiltered` (66,024 para "amparo") es el primer paso hacia uno, no un
sustituto.

### 4. El mismo expediente tiene dos formatos según dónde se lea
La API da `61-1998`; `AtributoElastic.aspx` y el PDF dan `61-98`. Solo en
expedientes anteriores al 2000 — 9 de los 20 de la primera corrida. El collector
**no los unifica a propósito**: normalizar es otra capa. Pero la capa de
vinculación tiene que saberlo o concluirá que no coinciden.

### 5. El `id` es consistente entre rutas, pero falta la prueba del tiempo
**Comprobado el 29-08-2026:** los 20 identificadores van y vuelven al mismo
expediente por **dos endpoints independientes** — se obtuvieron por el de texto
libre y se confirmaron por el de expedientes. 20/20 consistentes, 0 discrepan.
Eso descarta que sea un número de sesión: es una clave del repositorio.

**Lo que eso todavía no prueba** es la persistencia en el tiempo, que por
definición exige que pase tiempo. `obsgt cc-ptmp check-ids` existe para
volver a correrlo; la línea base está en
`data/manifests/cc_ptmp/id_stability_2026-08-29.json`.

Repetirlo en unas semanas. Si apareciera una discrepancia, la clave natural
pasa a ser `(expediente, fecha_sentencia)`.

### 6. No existe listado completo sin consulta
`mainSearch` vacío devuelve cero. Todo descubrimiento pasa por una consulta, y
toda consulta introduce un criterio de selección.

## Defectos de la fuente que el código ya sortea

### 7. `recordsTotal` no es el total
Devuelve el `length` pedido. El universo está en `recordsFiltered`. Hay test.

### 8. El servidor miente sobre la compresión
Anuncia a veces una codificación que el cuerpo no trae; httpx revienta con
`incorrect header check`. El cliente pide `Accept-Encoding: identity`.

### 13. La taxonomía de efecto procesal está a medias, y a propósito
`normalized_effect` se deriva de `literal_outcome` solo donde la lógica procesal
básica lo sostiene: en una instancia de revisión, rechazar el recurso deja en pie
la decisión recurrida y acogerlo la altera. **Lo demás queda sin valor.**

Completar la tabla a ojo sería convertir una inferencia en un hecho. Y este campo
alimenta la matriz de confirmación/revocación entre instancias, que es un
indicador central: un mapeo mal hecho aquí contamina el resultado y no se nota.

Los casos abiertos —qué efecto tiene un amparo denegado en única instancia, o un
dictamen en opinión consultiva— **requieren criterio jurídico guatemalteco, no de
ingeniería.** Cobertura actual: 13 de 20.

### 14. ~~Un campo del modelo sin evidencia comprobable~~
Revisado a mano. No era una cita inventada: el expediente **894-98** (id 795937)
escribe «expediente setenta y dos**- **noventa y dos» con un espacio después del
guion —resto de un salto de línea que `pdftotext` conserva— y el modelo lo citó
sin ese espacio. La cita era fiel; el cotejo era demasiado literal en un punto
que no debía serlo.

La normalización ahora une los guiones partidos. Es la única licencia que se toma
la comparación, y es estrecha a propósito: sigue sin aceptar sinónimos,
reordenamientos ni elisiones, y hay test de las tres cosas. Resultado: **76 de 76
verificadas**.

### 15. Una inconsistencia interna del propio documento, para revisión humana
En el expediente **894-98**, la Corte cita: «sentencia […] de fecha **nueve de
abril de mil novecientos noventa y uno**, en el **expediente setenta y dos-
noventa y dos**».

Un expediente de 1992 no puede resolverse en 1991. La inconsistencia está **en la
resolución original**, no en la extracción: puede ser un error de mecanografía del
tribunal, o el expediente puede ser 72-91.

**No se corrige.** Se registra tal como consta, porque "arreglar" en silencio la
cita de un tribunal es fabricar evidencia. Al construir el grafo de precedentes,
este vínculo debe quedar sin resolver y marcado, no adivinado hacia el año que
parezca más plausible.

Verificable en:
`https://jurisprudencia.cc.gob.gt/Sentencias/795937.894-98.pdf`

### 16. El «Sentido de la sentencia» del portal NO es la confirmación/revocación
**Comprobado el 30-08-2026 contra 70 documentos.** El campo que publica la CC se
refiere al **amparo**, no a la **apelación**. Un expediente puede decir
«Con Lugar -Derecho de defensa» y su fallo resolver «I) Confirma la sentencia
apelada»: la protección constitucional se concedió, pero la decisión recurrida
quedó en pie.

**Contraste final, sobre 1,686 apelaciones** (criterio amplio):

| Sentido del portal | Altera lo recurrido | No lo altera |
|---|---|---|
| Con Lugar (n=563) | 393 (70%) | 170 (30%) |
| Sin Lugar (n=1,123) | 358 (32%) | 765 (68%) |

**El piloto de 70 documentos daba otra cosa**: 62%/38% para «Con Lugar» y 11%/89%
para «Sin Lugar», este último calculado sobre 18 casos. El desacuerdo entre
etiqueta y fallo resultó **mayor** en la corrida grande, no menor, así que la
conclusión se refuerza. Pero la distancia entre n=18 y n>1.000 se deja escrita:
es en sí misma un dato sobre cuánto confiar en un piloto.

Está correlacionado, pero **usarlo como sustituto de la matriz de
confirmación/revocación misclasificaría cerca de un tercio de los «Con Lugar»**.

Consecuencia para el análisis: las tasas calculadas sobre este campo miden
«proporción registrada como Con Lugar», no «proporción en que la CC alteró la
decisión recurrida». Son variables distintas y no deben nombrarse igual.

Para obtener la matriz real hay que leer el punto resolutivo del documento. Una
regex cruda sobre «resuelve: I)» clasificó 45 de 70 (64%); el resto necesita
lectura. Es trabajo de la capa 3.

### 17. La tendencia del «Con Lugar» era, en buena parte, un artefacto de medicion
La capa 2 mostraba que la proporcion etiquetada «Con Lugar» pasaba de ~28% a 51%
entre 2003 y 2023 — un aparente duplicado. Leido el fallo real en 2.000
apelaciones, la tasa de alteracion de la decision recurrida es:

| Periodo | Etiqueta | Fallo real | La etiqueta subestima |
|---|---|---|---|
| 2003-2010 | 26.8% | 45.5% | 18.7 pp |
| 2011-2015 | 22.6% | 41.0% | 18.4 pp |
| 2016-2019 | 28.0% | 40.6% | 12.6 pp |
| 2020-2023 | 42.7% | 51.7% | 9.0 pp |

Dos conclusiones, y ninguna es la que sugeria la etiqueta:

1. **La tasa real siempre fue mucho mas alta** (~45% de media, no ~29%).
2. **La forma de la serie es distinta.** La etiqueta subia de forma sostenida; el
   fallo real baja y luego sube. Y buena parte del alza aparente es que la
   etiqueta se volvio mas fiel con los anos: la brecha se cierra de 18,7 a 9,0
   puntos.

Lo que si se sostiene: 2020-2023 (51,7%) esta significativamente por encima de
2011-2015 y 2016-2019 (p<0,001), **pero no de 2003-2010** (p=0,06). El nivel
actual no es inedito.

## Deuda menor

### 9. `.gitignore` menciona `data/pdf/`, que no se usa
La estructura vigente es la de `PRD-1.md` §15 (`data/{raw,parsed,processed}`)
más `data/manifests/` versionado y `data/cache/` ignorado. `data/pdf/` es
residuo; se deja el renglón porque no estorba.

### 10. `*.pdf` es un glob global en `.gitignore`
Una fixture PDF de test quedaría ignorada en silencio. Por eso los tests de PDF
usan bytes sintéticos en memoria, no archivos.

### 11. ~~No hay verificación automática de plausibilidad léxica~~
Resuelto: `parsers/quality.py` la hace por documento. Dos límites **medidos**,
no supuestos:

- una capa de texto que se comiera solo las **w** es indetectable por
  frecuencia (el español la usa un 0.01%);
- la fragmentación tipo escáner se detecta desde **~8% de palabras afectadas**;
  por debajo pasa. El corpus real está en 0.6–2.1%, así que hay cuatro veces de
  margen, pero el piso existe.

### 12. La prueba de OCR se hizo sobre un caso fabricado, no encontrado
Ninguno de los 20 documentos necesita OCR: todos tienen capa nativa de Word. Para
probar la red de seguridad se rasterizó uno bueno y se midió el OCR contra el
texto del original: 99.8% de palabras recuperadas.

Eso valida el mecanismo, **no predice el rendimiento sobre escaneos reales de
tribunal**, que traen inclinación, manchas, sellos y fotocopias de fotocopias.
La primera vez que aparezca un escaneo de verdad hay que volver a medir.
