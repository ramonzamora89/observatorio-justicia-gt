# Tareas pendientes

Actualizado: **2026-09-11**. En orden de prioridad.

*Revisión hecha midiendo el estado del repositorio, no releyendo la lista
anterior. Las cifras de la versión del 30 de agosto habían quedado obsoletas por
el commit de esa misma tarde: decía 44,8% contra 28,1%, y hoy es **35,1% contra
28,1%** sobre n=1.858.*

---

## 1. Terminar la validación del clasificador · **12 de 100, y ya pagó sola**

`data/manifests/cc_ptmp/validacion_resolutivo.csv` — 100 filas, **12 hechas**.

**Es la tarea con mejor rendimiento demostrado del proyecto.** En la fila doce de
cien, el revisor humano encontró que la regla contaba como alteración fallos
cuya única modificación era el plazo de pago de una multa al abogado
patrocinante. **181 documentos pasaron de «altera» a «mantiene», el 22% de todas
las alteraciones**, y la serie cambió de forma: donde había una U hay un
crecimiento sostenido.

Doce filas. Quedan ochenta y ocho.

```bash
uv run obsgt cc-ptmp validar --puntuar
```

**Lo medido hasta hoy:** las 12 dan veredicto comparable y **las doce
concuerdan** con el clasificador vigente. Decía «diez de diez» porque 17 filas
puntuaban contra la versión anterior del clasificador; ver tarea 4.

Y hay que decir lo que ese número **no** es: un 100% sobre doce tiene el límite
inferior del IC en **75,7%**, o sea que **no distingue un clasificador del 97% de
uno del 80%**, y `PRD-1.md` §16 exige más del 95%. Con 30 o 40 sí se distingue.
El comando ya lo dice solo: responde `SIN EVIDENCIA SUFICIENTE`, no `CUMPLE`.

**Dos cautelas para las que faltan:**

- ~~**Sesgo de orden.**~~ **Comprobado el 11-09-2026: el archivo ya está
  aleatorizado** —año medio 2015,1 en las 12 revisadas contra 2015,0 en las 88
  restantes, y estratos en proporción—. Se puede seguir en orden.
- **Lo valioso no es el acuerdo, es el desacuerdo.** Diez filas coincidieron y no
  enseñaron nada; las dos que costaron decidirse corrigieron el 22% del resultado
  principal. Que hoy las doce concuerden no cambia eso: concuerdan **porque** esas
  dos se leyeron despacio y movieron el criterio. Cuando una fila cueste
  decidirla, esa es la fila que hay que anotar con calma.

---

## 2. Escribir el criterio del accesorio en `PRD-1.md` · **media hora**

**El criterio metodológico central del proyecto no está en la especificación.**

Vive en un comentario de `src/observatorio_gt/resolutivo.py` y en el mensaje de
un commit:

```python
_SOLO_ACCESORIO = multa|costas|cobro|plazo|pago|abogado (patrocinante|auxiliante)|
                  tesoreria|honorarios|apercibimiento
_TOCA_EL_FONDO  = ampar|proteccion|acto reclamado|autoridad|derecho|pena|prision|
                  restituy|deja sin efecto|suspende|otorga|deniega
```

Una «confirmación con modificación» que sólo toca lo primero **mantiene** lo
recurrido; si toca lo segundo, **altera**.

Eso decide el 22% de las alteraciones y `PRD-1.md` no lo menciona. Un lector
externo no puede auditar la cifra principal sin leer el código, y eso contradice
el principio de que cada valor diga de dónde salió.

**Hay que escribir además su fundamento**, que es la regla heredada: *«amended»
no quiere decir que cambió el fondo*. Y las dos listas de términos, porque son
una decisión sustantiva disfrazada de expresión regular.

---

## 3. Elegir amplia o estricta para el titular · **decisión jurídica, no trabajo**

Sigue abierta, pero es una pregunta más chica que en agosto: el caso del
accesorio ya se resolvió y salió del medio. Lo que queda son las **129
resoluciones** que siguen clasificadas como «confirma con modificación» sin que
la modificación sea accesoria.

Cifras vigentes (`obsgt cc-ptmp tasas`), universo **Apelación de Sentencia de
Amparo**:

