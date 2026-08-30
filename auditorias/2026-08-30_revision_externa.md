# Peticiones y arreglos para el Observatorio de Resoluciones Judiciales

**Fecha:** 30 de agosto de 2026
**Origen:** revisión externa e independiente, hecha sobre los datos en disco y no
sobre la documentación.

Esta auditoría llegó de fuera del equipo que escribió el código. Se conserva en el
repositorio con su redacción original —incluidas las partes en que señala errores
que ya se corrigieron— porque el valor de una revisión externa está en que quede
el rastro de qué se encontró y cuándo, no solo el arreglo.

**Estado del repo al cerrar esta revisión (11:35):** commit `5e752dc`, con
`src/observatorio_gt/resolutivo.py` modificado sin commitear y una corrida nueva
de `estudio-apelaciones --por-periodo 500` iniciada a las 11:31.

**Sobre las cifras de la matriz de confirmación/revocación: aquí no van.** La
corrida de las 09:15 terminó a las 10:19 con 2.000 documentos, y sus números
llegué a leerlos. No los traslado por dos razones, y la segunda es la que manda:

1. `apelaciones.jsonl` se reinició al arrancar la corrida de las 11:31, así que
   esas cifras ya no se verifican contra el disco.
2. Salieron de la versión anterior de la regla, y el arreglo en curso dice que
   limitar la búsqueda a la cola del documento perdía 42 de 2.000 **y el sesgo
   corría contra los años recientes**, porque los fallos con voto razonado traen
   texto después del resolutivo. Cualquier tasa por período de esa corrida está
   inclinada justo donde no conviene.

Lo que sí queda en pie es todo lo que sale de `atributos.jsonl`, que no se tocó:
las Partes 2 y 3 y los puntos 1.3 a 1.5 de abajo. Los comandos de verificación
del final se corrieron y funcionan.

---

## Parte 1. Arreglos

### 1.1 La tabla de `KNOWN_ISSUES` §16 sigue con n=70

La tabla que contrasta el «Sentido de la sentencia» del portal contra el punto
resolutivo leído dice, para los «Sin Lugar», que 11% altera lo recurrido. Ese
número salió de 18 casos.

La conclusión de §16 no está en duda: en las dos corridas posteriores el
desacuerdo entre la etiqueta y el fallo resultó **mayor** que en el piloto, no
menor. El campo del portal no es la matriz de confirmación/revocación.

**Petición:** al cerrar la corrida con la regla corregida, actualizar la tabla
con el n final, y dejar dicho que el piloto de 70 daba otra cosa. No sustituir en
silencio: la distancia entre n=18 y n>1.000 es en sí misma un dato sobre cuánto
confiar en un piloto, y este proyecto vive de esa clase de anotación.

### 1.2 Publicar la tasa amplia y la estricta, no una sola

El lector del resolutivo cuenta como ALTERA cualquier modificación de lo
recurrido, aunque la apelación se rechace formalmente («sin lugar el recurso,
como consecuencia confirma con modificación»). El criterio está declarado en el
commit `5e752dc` y es defendible.

Pero pesa mucho: en la corrida de las 09:15, esa sola regla explicaba más de la
mitad de los «Sin Lugar» que alteraban, y moverla cambiaba la tasa por un factor
cercano a dos. No repito las cifras por lo dicho arriba; el punto es estructural
y no depende de ellas.

**Petición:** publicar las dos tasas, la amplia y la estricta, en vez de elegir
una. El punto resolutivo concreto ya se guarda en cada registro, así que el
recuento alternativo no cuesta ninguna petición a la fuente ni ningún token.

### 1.3 `fuente_efecto` dice «regla» también cuando ninguna regla disparó

`estudio_apelaciones.py` escribe `"fuente_efecto": "regla"` en todos los
registros, incluidos aquellos donde `regla` viene en `null` y el efecto es
`no_hallado` o `ambiguo`. En la corrida de las 09:15 eso ocurrió en 54 de 1.992.

