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

## Deuda menor

### 9. `.gitignore` menciona `data/pdf/`, que no se usa
La estructura vigente es la de `PRD-1.md` §15 (`data/{raw,parsed,processed}`)
más `data/manifests/` versionado y `data/cache/` ignorado. `data/pdf/` es
residuo; se deja el renglón porque no estorba.

### 10. `*.pdf` es un glob global en `.gitignore`
Una fixture PDF de test quedaría ignorada en silencio. Por eso los tests de PDF
usan bytes sintéticos en memoria, no archivos.

### 11. No hay verificación automática de plausibilidad léxica del texto extraído
El paso 6 del spike (leer una frase como prosa) se hizo a mano sobre 2 de 20
documentos. Corresponde al milestone de parsing convertirlo en comprobación por
documento.