| Periodo | n | Amplia | Estricta |
|---|---|---|---|
| 2003-2010 | 437 | 29,3% | 26,5% |
| 2011-2015 | 456 | 32,9% | 26,1% |
| 2016-2019 | 468 | 33,5% | 23,7% |
| 2020-2023 | 497 | **43,7%** | **35,6%** |
| **Total** | **1.858** | **35,1%** | **28,1%** |

Las dos series se publican hoy. Elegir una para el titular es jurídico.

**Y nótese que la dirección no depende de la elección:** las dos suben en el
último período, y en las dos el intervalo de confianza de 2020-2023 no se solapa
con el de 2016-2019. **Esa parte del hallazgo es robusta al criterio**, y
conviene decirlo así en vez de esperar a la decisión para publicar nada.

---

## 4. ~~Devolver el CSV de validación a UTF-8~~ · **hecho el 11-09-2026**

Hecho, pero **el diagnóstico que traía esta lista era falso y su receta habría
roto el archivo**. Queda escrito porque el error es reutilizable.

Decía que el archivo volvía «en cp1252» y que había que convertirlo entero.
Medido: el archivo era **UTF-8 válido salvo tres bytes**, los tres MacRoman
—`ó`, `á`, `ó`— tecleados por el revisor. Convertirlo entero a cp1252 habría
arreglado esos tres y **roto los 57 guiones** que ya estaban bien.

De dónde salió el diagnóstico: `leer_texto()` tanteaba codificaciones por
excepción, y **cp1252 no falla casi nunca**, así que ganaba siempre. Leer el
archivo con ella devolvía «modificaci—n», y ese síntoma —producido por el propio
lector— se anotó como si fuera el estado del archivo.

Lo hecho:

- los tres bytes parcheados; la ficha es UTF-8 estricto y los 57 guiones siguen;
- `leer_texto()` repara **byte a byte**: lo válido en UTF-8 se respeta y sólo lo
  que falla se traduce, eligiendo codificación **por el resultado** —gana la que
  produce una letra castellana— y no por orden de la lista;
- columna `VEREDICTO_CONTROLADO_altera_mantiene_no_aplica` junto a la prosa; el
  token manda, la prosa es el respaldo y se conserva;
- `COMO_VALIDAR_EL_RESOLUTIVO.md` reescrito, con el «CSV UTF-8» primero;
- 7 tests nuevos; la suite pasa entera.

### Y de paso: 17 filas puntuaban contra un clasificador que ya no existe

Hallazgo no previsto, y el que más importaba. La ficha se escribió el 30 de
agosto a las **16:18**; `apelaciones.jsonl` se regeneró a las **16:26**, ya con
el criterio del accesorio. **17 de las 100 filas** se quedaron con el
`veredicto_maquina` viejo, las 17 en la misma dirección `altera → mantiene`.

Consecuencia: `validar --puntuar` daba **88,9%** y dos fallos en el estrato de la
regla discutida. Los dos «fallos» eran filas donde el clasificador de hoy
**coincide** con el revisor. Refrescada la columna contra la fuente, es
**12 de 12**. El valor viejo se conserva en `veredicto_maquina_previo_2026-08-30`
y hay un test que falla si la ficha vuelve a quedarse atrás.

Esto también corrige lo que decía esta lista: no era «diez comparables que
concuerdan y dos que no dan veredicto». Son **doce comparables y doce
concuerdan**.

### Y el comando decía CUMPLE cuando no puede saberlo

Con el 100% recién salido, `validar --puntuar` respondía que se cumple el >95%
de `PRD-1.md` §16. Lo dictaba sobre el punto, ignorando que el **IC 95% baja a
75,7%** con n=12: compatible con un clasificador del 80%. Ahora el veredicto se
dicta sobre el intervalo y responde `SIN EVIDENCIA SUFICIENTE` hasta que el
intervalo entero pase el umbral.

**Siguiente:** las filas 7 y 10 esperan token —son las del accesorio, tienen
prosa y no veredicto— y quedan 88 por revisar.

---

## 5. Cerrar la ventana hasta 2026 · **2024 está, 2025 y 2026 no**

La lista anterior daba esto por pendiente entero. Está a medias:

```
2024:  243 fichas
2025:   16 fichas      <- prácticamente ausente
2026:    1 ficha       <- prácticamente ausente
```

