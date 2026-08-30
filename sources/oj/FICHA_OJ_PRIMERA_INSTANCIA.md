# Ficha de fuente — Organismo Judicial: Salas de Apelaciones y primera instancia

**Consultado:** 2026-08-30
**Pregunta:** ¿se pueden recolectar resoluciones de Salas de Apelaciones y de
juzgados de primera instancia? Son las fases 3 y 4 de `PROJECT.md`.

**Respuesta corta: no por vía automatizada, y el obstáculo es un control de
acceso que este proyecto no evade.**

## Lo que devolvió cada host

| Recurso | Resultado |
|---|---|
| `portal.oj.gob.gt/` | primera petición **200**; a partir de la segunda, **«Radware Captcha Page»** |
| `portal.oj.gob.gt/?page_id=6577` (Consultas Externas) | **302** → `validate.perfdrive.com` (ShieldSquare / Radware Bot Manager) |
| `sicej.oj.gob.gt/robots.txt` | **404** |
| `ww2.oj.gob.gt/robots.txt` | **200**, pero es el robots.txt de ejemplo que trae Joomla, sin reglas propias |
| CENADOJ (`ww2.oj.gob.gt/…/CentroAnalisisDocumentacionJudicial/`) | **218 bytes**, sin contenido útil |

El desafío de Radware llega a devolver nuestro propio user-agent dentro de la URL
(`sst=ObservatorioJusticiaGT/0.1.0…`): reconoce al cliente y lo manda a validar.

## Por qué se para aquí

`CLAUDE.md` lo dice sin margen: **no evadir CAPTCHA, login ni controles de
acceso.** Un muro anti-bot es exactamente eso. No se prueba con navegador
automatizado, ni rotando user-agent, ni bajando el ritmo hasta colarse.

**Distinción que importa:** el material **es público**. Una persona con un
navegador puede consultar el portal. Lo que no está disponible es la
**recolección automatizada a escala**, que es lo que un observatorio necesita
para construir un denominador. No es lo mismo «no se puede ver» que «no se puede
contar».

## Lo que ya se sabía, y esto confirma

- **SICEJ**, el consultor de expedientes, solo lo pueden usar las partes de cada
  caso: pide número de expediente **y** contraseña.
- **CENADOJ** publica estadística, no resoluciones, y su serie desagregada se
  corta en 2011.
- El Organismo Judicial **no tiene ventanilla que reciba una solicitud de
  información**: las dependencias se remiten unas a otras y sin acuse no corre
  plazo.

## Consecuencia para el plan

Las fases 3 y 4 de `PROJECT.md` —Salas de Apelaciones y primera instancia— **no
tienen hoy una vía técnica**. Las que quedan son institucionales:

1. **CIDEJ** (Centro de Información, Desarrollo y Estadística Judicial), que
   aparece como operador de SICEJ y no es CENADOJ. **Destinatario no probado.**
2. Una solicitud formal de acceso a información, con el problema de la ventanilla
   ya documentado.
3. Consulta manual con navegador, caso por caso, que sirve para verificar un
   expediente concreto pero no para construir un universo.

**Lo que sí se puede seguir haciendo mientras tanto:** la CC publica la sentencia
de primera y segunda instancia *como antecedente* dentro de sus propias
resoluciones. El campo `Tribunal de amparo de primer grado` de la ficha del
portal ya identifica al órgano inferior en 69 de 140 documentos sondeados. Eso no
da el universo de lo que resuelven esos órganos, pero sí una muestra sesgada
—solo lo que llegó en amparo a la CC— que puede servir para preguntas acotadas,
declarando el sesgo.