Es una afirmación de procedencia que no se cumple, en un proyecto cuyo criterio
central es que cada valor diga de dónde salió. Además el docstring del módulo
anuncia «por regla cuando alcanza, con modelo cuando no», y la rama del modelo no
está implementada: `pendientes_modelo` se cuenta y no se usa.

**Petición:** que `fuente_efecto` valga `null` (o `sin_clasificar`) cuando no
disparó ninguna regla, y que el docstring diga lo que el código hace. Si la capa
de modelo se va a implementar, esos registros son exactamente su entrada.

### 1.4 Un falso positivo de búsqueda que conviene documentar como regla

Buscando casos de antejuicio en las 8.594 fichas de atributos, el término
`antejuicio` sobre el texto completo de la ficha devuelve **2.136 documentos**.
Es un número plausible, coherente en el tiempo y falso.

**2.036 de esos 2.136 son el nombre de un tribunal**, no un caso de antejuicio:

```
2036  Tribunal de amparo de primer grado -> "Corte Suprema de Justicia -Cámara de Amparo y Antejuicio"
 103  Por tipo de antecedente          -> "Penal -Diligencias de antejuicio"   <- estos sí
  80  Por tipo de acto reclamado       -> "Penal -Rechazo liminar de solicitud de antejuicio"
```

Los casos reales son **112** (uniendo los campos temáticos y quitando duplicados).

Es la misma familia de error que el repo ya cataloga: un resultado coherente que
describe otra cosa. Un cero invita a sospechar; un número razonable, no.

**Petición:** agregarlo a las reglas heredadas de `CLAUDE.md` con una formulación
propia del observatorio, del tipo:

> **Un término buscado sobre la ficha completa puede estar contándose desde el
> nombre de un órgano.** Antes de contar una materia, decir en qué campo vive.
> Los campos temáticos (`Por tipo de antecedente`, `Por tipo de acto reclamado`,
> `Tema`, `Materia`) describen el caso; `Tribunal de amparo de primer grado` y
> `Autoridad impugnada` describen quién lo vio, y llevan nombres de cámaras que
> contienen materias.

### 1.5 Dos números que conviene fijar en la documentación

Al recomputar la serie de «Con Lugar» me dio 40% para 2023 sobre todos los tipos
de expediente, y **51% restringiendo a `Apelación de Sentencia de Amparo`**, que
es la cifra del commit `c85d744`. Es correcta, pero la documentación no dice
sobre qué universo está calculada.

**Petición:** que toda cifra de la serie diga el tipo de expediente sobre el que
se calculó. Son variables distintas y se parecen demasiado.

---

## Parte 2. Peticiones de trabajo nuevo

Van en orden de utilidad, y las dos primeras son baratas.

### 2.1 Censo completo del subuniverso de antejuicio

**Qué:** todos los expedientes publicados cuya materia sea antejuicio, no una
muestra.

**Cuánto:** en la muestra estratificada hay 112. Ponderando por estrato,
**≈812 expedientes publicados entre 1996 y 2023**. Distribución por año, en la
muestra:

```
1999:1  2000:1  2002:5  2003:3  2004:4  2005:5  2006:3  2007:2  2008:4  2009:4
2010:6  2011:6  2012:3  2013:5  2014:6  2015:5  2016:5  2017:6  2018:6  2019:6
2020:7  2021:6  2022:7  2023:6
```

**Qué se sabe ya:** de los que traen el campo de sentido, **84 registrados «Sin
Lugar» contra 19 «Con Lugar»**. Con la advertencia de §16: eso es «proporción
registrada como Sin Lugar», no «proporción en que la CC dejó en pie la decisión
sobre el antejuicio». Para lo segundo hay que leer el resolutivo, que es
exactamente lo que ya sabe hacer la capa 3.