Contra las 250-400 anuales de los años normales, 2025 y 2026 no están cubiertos,
y es el único tramo que solapa con los hechos que hoy son noticia.

```bash
uv run obsgt cc-ptmp muestra --desde 2025 --hasta 2026
uv run obsgt cc-ptmp atributos
```

Antes de graficar ese tramo, la cautela 2 de la auditoría: **un año reciente
puede estar incompleto porque la CC aún no ha publicado**, no porque haya
resuelto menos. Son cosas distintas y se parecen en el eje Y.

---

## 6. Censo completo del subuniverso de antejuicio · **lo más barato que queda**

Petición 2.1 de la auditoría, que la lista anterior no recogía.

**Qué:** todos los expedientes publicados cuya materia sea antejuicio, no una
muestra. **≈812 expedientes**, unos **27 minutos de red y menos de un dólar**.

Lo que ya se ve en la muestra:

| Acto reclamado | n |
|---|---|
| Declaratoria con lugar de diligencias de antejuicio | 25 |
| **Rechazo liminar de solicitud de antejuicio** | **22** |
| Declaratoria sin lugar de diligencias de antejuicio | 18 |
| Admisión a trámite de diligencias de antejuicio | 8 |
| Remisión de expediente al Congreso | 6 |
| Remisión a Salas de Apelaciones | 1 |

De las 22 de rechazo liminar, el sentido **registrado** es 20 «Sin Lugar» contra
2 «Con Lugar».

**Y aquí la advertencia de `KNOWN_ISSUES` §16 no es formalismo:** eso es
«proporción registrada como Sin Lugar», no «proporción en que la Corte dejó en
pie la decisión sobre el antejuicio». Para lo segundo hay que leer el resolutivo,
que es lo que hace la capa 3 y lo que la tarea 1 está validando. **Hacer el censo
sin leer el resolutivo produce un número que se va a citar mal**, y este es un
subuniverso donde citar mal tiene consecuencias.

### Decidido el 11-09-2026

**Composición real del subuniverso** (muestra n=112), que esta tarea no tenía
medida y que cambia el diseño:

| Tipo de expediente | n | % |
|---|---|---|
| **Amparo en Única Instancia** | 80 | **71,4%** |
| Apelación de Sentencia de Amparo | 30 | 26,8% |
| Inconstitucionalidad de Carácter General | 2 | 1,8% |

**La tarea 1 no desbloquea esto.** La validación se sortea sobre
`apelaciones.jsonl`, universo *Apelación de Sentencia de Amparo*: terminarla
valida el clasificador para el 26,8% y **no dice nada del 71,4%**. Y en ese 71,4%
la pregunta ni siquiera aplica —en un amparo en única instancia no hay decisión
inferior que confirmar o alterar—. De los 112 casos, sólo **27 (24%)** producen
hoy un veredicto altera/mantiene.

**Decisión 1 — dos indicadores, declarados por separado y nunca sumados:**

- **Amparo en única instancia** → `Sentido de la sentencia` (otorga/deniega).
  `KNOWN_ISSUES` §16 descarta ese campo **para apelaciones**, porque se refiere al
  amparo y no a lo recurrido. Pero en única instancia **el amparo es la
  decisión**, así que ahí §16 no aplica y el campo es el correcto. Hay que
  normalizarlo: viene con motivo pegado —«Sin Lugar -Ausencia de agravio»— y
  **16,1% vacío**.
- **Apelación de sentencia de amparo** → capa 3, la que valida la tarea 1.

**Decisión 2 — recolectar la metadata ya**, sin esperar al indicador. Sirve para
cualquier diseño, y convierte el **812 —hoy estimación ponderada desde muestra,
no conteo—** en un número real.

Y de paso recomputa `antejuicio.json`, que es de las **14:29** del 30 de agosto,
anterior al criterio del accesorio de las 16:26. Sólo **11 de sus 112 casos**
cruzan con `apelaciones.jsonl` y ninguno de esos 11 difiere; **los otros 101 no
están comprobados** —que no es lo mismo que estar bien—.

### Por qué sube de prioridad, y bajo qué condiciones

