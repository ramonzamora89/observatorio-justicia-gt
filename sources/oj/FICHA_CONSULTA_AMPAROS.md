# Ficha de fuente — Consulta de amparos de la Cámara de Amparo y Antejuicio (CSJ)

**Consultado:** 2026-10-08, a mano, desde Chrome (operado con Claude in Chrome).
CAPTCHA marcado por Moncho en cada consulta. **Todas las consultas con VPN
encendida**; salida Proton «Guatemala» (ver la decisión sobre VPN en la
tarea 12 de `TAREAS.md`). Sin probar sin VPN: no se sabe si hace falta.
**Pregunta:** ¿qué dice el OJ, en público, de los amparos que conoce la Corte
Suprema?

**Respuesta corta: la ficha de cada amparo trae fecha de admisión y actuaciones
fechadas, lo que permite medir duración. Pero cada consulta exige CAPTCHA y
conocer el número o el nombre exacto: sirve para verificar casos y armar
muestras pequeñas, no para un censo.**

Alcance: amparos que tramita la **CSJ** (Cámara de Amparo y Antejuicio). No los
de la CC. Las sentencias de la CSJ apeladas pasan a la CC, así que la ficha es
un puente para la vinculación entre instancias (tarea 10).

## Dos versiones del mismo sistema

| | `ww2.oj.gob.gt/consultamparos/` (y `/consultamparista/`) | `consultasexternas.oj.gob.gt/consultasExternas/Amparos` |
|---|---|---|
| CAPTCHA | imagen con texto | reCAPTCHA de casilla |
| Búsquedas | número de amparo (año + número); amparista; expediente judicial de 2.ª instancia | por expediente (año + número); por nombre del amparista + rango de fechas |
| Fecha de admisión | día | día y **hora** |
| Campo «Otorgado o denegado provisionalmente» | **sí** | **no aparece** |
| Actuaciones fechadas | sí | sí, las mismas |
| Texto de resoluciones | no | no |

El portal `consultasExternas` es el que el propio OJ dio como enlace en una
respuesta de acceso a la información. Su raíz lista otras consultas: agenda de
audiencias, RECEDE, antejuicios, verificador de documentos, pensión
alimenticia, prestación laboral y notificaciones por estrado.

## Campos de la ficha

Año · número · oficial · fecha de admisión · autoridad impugnada · amparista ·
acto reclamado · terceros interesados · actuaciones con fecha · (solo `ww2`)
otorgado o denegado provisionalmente.

## Caso de verificación: amparo 2297-2023

Elegido porque su número y su desenlace se conocen por prensa. Las dos versiones
devolvieron la misma ficha:

- admitido el **14-07-2023** (08:36:29);
- amparista: un partido político, «por medio de» su secretario general;
- 8 actuaciones, la última «se entregó al notificador para notificar
  sentencia» el **18-08-2023**: **35 días** desde la admisión hasta ahí. Esa es
  la fecha del envío a notificar, no necesariamente la de la sentencia;
- en `ww2`, el campo de amparo provisional está **vacío**. Con un solo caso no
  se sabe si es la norma.

## Cómo se comporta la búsqueda

Todas las consultas siguientes aceptaron el CAPTCHA. Son respuestas, no fallos.

- **El amparista registrado no es la persona.** Si el actor es una
  organización, el campo dice «[organización], por medio de [persona]». Buscar
  el nombre de la persona no la encuentra.
- **Los terceros interesados no se buscan.** Una persona que figura como
  tercera interesada dio «No hay información para mostrar».
- **Dos palabras devuelven «Demasiados registros, por favor sea más
  específico»**, sin filas. El nombre completo sin tildes no devolvió nada,
  aunque el registro lo guarda con tildes y el formulario pide «solo letras».
  **No comprobado** si las tildes son la causa.
- **No lista por fechas.** En `consultasExternas`, con el nombre vacío y un
  rango de un día, el botón «Buscar» no responde. La fecha de fin escrita a
  mano tampoco se aplica: hay que elegirla en el calendario. **No comprobado**
  si nombre más rango filtra por fecha de admisión.

## Qué sirve y qué no

- **Sirve** para medir la duración de casos concretos (admisión → actuaciones →
  sentencia) y para verificar lo que dice la prensa sobre un amparo de la CSJ.
- **No sirve** para el denominador: no hay forma pública de listar todos los
  amparos de un periodo. Ese universo se pide por acceso a la información, en el
  estado en que se encuentre (art. 45), y ahora se puede nombrar campo por campo.
- **Captura manual.** Cada consulta exige CAPTCHA de una persona. No entra a un
  collector automático.

Capturas con URL, parámetros, hora y hash, fuera de Git (traen nombres de
personas): `data/raw/oj_amparos_csj/`.