**Por qué importa:** el antejuicio es el mecanismo por el que un funcionario
electo queda o no expuesto a proceso penal. Un censo con denominador permite
preguntar si la CC trata distinto unos antejuicios que otros, y permite
descartarlo si no.

**Costo estimado:** ~812 documentos a 0,5 peticiones/segundo son unos 27 minutos
de red. La clasificación va 98% por regla; el 2% restante, a $0,0066 por
documento, no llega a un dólar.

### 2.2 Subuniverso de amparos promovidos por el Ministerio Público o una fiscalía

**Qué:** todas las resoluciones publicadas en que el postulante es el MP, una
fiscalía o la FECI.

**Cuánto:** 329 en la muestra de 8.594. Ponderado, **≈2.500 resoluciones
publicadas entre 1996 y 2023**. El 91% son de materia penal. Por año, en la
muestra:

```
1998:1  1999:1  2000:1  2001:1  2002:5  2003:12 2004:6  2005:6  2006:4  2007:5
2008:12 2009:25 2010:15 2011:14 2012:12 2013:13 2014:22 2015:22 2016:42 2017:31
2018:8  2019:10 2020:15 2021:23 2022:11 2023:12
```

Sentido registrado en la muestra: 194 «Sin Lugar», 123 «Con Lugar», 2
«Parcialmente con Lugar», 8 sin campo.

**Por qué importa:** es la línea base que permite responder si un magistrado o
una integración de la Corte resuelve distinto que sus pares cuando quien pide
amparo es la acusación. Sin ese denominador, una lista de resoluciones que
apuntan en una dirección solo confirma lo que ya pensaba quien la armó.

**Costo estimado:** ~2.500 documentos, unas 1,4 horas de red al ritmo declarado,
y menos de veinte dólares de modelo en el peor caso.

### 2.3 El voto por magistrado

Es la pieza que falta para que 2.2 sirva de verdad, y es la más cara.

**Lo que ya se puede:** los magistrados firmantes se extraen del pie de firmas,
con cotejo nombre por nombre (20/20 en el piloto).

**Lo que falta:** distinguir quién firma de quién vota en contra. Los votos
disidentes y razonados están en el cuerpo del documento, no en el resolutivo, así
que la estrategia de mandar solo la cola no alcanza aquí.

**Petición:** antes de gastar en esto, medir sobre 30 documentos qué proporción
de las resoluciones de la CC traen voto disidente identificable, y con qué
formulación lo introducen. Si la formulación es estable, es trabajo de regla y no
de modelo. Si no lo es, conviene saberlo antes y no después.

**Y hay un adelanto gratis.** El arreglo de `resolutivo.py` del 30 de agosto
detectó que los fallos con voto razonado traen texto después del punto
resolutivo, y que **son más frecuentes en años recientes**. Eso ya es media
medición: dice que el voto razonado existe con formulación reconocible y que su
frecuencia cambia en el tiempo. Conviene convertir ese hallazgo incidental en una
cifra explícita, porque una serie de «proporción de fallos con voto razonado por
año» es, por sí sola, un indicador de cohesión de la Corte, y no cuesta ninguna
petición nueva a la fuente.

### 2.4 Búsqueda por nombre de parte

La ficha del portal publica `Postulante`, `Tercero interesado` y `Autoridad
impugnada`. Con las 8.594 fichas ya recogidas se puede localizar a una persona
concreta en el corpus, y con el censo completo se podría a escala.

**Petición:** un comando que, dado un nombre, devuelva los expedientes donde esa
persona aparece como parte, **con el denominador al lado** (cuántas resoluciones
hay en ese mismo período y materia). El denominador no es un adorno: es lo que
impide que la respuesta se lea como una lista de cargos.

Y una cautela que el propio repo ya sabe: los nombres guatemaltecos producen
falsos positivos con facilidad, y la ficha da nombre completo pero no fecha de
nacimiento ni identificador. Cualquier coincidencia por nombre es un puntero a un
documento que hay que abrir, no una identificación.

