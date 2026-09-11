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

Petición 2.2. 329 en la muestra actual. Es la línea base para preguntar si la
Corte resuelve distinto cuando quien pide amparo es la acusación.

Sentido registrado en la muestra: 194 «Sin Lugar», 123 «Con Lugar», 2
«Parcialmente con Lugar», 8 sin campo.

---

## 9. Proporción de fallos con voto razonado por año · **adelanto gratis**

Media petición 2.3, y no cuesta ninguna consulta nueva a la fuente.

El arreglo de `resolutivo.py` del 30 de agosto detectó de paso que los fallos con
voto razonado traen texto después del punto resolutivo, y que **son más
frecuentes en años recientes**. Convertir ese hallazgo incidental en una serie
explícita es, por sí solo, un indicador de cohesión de la Corte.

**Antes de gastar en la parte cara** —distinguir quién firma de quién disiente—
medir sobre 30 documentos qué proporción trae voto disidente identificable y con
qué formulación lo introduce. Si la formulación es estable es trabajo de regla; si
no, conviene saberlo antes y no después.

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
