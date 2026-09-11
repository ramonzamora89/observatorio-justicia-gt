# Ficha de fuente — CIDEJ y la Unidad de Información Pública del OJ

**Consultado:** 2026-09-11
**Pregunta:** ¿es CIDEJ un destinatario viable para pedir datos de primera
instancia y Salas de Apelaciones? (Tarea 7; fases 3 y 4 de `PROJECT.md`.)

**Respuesta corta: CIDEJ no es el destinatario. La Unidad de Información Pública
del OJ sí lo es, y la ley le prohíbe expresamente devolver la solicitud por
incompetencia.**

## Lo que corrige de lo que este proyecto creía

`CLAUDE.md` arrastra, del trabajo de campo de agosto de 2026, que **«el Organismo
Judicial no tiene ventanilla que reciba una solicitud de información»**. Es
demasiado fuerte, y sostenerlo costó semanas.

El OJ **tiene** Unidad de Información Pública, con formulario web propio. El
formulario viejo —`ww2.oj.gob.gt/unip/sendMail.htm`— responde 200 y su único
contenido es un aviso de mudanza:

> «Este formulario se encuentra en la siguiente dirección:
> https://web.oj.gob.gt/formularioip/»

Lo que sí es cierto, y es otra cosa, es que **las dependencias se remiten unas a
otras**. Contra eso la ley tiene una norma específica, y no se estaba invocando.

## Estado de acceso verificado

| Recurso | Resultado |
|---|---|
| `ww2.oj.gob.gt/unip/sendMail.htm` | **200**, 1.076 b — aviso de traslado al formulario nuevo |
| `web.oj.gob.gt/formularioip/` | **403** a cliente automatizado |
| `web.oj.gob.gt/robots.txt` | **403** — no se pudo leer |
| `directorio.oj.gob.gt/` | **200**, 2.166 b |
| Manual de Procedimientos de CIDEJ (dos URL oficiales) | **403** en ambas |

**El 403 del formulario no significa que esté cerrado**: significa que rechaza a
un cliente no-navegador. **No se probó desde navegador y no se forzó**, conforme
a la regla de no evadir controles. Queda como **no comprobado**, no como cerrado.
Es un trámite que una persona hace en su navegador, y ahí es donde toca.

## Qué es CIDEJ, y por qué no se le escribe directamente

Centro de Información, Desarrollo y Estadística Judicial. Según fuentes públicas
del propio OJ: diseño, captura y difusión de la **estadística judicial**, y
desarrollo de los **sistemas de información** de los tribunales. Sede en el
Palacio de Justicia, 21 calle 7-70 zona 1, planta baja.

No es CENADOJ. Entre 2003 y 2014 absorbió la rama de Estadística.

**Su manual de atribuciones no se pudo descargar (403 en las dos URL oficiales),
así que sus atribuciones formales están sin verificar.** Lo anterior viene de
fuentes secundarias y del propio buscador, no del documento normativo.

Y precisamente por eso no se le escribe a CIDEJ: **escribirle a la dependencia
que uno cree competente es el error que produjo el peloteo de agosto.** La
solicitud va a la Unidad de Información Pública, que es quien está obligada a
recibirla, y se **nombra** a CIDEJ dentro como probable poseedor para que la
remisión interna sea trivial.

## El marco legal, verificado contra el texto de la ley

Decreto 57-2008, Ley de Acceso a la Información Pública. Texto extraído del PDF
oficial (22 páginas, 8.613 palabras, capa de texto limpia y verificada como prosa
antes de citar).