---

## Parte 3. Cautelas que conviene no perder

Son del repo, no mías. Las repito porque cualquiera que use los números de arriba
las necesita en la misma página.

1. **El universo es lo publicado, no lo resuelto.** `2-2020` devuelve cero. La
   CC publica jurisprudencia seleccionada, y toda tasa calculada encima hereda
   esa selección.
2. **Antes de 2002 el campo de sentido casi no existe:** 4-18% de cobertura entre
   1996 y 2001, 58% en 2002, 95-100% desde 2003. Una serie que arranque antes de
   2002 mide cobertura del portal, no conducta de la Corte.
3. **Las estimaciones ponderadas de la Parte 2 son estimaciones.** Salen de una
   muestra estratificada por año con e=5% por estrato. El censo completo dará
   otro número, cercano pero no idéntico.
4. **El «Sentido de la sentencia» se refiere al amparo, no a la apelación.** Ver
   1.1 y 1.2.
5. **Una tasa por período leída con una regla que falla más en unos años que en
   otros no es una tasa, es la forma de la falla.** Es lo que pasó con la versión
   de `resolutivo.py` anterior al 30 de agosto: perdía documentos con voto
   razonado, que abundan en los años recientes. Cuando una regla no clasifica,
   conviene mirar **cómo se reparten los no clasificados en el tiempo** antes de
   publicar cualquier serie.

---

## Verificación

Todo lo anterior se recomputa desde el repo, sin red:

```bash
cd observatorio_justicia_gt

# 1.1 y 1.2 — contraste etiqueta / resolutivo, y reglas que lo empujan
# (correr al terminar la corrida en curso; con el archivo a medias da un parcial)
python3 - <<'PY'
import json, collections
rows=[json.loads(l) for l in open('data/processed/cc_ptmp/apelaciones.jsonl') if l.strip()]
rows=[r for r in rows if 'efecto' in r]
for et in ('con lugar','sin lugar'):
    g=[r for r in rows if (r.get('sentido_portal') or '').lower().startswith(et)]
    print(et, collections.Counter(r['efecto'] for r in g))
    print('  reglas que alteran:', collections.Counter(r['regla'] for r in g if r['efecto']=='altera').most_common())
PY

# 1.4 — en qué campo vive cada aparición de "antejuicio"
python3 - <<'PY'
import json, collections
c=collections.Counter()
for l in open('data/processed/cc_ptmp/atributos.jsonl'):
    if not l.strip(): continue
    for k,v in (json.loads(l).get('atributos') or {}).items():
        if 'antejuicio' in str(v).lower(): c[k]+=1
print(c.most_common())
PY

# 2.1 y 2.2 — tamaño ponderado de cada subuniverso
python3 - <<'PY'
import json, re
dis=json.load(open('data/manifests/cc_ptmp/diseno_muestral.json'))['estratos']
TEMA=('Por tipo de antecedente','Por tipo de acto reclamado','Tema','Tema abordado',
      'Tema subyacente (texto libre','Disposiciones impugnadas','Acto Reclamado')
aj=mp=0.0; naj=nmp=0
for l in open('data/processed/cc_ptmp/atributos.jsonl'):
    if not l.strip(): continue
    d=json.loads(l); a=d.get('atributos') or {}; y=d['estrato_anio']
    peso=dis[y]['N']/dis[y]['n']
    if 'antejuicio' in ' | '.join(str(a.get(k,'')) for k in TEMA).lower(): aj+=peso; naj+=1
    if re.search(r'ministerio p[uú]blico|fiscal[ií]a|feci', (a.get('Postulante') or '')+' '+(a.get('Solicitante') or ''), re.I): mp+=peso; nmp+=1
print(f'antejuicio: {naj} en muestra, ~{aj:.0f} en el universo')
print(f'MP/fiscalia: {nmp} en muestra, ~{mp:.0f} en el universo')
PY
```
