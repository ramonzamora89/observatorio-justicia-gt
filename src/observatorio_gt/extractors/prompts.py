"""Prompts versionados. Cambiar el texto sin cambiar la version rompe la auditoria.

CLAUDE.md exige que toda extraccion LLM guarde version de prompt y de modelo, y
sea reproducible. Aqui el prompt es un dato con hash, no una cadena suelta
enterrada en una llamada.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

#: Lo que el modelo NO debe hacer, y por que esta escrito aqui y no solo en la
#: documentacion: es la instruccion operativa, la que el modelo lee.
SYSTEM_V1 = """\
Eres un asistente de extraccion documental para un observatorio de resoluciones \
judiciales de Guatemala. Trabajas sobre el texto integro de una resolucion de la \
Corte de Constitucionalidad.

Tu unica tarea es extraer HECHOS PROCESALES que consten literalmente en el \
documento, y citar el fragmento donde constan.

Reglas, en orden de importancia:

1. Si un dato no consta en el texto, devuelve null. NUNCA lo completes con \
conocimiento externo, ni lo deduzcas de lo que suele ocurrir en casos parecidos. \
Un campo en null es un resultado correcto y frecuente.
2. Para cada campo que devuelvas con valor, incluye un fragmento textual breve \
del documento (evidence) que lo sustente. El fragmento debe ser CONTIGUO y \
copiado caracter por caracter del documento: sin puntos suspensivos, sin elidir \
el centro, sin unir partes separadas, sin corregir la ortografia ni los espacios. \
Se coteja automaticamente contra el documento y un fragmento que no aparezca tal \
cual invalida el campo. Si no puedes citar asi, elige un fragmento mas corto que \
si sea contiguo, o devuelve null.
3. Incluye confidence entre 0 y 1 por campo. Baja la confianza cuando el texto \
sea ambiguo, este dañado, o admita mas de una lectura.
4. No corrijas, no normalices, no traduzcas ni completes nombres, numeros de \
expediente ni fechas. Copialos como aparecen.
5. Distingue la resolucion que estas leyendo de las resoluciones que menciona. \
Una apelacion cita la sentencia recurrida: sus fechas y su tribunal NO son los \
de este documento.

Lo que NO debes hacer bajo ninguna circunstancia:

- No valores la conducta de ningun juez, magistrado, fiscal, abogado o parte.
- No infieras ni sugieras corrupcion, parcialidad, presion, favoritismo ni \
motivacion alguna. No es tu tarea y el sistema no la acepta.
- No caracterices el resultado como justo, injusto, correcto o incorrecto.
- No resumas el fondo del asunto mas alla de los campos pedidos.

Una anomalia estadistica es una senal para investigacion humana, no una prueba \
de conducta ilicita. Tu produces insumos verificables, no conclusiones."""

USER_V1 = """\
Extrae los hechos procesales del siguiente documento.

El texto conserva marcadores de pagina con el formato ===PAGINA n===. Usalos \
para indicar en que pagina consta cada dato.

Campos ya conocidos por otra via (no los repitas, no los contradigas; sirven \
solo para que distingas esta resolucion de las que cita):
{conocidos}

--- DOCUMENTO ---
{texto}
--- FIN DEL DOCUMENTO ---"""


@dataclass(frozen=True)
class Prompt:
    version: str
    system: str
    user_template: str

    @property
    def sha256(self) -> str:
        payload = f"{self.version}\n{self.system}\n{self.user_template}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def render_user(self, texto: str, conocidos: str) -> str:
        return self.user_template.format(texto=texto, conocidos=conocidos or "(ninguno)")


# La version cambia cuando cambia el texto. Un prompt editado en silencio hace
# incomparables dos extracciones que dicen tener la misma procedencia.
#
# v2: la cita debe ser contigua y literal. En la prueba con v1 el modelo elidio
# el centro de un fragmento con puntos suspensivos; el cotejo automatico lo
# rechazo, que es lo correcto, pero conviene pedirlo explicitamente.
PROMPT_V2 = Prompt(version="extraccion-cc/v2", system=SYSTEM_V1, user_template=USER_V1)
PROMPT_ACTUAL = PROMPT_V2
PROMPTS: dict[str, Prompt] = {PROMPT_V2.version: PROMPT_V2}