Existe una investigación periodística externa que quiere exactamente este
indicador. **Eso no es razón para priorizarlo**, y el proyecto tiene una regla
explícita: un observatorio construido dentro de la investigación que quiere una
respuesta produce números sospechosos aunque el código sea impecable.

Lo que sí lo justifica es que **la petición 2.1 ya estaba primera en una auditoría
externa fechada antes de que llegara esa demanda**, por sus propios méritos.

**Dos condiciones que hay que sostener:** el indicador se calcula para todo el
subuniverso, no para los expedientes de interés de nadie; y se publica **aunque
desmienta** lo que esa investigación espera encontrar.

---

## 7. ~~Probar CIDEJ~~ · **solicitud redactada el 11-09-2026, falta enviarla**

Ver `sources/oj/FICHA_CIDEJ.md` y `sources/oj/solicitud_uip_oj_2026-09-11.md`.

**El destinatario no era CIDEJ.** Escribirle a la dependencia que uno cree
competente es lo que produjo el peloteo de agosto. La solicitud va a la **Unidad
de Información Pública del OJ**, y nombra a CIDEJ dentro para que la remisión
interna sea trivial.

**Y corrige una regla heredada de `CLAUDE.md`:** decía que «el Organismo Judicial
no tiene ventanilla que reciba una solicitud de información». El OJ **sí tiene**
Unidad de Información Pública, con formulario en `web.oj.gob.gt/formularioip/`.
Lo que es cierto es otra cosa: que las dependencias se remiten unas a otras. Y
contra eso la ley tiene una norma que no se estaba invocando —**artículo 38 del
Decreto 57-2008**: quien recibe «no podrá alegar incompetencia (…) debiendo
obligadamente (…) remitirla inmediatamente a quien corresponda»—.

El artículo que manda sobre la redacción es el **45**: la información se entrega
«en el estado en que se encuentre» y la obligación «no comprenderá el
procesamiento». **Pedir una tasa o un cruce es pedir procesamiento y se rechaza
con la ley en la mano.** Por eso el pedido 1 no pide datos: pide el **catálogo de
qué datos existen**, que es barato de responder y convierte la segunda solicitud
en específica.

**Lo que falta, y es de Moncho:** rellenar los corchetes y enviarla. El
formulario da **403 a cliente automatizado** y no se forzó —queda *no
comprobado*, no cerrado—; es un trámite de navegador. **Guardar el acuse: sin
acuse no corre plazo, y es lo que faltó en agosto.**

Plazos que empiezan a correr: **10 días** (art. 42), prórroga avisada 2 días
antes (art. 43), **afirmativa ficta** (art. 44), recurso a los **15 días**
(art. 54).

---

## 8. Subuniverso del Ministerio Público · ~2.500 documentos, ~1,4 h

Petición 2.2. Es la línea base para preguntar si la Corte resuelve distinto
cuando quien pide amparo es la acusación.

### Decidido el 11-09-2026

**Composición**, contando por el campo `Postulante` sobre las 8.594 fichas de
atributos: **324 fichas**, repartidas en

| Tipo de expediente | n | % |
|---|---|---|
| Apelación de Sentencia de Amparo | 182 | 56,2% |
| Amparo en Única Instancia | 140 | 43,2% |
| Inconstitucionalidad de ley en Caso Concreto | 2 | 0,6% |

Misma forma que el antejuicio y menos grave: aquí la tarea 1 cubre la mayoría,
pero el 43,2% necesita igualmente el indicador de única instancia. **Se aplica la
misma decisión de dos indicadores declarados por separado.**

**Decisión 1 — familia normalizada y auditada.** El campo viene sin normalizar:

```
197  Ministerio Público
 25  Ministerio Público, por medio de la Unidad de Impugnaciones
 10  Fiscal General de la República y Jefe del Ministerio Público
  5  Ministerio Publico                     <- sin tilde
  5  Ministerio Público, por medio de la Unidad de Impugnaciones,
  5  Ministerio Público, Unidad de Impugnaciones
  4  Ministerio Público por medio de la Unidad de Impugnaciones
  4  Ministerio Público, por medio de la Fiscalía de Ejecución
  3  Unidad de Impugnaciones del Ministerio Público
  2  Fiscalía de Ejecución del Ministerio Público
```

