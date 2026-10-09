# Ficha de fuente — Sistema de Consulta de Jurisprudencia de la CC (`consultajur`)

**Consultado:** 2026-10-08, a mano, desde Chrome (operado con Claude in Chrome).
**Pregunta:** ¿qué ofrece la CC además del portal que usa el collector
(`jurisprudencia.cc.gob.gt/ptmp`, ver `jurisprudencia/FICHA_CC_PTMP.md`)?

**Respuesta corta: el sistema vigente de jurisprudencia es otro, y publica los
autos —incluidos los de amparo provisional— que el portal viejo no muestra.**
Todavía no se ha caracterizado técnicamente: esta ficha es de reconocimiento.

## Dónde está

- Enlace desde `cc.gob.gt` → Servicios → Jurisprudencia → «Consulta de
  jurisprudencia»: `https://consultajur.cc.gob.gt/wcJur`
- Redirige a `/wcJur/Portal/wfPrincipal.aspx` (ASP.NET WebForms).
- Su botón **«Sistema anterior»** lleva a `jurisprudencia.cc.gob.gt/ptmp/Inicio.aspx`:
  **el portal del collector es el sistema anterior.**
- `robots.txt`: **404** (consultado con el user-agent del proyecto). No hay
  política declarada, ni las Content-Signals de `jurisprudencia.cc.gob.gt`.
- Cloudflare: la primera visita desde el navegador de Moncho pasó un desafío;
  la siguiente pestaña cargó sin desafío. **No comprobado** cómo responde a un
  cliente HTTP.

## Secciones

| Sección | Página | Modos de búsqueda |
|---|---|---|
| Sentencias | `wfTextoLibre.aspx` | Texto libre · Número de expediente · Tipo de proceso y tema |
| Autos | `wfTextoLibreAut.aspx` | Texto libre · Número de expediente · Consulta por propiedades |
| Estándares internacionales | `wfInterDerHum.aspx` | no abierta |
| Doctrina legal | `wfConsJurCC.aspx` | no abierta |
| Boletines, Innovaciones, Resoluciones de interés | menú | no abiertas |

El texto libre dice admitir **búsqueda exacta uniendo términos con «+»**
(`niñez+salud+libertad`). El portal viejo no hace búsqueda de frase (ver «Cosas
que NO hay que volver a intentar» en `TAREAS.md`). **No comprobado** que este
sí la haga: hay que medirlo antes de contar nada con él.

Cada resultado ofrece «Ver resolución» (visor de PDF) y «Ver ficha
jurisprudencial».

## Dos pruebas

**Sentencias, texto libre «CACIF».** 66 expedientes, de 2000 a 2025, con tipo
de proceso. Son **menciones en el texto**, no casos con esa entidad como
postulante: la trampa del conteo de «antejuicio» (`CLAUDE.md`).

**Autos, texto libre «amparo provisional» (sin «+»).** Lista larga, total y
orden no comprobados. Tipos de resolución que aparecen: apelación de auto de
amparo provisional, apelación de auto de suspensión, ocurso de queja,
aclaración y/o ampliación, enmienda de oficio, desistimiento, auto para mejor
fallar, planteamiento de error sustancial. Expedientes de 2016 a 2026.

## Por qué importa

- **Amparo provisional (tarea 12).** Queda registrado al menos cuando su auto se
  apela ante la CC. **No comprobado** si aparece el provisional que la CC
  otorga o deniega en sus propios amparos de única instancia.
- **Autos en general.** El portal viejo publica sentencias; los autos son otra
  capa de la actividad de la Corte (incidentes, quejas, aclaraciones) que el
  denominador actual no ve.

## Lo que esta ficha no resuelve

- Si `consultajur` y `ptmp` comparten base de datos o si uno tiene documentos
  que el otro no. El censo de `ptmp` sí trae sentencias de 2025 (4.146) y 2026
  (2.009): la cobertura reciente no es lo que los distingue.
- Endpoints, paginación, límites de tasa, estabilidad de identificadores. Eso es
  un spike técnico aparte, igual al que se hizo con `ptmp`, y sin descarga
  masiva.

## Consulta de expedientes de la CC: fuera de alcance

`cc.gob.gt` → Servicios → «Consulta de expedientes» lleva a
`casillero.cc.gob.gt/consultaweb/`. Tiene desafío de Cloudflare con casilla y
después **exige crear un usuario**. Al intentarlo, el servidor devolvió un error
de ejecución genérico de ASP.NET (`/ConsultaWEb/frmUsuario.aspx`).
**Requiere cuenta: queda fuera por la regla de no usar login.** Era la única
fuente pública candidata para ver **expedientes en trámite** de la CC. Ese dato
se pide por acceso a la información.

«Consulta de expedientes archivados»
(`jurisprudencia.cc.gob.gt/ConsArch/…`) no se abrió.

Notas de la exploración, fuera de Git: `data/raw/cc_consultajur/`.
