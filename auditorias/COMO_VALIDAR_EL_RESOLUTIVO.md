# Cómo revisar la muestra de validación

**Ficha:** `data/manifests/cc_ptmp/validacion_resolutivo.csv` — 100 filas.

## Qué se está midiendo y por qué

Este proyecto publicó una matriz de confirmación/revocación —44,8% de las
apelaciones alteran la decisión recurrida— construida con una regla
determinística que **nadie ha verificado a mano**. `PRD-1.md` §16 exige >95% de
exactitud en el resultado principal, y ese criterio nunca se midió.

Ya pasó una vez: una revisión manual de tres documentos tumbó la serie de voto
razonado, que estaba medida sobre 1.992 y publicada con intervalos de confianza.

## Cómo revisar cada fila

1. Abre `url_del_documento`.
2. Busca el **punto resolutivo** —«POR TANTO… resuelve: I)…»— y léelo.
3. Escribe en `VEREDICTO_HUMANO_altera_mantiene_otro` una de tres palabras:

| Escribe | Cuando |
|---|---|
| `altera` | la CC revoca, modifica o anula lo recurrido, o acoge la apelación |
| `mantiene` | confirma lo recurrido, o rechaza la apelación sin tocar la sentencia |
| `otro` | no decide sobre una decisión inferior: aclaración, amparo en única instancia, inadmisión |

**Lee el documento, no la columna `lo_que_leyo_la_maquina`.** Esa columna está al
final a propósito. Si la regla leyó el punto equivocado —le pasó: durante un
tiempo tomaba la integración del tribunal en vez del fallo— mirarla primero
esconde justo el error que se busca.

## El caso que decide más

30 de las 100 filas dicen `confirma con modificacion`. Son fallos del tipo:

> «Sin lugar el recurso de apelación… **como consecuencia, confirma la sentencia
> apelada, con la modificación que…**»

Están contados como **altera**, con este criterio: si la sentencia revisada
cambió, dejó de ser la misma decisión. Es un criterio, no un hecho, y **mueve la
tasa global de 44,8% a 28,1%**.

Si al leerlos te parece que deberían contar como `mantiene`, escríbelo. No es un
error de la máquina: es la pregunta de si el criterio es el correcto, y la
respuesta es jurídica, no de ingeniería.

## Al terminar

```bash
uv run obsgt cc-ptmp validar --puntuar
```

Da la exactitud por estrato y la global ponderada —los estratos tienen tamaños
distintos y la regla discutida está sobrerrepresentada a propósito— con su
intervalo de confianza, y dice si se cumple el criterio del PRD.

No hace falta terminar las 100 de una vez: las filas en blanco se ignoran y el
cálculo se hace sobre lo revisado.