Se agrupan todas, incluidas Unidad de Impugnaciones, Fiscalía de Ejecución y
Fiscal General: son el MP actuando. **El listado completo de variantes agrupadas
se publica junto al dato**, para que la agrupación sea auditable. Es agrupación
por criterio explícito, no filtro por subcadena a ciegas —que es lo que está
prohibido en la lista del final—.

**Decisión 2 — comparar contra el resto de postulantes, emparejando por materia y
período.** Sin emparejar, si el MP litiga sobre todo en penal y el universo es
mayoritariamente otra cosa, lo que se mida será composición y no trato. El
universo comparable se calcula para toda la judicatura, no sólo para el sujeto de
interés: pedirlo sólo para quien interesa mete el sesgo en la pregunta.

**Pendiente de medir:** el sentido registrado en la muestra que citaba esta lista
—194 «Sin Lugar», 123 «Con Lugar», 2 «Parcialmente», 8 sin campo— **no se ha
recomputado** y sale del mismo campo que `KNOWN_ISSUES` §16 desaconseja para
apelaciones. No usarlo hasta separarlo por tipo de expediente.

---

## 9. Voto razonado · **RETRACTADO — no rehacer la serie**

*Reescrita el 11-09-2026. La versión anterior de esta tarea pedía justamente lo
que el proyecto ya había retirado.*

**Lo que decía esta tarea:** que el arreglo de `resolutivo.py` detectó que los
fallos con voto razonado traen texto después del punto resolutivo y son más
frecuentes en años recientes, y que convertir eso en una serie explícita era
«por sí solo, un indicador de cohesión de la Corte». Lo llamaba *adelanto
gratis*.

**Lo que dicen `KNOWN_ISSUES` §18 y la cabecera de `src/observatorio_gt/voto.py`:**

> «**Conclusión: la serie mide cómo la Corte anota sus sentencias, no cuánto
> disiente.** No debe publicarse como indicador de cohesión.»

La observación era correcta y la explicación falsa. **Lo que sigue al resolutivo
en documentos recientes es la firma electrónica** —«Firmado digitalmente por X,
Razón: Aprobado»—, encabezados repetidos y bloques de firmas más largos. Y de los
21 documentos marcados, **sólo 2 traen el texto del voto**; los otros 19 llevan
una anotación junto al nombre del magistrado y nada más.

La anotación desaparece después de 2010, pero **el formato del documento también
cambió**: los paréntesis en el bloque de firmas pasaron de 45 a 232 documentos,
sólo que ahora anotan montos de multa. No se puede distinguir desde aquí «dejó de
haber disidencias» de «dejó de anotarse».

**Cómo llegó a estar escrita como tarea pendiente:** la retractación y esta lista
se escribieron el mismo día. La lista recogió el hallazgo incidental y no la
corrección. Es el mismo error que el diagnóstico de cp1252 de la tarea 4, con más
consecuencias: aquí lo que estaba en riesgo era **republicar algo ya retirado**.

### Lo único que queda vivo, y no es esto

`KNOWN_ISSUES` §18 cierra las dos vías que se probaron: la Gaceta Jurisprudencial
**no sirve** —comprobado el 30-08-2026: son fichas por expediente, sin bloque de
firmas; «disidente» y «razonado» aparecen **cero** veces en 345 páginas con el
texto extraído limpio— y la detección por texto mide formato.

Queda **pedirle la serie a la CC**, y ahora hay con qué. La Corte de
Constitucionalidad es sujeto obligado por el **artículo 6 numeral 5** del Decreto
57-2008, y la solicitud del OJ preparada en la tarea 7 sirve de plantilla:
`sources/oj/solicitud_uip_oj_2026-09-11.md`.

Redactarla con la misma disciplina del artículo 45 —**en el estado en que se
encuentre, sin pedir procesamiento**—: no pedir «proporción de fallos con voto
razonado», que es un cálculo y se rechaza, sino **el registro de votos razonados
y disidentes por magistrado y expediente**, tal como la CC lo lleve.

**Si no se puede medir, no se publica.** Que la pregunta sea interesante no la
convierte en medible.

---

## 10. Vinculación entre instancias (MVP-3) · **confirmado sin empezar**

`appeal_links: 0`. También `citations: 0` y `judicial_officers: 0`.

