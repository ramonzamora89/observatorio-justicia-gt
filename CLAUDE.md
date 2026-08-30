# CLAUDE.md

## Rol
Implementa el Observatorio de Resoluciones Judiciales de Guatemala siguiendo `PROJECT.md`, `PRD-1.md`, `DATA_MODEL.md` y `PIPELINE.md`.

## Regla principal
No intentes construir todo el sistema de una vez. Trabaja mediante tareas pequeñas, verificables y con tests.

## Antes de programar
1. Lee todos los documentos raíz.
2. Inspecciona el repositorio.
3. Identifica el milestone actual.
4. Escribe un plan corto.
5. Implementa solamente ese milestone.
6. Ejecuta tests.
7. Documenta resultados y limitaciones.

## Restricciones de investigación
- Solo fuentes públicas y legalmente accesibles.
- No evadir CAPTCHA, login ni controles de acceso.
- Rate-limit collectors.
- Conservar URL y hash de cada documento.
- Nunca convertir inferencias en hechos.
- No etiquetar jueces/personas como corruptos automáticamente.
- Una anomalía estadística es una señal para investigación, no prueba de conducta ilícita.

## Código
- Python 3.12+
- type hints
- Pydantic para contratos de datos
- pytest
- funciones pequeñas
- separación estricta entre adquisición, parsing, extracción y análisis
- configuración fuera del código
- logging estructurado

## IA/LLM
Toda extracción LLM debe:
- usar schema;
- devolver confidence;
- devolver evidencia;
- permitir `null`;
- guardar versión de prompt/modelo;
- ser reproducible/auditable.

No pedir al modelo que determine si un juez es corrupto.

## Git
Commits pequeños y descriptivos.

No incluir documentos judiciales masivos en Git. Guardar manifests y hashes; usar almacenamiento de datos separado.

## Primer milestone
Crear un **CC discovery spike**.

Objetivo:
1. investigar técnicamente el Portal de Jurisprudencia de la CC;
2. documentar endpoints/formularios disponibles sin evadir controles;
3. crear collector de prueba;
4. obtener metadata de 20 resoluciones;
5. guardar manifest JSONL;
6. crear tests;
7. no ejecutar scraping masivo todavía.

## Definition of Done
Cada milestone debe producir:
- código;
- tests;
- README/update;
- sample output;
- lista de problemas conocidos;
- siguiente tarea recomendada.

---

# Reglas heredadas

Estas no son teoría. Cada una **produjo un resultado falso** en trabajo previo
con documentos judiciales, y se descubrió después. Tratan de exactamente lo que
este pipeline va a procesar.

## Un número de expediente equivocado es una persona equivocada

Una lista asignó a un acusado un número de causa que en realidad era de **otro
hombre**, muerto antes del juicio. El repositorio judicial seguía devolviendo la
carátula con el otro apellido: el repositorio tenía razón y la lista estaba mal.

**Un número de caso es una afirmación de identidad**, igual que un nombre.
Fusionar por número sin abrir el documento es el mismo error que fusionar por
apellido. **Una carátula que no corresponde a la persona es una señal de alto,
no una curiosidad.**

Para este pipeline: al ligar una resolución con un expediente, verificar que
las partes coinciden, y si no coinciden **no ligar** y marcarlo para revisión.

## Una capa de texto puede perder letras y verse completa

`pdftotext` sobre un documento judicial devolvió «agree ent», «kno ing»,
«kilo ra s»: omitía en silencio cada **m**, **g** y **w**. Pasó todas las
comprobaciones que no consisten en leer: 423 palabras, párrafos intactos, firma
presente. El PDF hermano del mismo tribunal no tenía el defecto, así que es una
propiedad **del archivo**, no del tribunal.

**Antes de citar de un PDF, leer una frase de la extracción como prosa.** Una
letra que falta es invisible para un contador de palabras y evidente para un
ojo. En un pipeline automático: una comprobación de plausibilidad léxica por
documento, y si falla, re-OCR con `--force-ocr` y verificación contra la imagen.

## El OCR del propio tribunal puede ser peor que el nuestro

Un documento llegó con capa de texto hecha por el escáner del tribunal
(LeanScan 3.5). Rendía el apellido de la acusada partido en pedazos, con
espacios dentro de cada palabra: «CH ACO N R O SSELL».

**Que un PDF tenga texto no significa que tenga texto usable.** Comprobar el
campo `Producer` con `pdfinfo`: si viene de un escáner, descartar esa capa y
re-OCR.

## Una cláusula que firman todos no distingue a nadie

Un acuerdo traía una cláusula de cooperación completa, con testimonio veraz y
hasta trabajo encubierto. Leída sola parecía un hallazgo. **Aparece palabra por
palabra en los otros dos acuerdos comparables. Tres de tres: es la plantilla del
distrito.**

**Antes de tratar cualquier lenguaje de formulario como un hallazgo, contar en
cuántos documentos comparables aparece.** Esto vale para acusaciones, renuncias
y condiciones estándar, y es la razón por la que este proyecto necesita el
denominador antes que la anécdota.

## «Amended» no quiere decir que cambió el fondo

Tres documentos enmendados, tres cosas distintas: uno **redujo la pena** y lo
dice; otro **no tocó la pena** y sólo corrigió un número de registro; el tercero
**movió una audiencia media hora**.

**Una enmienda es una reducción sólo si el documento dice por qué se enmendó.**
Cuando el formulario deja ese campo vacío, comparar contra el original y
reportar qué cambió de verdad. Si no cambió nada de fondo, eso es el hallazgo.

## Sin denominador no hay patrón

Un conjunto de resoluciones que apuntan en una dirección no prueba nada sin
saber cuántas dictó ese órgano y en qué sentido. **Sin el denominador no es un
patrón: es una lista de casos que le dan la razón a quien la armó.**

Es la razón de existir de este proyecto, así que va en el diseño y no sólo en la
advertencia: **ningún indicador por juez se publica sin su universo comparable
al lado**, y la comparación se pide para toda la judicatura, no sólo para el
órgano de interés. Pedir sólo por el que interesa mete el sesgo en la pregunta.

## Una respuesta vacía no es un resultado negativo

Un repositorio devuelve **HTTP 202 con cuerpo vacío** cuando limita la tasa. Una
lectura ingenua lo cuenta como cero resultados y concluye que el documento no
existe. Eso marcó tres casos como ausentes que sólo estaban en cola.

**Comprobar el código de estado y el largo del cuerpo antes de concluir
ausencia.** Y cuando una comprobación no se pudo completar, escribir **«no
comprobado»**, nunca «no está». Un HTTP 200 con veinte palabras también es una
descarga fallida.

## Lo que ya se sabe de estas fuentes, y ahorra semanas

Trabajo de campo sobre el Organismo Judicial, agosto de 2026:

- **el Organismo Judicial no tiene ventanilla que reciba una solicitud de
  información**: varias dependencias responden que no les toca y remiten a otra,
  y sin acuse no corre plazo;
- sus **boletines estadísticos desagregados dejaron de publicarse en 2011**;
- **SICEJ**, el consultor de expedientes, **sólo lo pueden usar las partes** de
  cada caso;
- **CIDEJ** aparece como operador del sistema y **no es CENADOJ**: es un
  destinatario que todavía no se ha probado.

Las fases 2 a 4 de este proyecto dependen de ahí. Conviene empezar sabiéndolo.