| Artículo | Qué dice, y para qué sirve aquí |
|---|---|
| **6, numeral 3** | Sujetos obligados: **«Organismo Judicial y todas las dependencias que lo integran»**. Nombrado expresamente. No hay discusión sobre si aplica |
| **19** | Cada sujeto obligado designa Unidad de Información, **con enlace en todas sus oficinas a nivel nacional** |
| **20, numeral 2** | La Unidad debe **orientar** al interesado en la formulación de la solicitud |
| **38** | **La norma decisiva.** Quien recibe **«no podrá alegar incompetencia o falta de autorización para recibirla, debiendo obligadamente, bajo su responsabilidad, remitirla inmediatamente a quien corresponda»** |
| **41** | Sólo tres requisitos: a quién se dirige, quién solicita, qué se pide. **«No podrá exigirse la manifestación de una razón o interés específico»** |
| **42** | Resolución en **diez días**, por escrito, en uno de cuatro sentidos —incluido «expresando la inexistencia» |
| **43** | Prórroga de hasta diez días más, avisando **dos días antes** del vencimiento |
| **44** | **Afirmativa ficta**: sin respuesta en plazo, queda obligado a entregarla en diez días más, sin costo. Su incumplimiento es **causal de responsabilidad penal** |
| **45** | Toda solicitud recibe **resolución por escrito**, fundada y motivada si niega o amplía |
| **54** | Recurso de revisión ante la máxima autoridad, **quince días** desde la notificación |
| **55, numerales 3-5** | El recurso procede también por información **incompleta**, por **falta de respuesta** y por **vencimiento del plazo** |

## La restricción que manda sobre cómo se redacta la petición

**Artículo 45, párrafo tercero:**

> «La información se proporcionará **en el estado en que se encuentre** en
> posesión de los sujetos obligados. La obligación **no comprenderá el
> procesamiento** de la misma, ni el presentarla conforme al interés del
> solicitante.»

Esto es una negativa legítima esperando a que la pidamos mal. **Pedir una tasa,
un indicador o un cruce es pedir procesamiento, y se puede rechazar con la ley en
la mano.** Hay que pedir **lo que ya existe**: bases, exportaciones, reportes
generados, catálogos de campos. El procesamiento lo hace este proyecto, que para
eso está.

De paso: es la misma disciplina que el proyecto ya se impone hacia dentro. El
denominador se construye aquí, no se le encarga a la fuente.

## Estrategia, y por qué el primer pedido es el catálogo

El pedido 1 de la solicitud no pide datos: pide **qué datos existen** —sistemas,
qué registra cada uno, qué campos, qué período, en qué formato—. Es barato de
responder, no admite la objeción del artículo 45 porque no pide procesar nada, y
convierte los pedidos siguientes en específicos en vez de especulativos.

Pedir bien la segunda vez depende de saber qué hay. Hoy no se sabe.

Se incluye además el **Manual de Procedimientos de CIDEJ**, que es público y que
este proyecto no pudo descargar por el 403. Es de entrega trivial y **sirve de
prueba del canal**: si ni eso llega, el problema no es el alcance de lo pedido.

## Qué hacer con la respuesta

- **Guardar el acuse.** Sin acuse no corre plazo, y es lo que faltó en agosto.
- **Contar diez días hábiles** desde la presentación. Anotar la fecha.
- Si avisan prórroga, debe llegar **dos días antes** del vencimiento (art. 43).
- Si no hay respuesta: opera la **afirmativa ficta** del art. 44, y procede
  recurso de revisión por los numerales 4 y 5 del art. 55.
- Si responden «no nos corresponde»: **el artículo 38 lo prohíbe**. Eso no es una
  respuesta, es una infracción, y se recurre.
- Si entregan parcialmente: el numeral 3 del art. 55 cubre la información
  incompleta.

## Lo que esta ficha NO establece

- **Las atribuciones formales de CIDEJ.** El manual dio 403. Sin verificar.
- **Si el formulario web funciona.** No se probó desde navegador.
- **Si CIDEJ posee efectivamente resoluciones**, o sólo estadística agregada. Es
  justamente lo que pregunta el pedido 1.
- **Nada sobre plazos reales de respuesta del OJ.** No hay antecedente propio.