La CC identifica al órgano inferior y la fecha de la sentencia recurrida; con eso
se puede empezar a reconstruir el ciclo procesal, aunque solo hacia arriba.

`PIPELINE.md` §7 fija la prioridad de señales y prohíbe aceptar vínculos débiles.
Y `KNOWN_ISSUES` §4 avisa de algo que esta capa necesita saber: **el mismo
expediente se escribe `61-1998` en la API y `61-98` en el portal y el PDF**, sólo
en los anteriores al 2000. El collector no los unifica a propósito.

---

## 11. Búsqueda por nombre de parte · petición 2.4

Un comando que, dado un nombre, devuelva los expedientes donde esa persona
aparece como parte, **con el denominador al lado**: cuántas resoluciones hay en
ese mismo período y materia.

El denominador no es un adorno. Es lo que impide que la respuesta se lea como una
lista de cargos.

Y la cautela que el repo ya sabe: los nombres guatemaltecos producen falsos
positivos con facilidad, y la ficha da nombre completo pero **ni fecha de
nacimiento ni identificador**. Cualquier coincidencia por nombre es un puntero a
un documento que hay que abrir, no una identificación.

---

## 12. Dos insumos y una pregunta, recibidos el 02-10-2026 · **sin empezar**

Vienen de la misma investigación externa que menciona la tarea 6, y valen las
mismas dos condiciones: se calcula para todo el universo y se publica aunque
desmienta a quien lo pidió. **No se recibe ninguna hipótesis, solo fuentes.**

**Insumo para la tarea 6 (y la 10, vinculación entre instancias).** El OJ
publica una consulta de antejuicios
(`consultasexternas.oj.gob.gt/consultasExternas/Antejuicios`). La pestaña
«Búsqueda por Fechas», con competencia y fase obligatorias, devuelve el
historial completo de cada fase sin importar el rango de fechas: año, número,
fecha de admisión, nombres, competencia y fase. **No da el cargo ni la fecha de
resolución.** El 02-10-2026 la Corte Suprema tenía 906 expedientes en 12 fases
(desde fines de 2016). Existe una copia cruda de esas tablas: diez TSV, uno
por fase, con `SHA256SUMS` y un encabezado de URL, parámetros y hora (ruta en
`CONTEXTO_LOCAL.md`, que no se versiona). **Úsese solo la copia cruda, nunca
los archivos derivados que la acompañan**, que traen una clasificación propia
de la investigación. Defectos conocidos: un expediente puede aparecer en
varias fases (19 de 906), y la fase registrada contradice a la prensa en varios
casos. La pregunta es si el número CSJ (año-número) permite enlazar con el acto
reclamado de las fichas de la CC.

**Insumo para la tarea 5.** La consulta del OJ responde desde fuera de
Guatemala por VPN (salida Proton «Guatemala», 02-10-2026). Sigue sin
aclararse si el bloqueo anterior era geográfico.

**Pregunta nueva: el amparo que detiene un proceso.** ¿Con qué frecuencia la CC
otorga amparo **provisional**, y luego definitivo, en asuntos de elección de
segundo grado (comisiones de postulación, elección de magistrados, de contralor
y de fiscal general) frente al resto de su materia? La pregunta nace de la
observación de que el amparo se usa para frenar o mover procesos. **Esa
observación no está medida, y por eso es una pregunta y no una hipótesis.**
Antes de diseñar nada: ¿el amparo provisional queda registrado en lo que publica
la CC, o solo la sentencia?

## Cosas que NO hay que volver a intentar

- **Buscar en el endpoint de texto libre para contar.** No hace búsqueda de
  frase: «voto razonado disidente» devuelve 47.720 de 66.025 y «antejuicio»
  27.897. Cualquier conteo suyo es ruido.
- **La Gaceta Jurisprudencial para medir votos razonados.** Comprobado: son
  fichas por expediente, sin firmas ni votos. Cero menciones en 345 páginas.
- **El portal del OJ por vía automatizada.** Requiere credencial de abogado y
  notario, y hay desafío anti-bot. No se evade.
- **Publicar una serie temporal sin preguntar qué cambió en el documento.** Van
  tres veces que el patrón era de la fuente, no de la Corte.
