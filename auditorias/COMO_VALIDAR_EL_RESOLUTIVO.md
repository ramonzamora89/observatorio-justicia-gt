# Cómo revisar la muestra de validación

**Ficha:** `data/manifests/cc_ptmp/validacion_resolutivo.csv` — 100 filas.

## Guárdala como «CSV UTF-8», no como «CSV»

Antes de nada, porque es la parte que ya falló una vez.

Numbers y Excel ofrecen dos exportaciones que se llaman casi igual. La de
«CSV» a secas guarda en la codificación antigua del sistema —en Mac, MacRoman—
y ahí las tildes que escribas dejan de ser legibles. **Elige siempre la opción
que diga UTF-8.**

Si se cuela igual, no pasa nada: `leer_texto()` repara byte a byte y hay un test
de regresión. Lo que **no** hay que hacer es «arreglarlo» convirtiendo el archivo
entero a cp1252. La ficha que volvió el 30 de agosto era UTF-8 válido con
**tres** bytes MacRoman sueltos; convertirla entera habría arreglado esos tres y
roto los **57 guiones** que ya estaban bien.

## Qué se está midiendo y por qué

Este proyecto publica una matriz de confirmación/revocación —**35,1% amplia
contra 28,1% estricta** sobre n=1.858, universo *Apelación de Sentencia de
Amparo*— construida con una regla determinística. `PRD-1.md` §16 exige >95% de
exactitud en el resultado principal.

Recomputa la cifra antes de citarla: vive en `obsgt cc-ptmp tasas` y en
`matriz_apelaciones.json`, no en este documento.

Ya pasó una vez: una revisión manual de tres documentos tumbó la serie de voto
razonado, que estaba medida sobre 1.992 y publicada con intervalos de confianza.
Y volvió a pasar en la fila doce de ésta: **181 documentos cambiaron de bando**.

## Cómo revisar cada fila

1. Abre `url_del_documento`.
2. Busca el **punto resolutivo** —«POR TANTO… resuelve: I)…»— y léelo.
3. Escribe **las dos cosas**:

**`VEREDICTO_CONTROLADO_altera_mantiene_no_aplica`** — una de tres palabras
exactas, que es lo que cuenta el puntuador:

| Escribe | Cuando |
|---|---|
| `altera` | la CC revoca, modifica o anula lo recurrido, o acoge la apelación |
| `mantiene` | confirma lo recurrido, o rechaza la apelación sin tocar la sentencia |
| `no_aplica` | no decide sobre una decisión inferior: aclaración, amparo en única instancia, inadmisión |

**`VEREDICTO_HUMANO_altera_mantiene_otro`** — la misma decisión en prosa, con lo
que hayas visto.

La prosa no es un adorno ni un resto del formato viejo. **Fue leyéndola como se
vio el problema del accesorio**, que un desplegable no habría dejado ver: las dos
filas que lo destaparon no decían «altera» ni «mantiene», describían un fallo que
confirmaba y sólo movía el plazo de una multa. Un token solo habría perdido eso.

Si el token está escrito, manda él. Si lo dejas vacío, el puntuador lee la prosa.

**Lee el documento, no la columna `lo_que_leyo_la_maquina`.** Esa columna está al
final a propósito. Si la regla leyó el punto equivocado —le pasó: durante un
tiempo tomaba la integración del tribunal en vez del fallo— mirarla primero
esconde justo el error que se busca.

## El caso que decide más

30 de las 100 filas son del tipo:

> «Sin lugar el recurso de apelación… **como consecuencia, confirma la sentencia
> apelada, con la modificación que…**»

Desde el 30 de agosto esas 30 están partidas en dos por el criterio del
accesorio:

- **17** donde lo único que cambia es la multa, las costas o el plazo de pago al
  abogado patrocinante. Cuentan como **mantiene**: `confirma; la modificacion es
  accesoria`.
- **13** donde la modificación toca el fondo —el amparo, el acto reclamado, la
  pena—. Siguen contando como **altera**.

Ese criterio decide el 22% de todas las alteraciones y es **un criterio, no un
hecho**. Si al leer una de estas filas te parece que la raya está en otro sitio,
escríbelo en la prosa: es la pregunta de si el criterio es correcto, y la
respuesta es jurídica, no de ingeniería.

## Dos filas pendientes

Las filas **7 y 10** son precisamente las que destaparon el accesorio. Tienen la
prosa escrita pero el token vacío a propósito: describiste el fallo sin dictar
veredicto, y rellenarlo por ti sería escribir como tuyo un juicio que no hiciste.
Ahora que el criterio existe, ponles el token.

## Al terminar

```bash
uv run obsgt cc-ptmp validar --puntuar
```

Da la exactitud por estrato y la global ponderada —los estratos tienen tamaños
distintos y la regla discutida está sobrerrepresentada a propósito— con su
intervalo de confianza.

**El veredicto se dicta sobre el intervalo, no sobre el punto.** Con 12 filas
revisadas la exactitud es 100% y el límite inferior 75,7%: eso es compatible con
un clasificador del 80% y no distingue nada, así que el comando responde `SIN
EVIDENCIA SUFICIENTE` y no `CUMPLE`. Hacen falta 30 o 40 para que el intervalo
empiece a separar.

No hace falta terminar las 100 de una vez: las filas en blanco se ignoran y el
cálculo se hace sobre lo revisado. El archivo ya está en orden aleatorio
—comprobado: año medio 2015,1 en las 12 revisadas contra 2015,0 en las 88
restantes—, así que puedes ir en orden sin sesgar la medición.