- **Filtrar un campo por subcadena.** *Añadido el 02-09-2026.* Contar
  `'rechazo liminar' in valor` sobre `Por tipo de acto reclamado` devuelve **617
  fichas**; sólo **22** son de antejuicio. Las otras 595 son rechazos liminares
  de casación (236), nulidad civil (59), revocatoria administrativa (56) y
  reposición penal (33). Es la regla del nombre de órgano con otra cara: allí la
  trampa estaba en el campo equivocado, aquí en el **valor incompleto**.
  **Comparar contra el valor completo del campo, siempre.**
- **Recoger en esta lista un hallazgo sin comprobar si fue retractado.**
  *Añadido el 11-09-2026.* La tarea 9 pedía publicar la serie de voto razonado
  como indicador de cohesión **el mismo día** en que `KNOWN_ISSUES` §18 la
  retractaba por medir formato del documento. La lista recogió el hallazgo
  incidental y no la corrección, y ahí se quedó nueve días. **Antes de escribir
  una tarea que publique algo, comprobar que `KNOWN_ISSUES` no lo haya retirado.**
  Una lista de tareas es documentación, y la documentación se desincroniza.
- **Tantear codificaciones por excepción.** *Añadido el 11-09-2026.* `cp1252` y
  `latin-1` decodifican casi cualquier byte **sin lanzar error**, así que un bucle
  `for cod in (...): try: decode` devuelve siempre la primera de la lista y la
  corrupción no se nota. Así se diagnosticó como cp1252 una ficha que era UTF-8
  con tres bytes MacRoman. **Elegir la codificación por el resultado** —en
  castellano, la que produce vocales acentuadas— y reparar sólo los bytes que
  fallan, nunca el archivo entero.
- **Puntuar contra una columna de veredicto congelada.** *Añadido el 11-09-2026.*
  La ficha de validación guarda lo que dijo el clasificador **el día que se
  generó**. Si el clasificador cambia después, la revisión humana se compara
  contra una versión que ya no existe y los desacuerdos son fantasmas: 17 de 100
  filas, y un 88,9% donde había un 100%. **Refrescar contra la fuente antes de
  puntuar**, conservando el valor viejo.
- **Citar una cifra de `TAREAS.md` sin recomputarla.** *Añadido el 02-09-2026.*
  Esta lista llevaba desde el 30 de agosto diciendo «44,8% contra 28,1%» cuando
  el commit de esa misma tarde la había dejado en **35,1% contra 28,1%**. Una
  lista de tareas es documentación, no fuente: **el número vive en
  `obsgt cc-ptmp tasas` y en `matriz_apelaciones.json`.**

---

## Cerrado desde la revisión del 30 de agosto

*Va al final a propósito: `scripts/tareas_prioritarias.py` emite los primeros
bloques `##` al arrancar la sesión, y lo cerrado no es una tarea.*

La **Parte 1 de la auditoría externa está completa**, y la lista anterior no lo
registraba:

| Petición | Estado |
|---|---|
| **1.1** `KNOWN_ISSUES` §16 con n=70 | **Hecho.** Ahora contrasta 1.686 apelaciones |
| **1.2** Publicar tasa amplia y estricta | **Hecho.** `obsgt cc-ptmp tasas` publica las dos, con IC 95% |
| **1.3** `fuente_efecto` mentía sobre su procedencia | **Hecho.** Escribe `None` cuando no disparó regla (1.986 con regla, 14 sin ella), y el docstring ya dice que la capa de modelo no está implementada |
| **1.4** Documentar el falso positivo de búsqueda | **Hecho.** Es la regla «Un término buscado puede estar contándose desde el nombre de un órgano» de `CLAUDE.md` |
| **1.5** Que toda cifra diga su universo | **A medias.** `matriz_apelaciones.json` y `obsgt cc-ptmp tasas` sí encabezan con el universo; `KNOWN_ISSUES` §17 dice «2.000 apelaciones» sin nombrar el tipo de expediente. Arreglo de una línea |

Y el hallazgo del criterio del accesorio, con sus dos arreglos derivados: el
puntuador que exigía el token exacto contra un revisor que escribe en prosa
—daba 0% de exactitud sobre doce revisiones que coincidían todas— y la detección
del cp1252, que sigue pendiente de arreglar y es la tarea 4.
