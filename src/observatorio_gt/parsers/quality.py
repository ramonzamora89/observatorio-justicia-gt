"""Comprobacion de plausibilidad lexica del texto extraido.

Existe por una regla heredada concreta: ``pdftotext`` sobre un documento judicial
devolvio «agree ent», «kno ing», «kilo ra s» -- omitia en silencio cada **m**,
**g** y **w**. Paso todas las comprobaciones que no consisten en leer: 423
palabras, parrafos intactos, firma presente. **Una letra que falta es invisible
para un contador de palabras y evidente para un ojo.**

Este modulo es ese ojo, automatizado. Mide cuatro cosas independientes:

1. **Letras ausentes.** Si una letra que el espanol usa con frecuencia conocida
   aparece muchisimo menos de lo esperado, la capa de texto la esta comiendo.
2. **Palabras funcionales.** La prosa espanola real trae "de", "la", "que", "el"
   en proporcion estable. Un texto sin ellas no es prosa.
3. **Fragmentacion.** El OCR de escaner parte las palabras: «M ARLLOR Y CH ACO N
   R O SSELL». Se mide en exceso de tokens de una y dos letras.
4. **Densidad.** Un documento con texto casi vacio no tiene capa utilizable.

Ninguna de las cuatro basta sola. El veredicto las combina, y **ante la duda
manda revisar, no descartar**.

Limite honesto: la **w** es indetectable por frecuencia, porque el espanol
practicamente no la usa (0.01%). Si una capa de texto se comiera solo las w, este
modulo no lo veria. Se documenta en vez de fingir que cubre el caso completo.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum

#: Frecuencia relativa de cada letra en espanol, en porcentaje sobre el total de
#: letras. Solo se vigilan las que superan el umbral: por debajo, la ausencia no
#: distingue un defecto de una casualidad.
FRECUENCIA_ESPANOL: dict[str, float] = {
    "e": 13.7, "a": 12.5, "o": 8.7, "s": 8.0, "r": 6.9, "n": 6.7, "i": 6.2,
    "d": 5.9, "l": 5.0, "c": 4.7, "t": 4.6, "u": 3.9, "m": 3.2, "p": 2.5,
    "b": 1.4, "g": 1.0, "v": 0.9, "y": 0.9, "q": 0.9, "h": 0.7, "f": 0.7,
    "z": 0.5, "j": 0.4, "x": 0.2, "k": 0.01, "w": 0.01,
}

#: Solo se vigilan letras con frecuencia esperada >= 0.8%. Deja fuera w y k, que
#: el espanol casi no usa: su ausencia no prueba nada.
UMBRAL_VIGILANCIA = 0.8

#: Una letra vigilada que aparece por debajo de esta fraccion de lo esperado se
#: considera desaparecida.
FRACCION_SOSPECHOSA = 0.15

#: Palabras funcionales del espanol. Si faltan, no es prosa.
FUNCIONALES: frozenset[str] = frozenset(
    [
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las",
        "por", "un", "para", "con", "no", "una", "su", "al", "lo", "como",
        "mas", "pero", "sus", "le", "ya", "o", "este", "si", "porque", "esta",
        "entre", "cuando", "muy", "sin", "sobre", "tambien", "me", "hasta",
        "hay", "donde", "quien", "desde", "todo", "nos", "durante", "todos",
        "uno", "les", "ni", "contra", "otros", "ese", "eso", "ante", "ellos",
        "e", "esto", "mi", "antes", "algunos", "unos", "yo", "otro", "otras",
        "otra", "tanto", "esa", "estos",
    ]
)

#: Tokens de una letra que si son palabras del espanol.
UNILETRAS_VALIDAS = frozenset("aeouy")

#: Palabras de dos letras que el espanol usa de verdad. Contarlas como
#: fragmentos infla la metrica en cualquier texto sano: en prosa juridica
#: "de", "la" y "en" son de las mas frecuentes del documento.
BILETRAS_VALIDAS: frozenset[str] = frozenset(
    [
        "de", "la", "el", "en", "un", "se", "su", "al", "lo", "no", "es", "ni",
        "si", "ya", "yo", "me", "te", "le", "mi", "tu", "da", "va", "ir", "os",
        "ha", "he", "as", "ex", "id",
    ]
)


class TextVerdict(StrEnum):
    USABLE = "usable"
    #: Hay texto, pero no se puede confiar en el. Manda re-OCR y cotejo.
    SOSPECHOSO = "sospechoso"
    #: Practicamente no hay capa de texto. Es el caso del documento escaneado.
    SIN_CAPA_DE_TEXTO = "sin_capa_de_texto"


@dataclass(frozen=True)
class TextQuality:
    verdict: TextVerdict
    caracteres: int
    palabras: int
    ratio_funcionales: float
    ratio_fragmentacion: float
    letras_desaparecidas: tuple[str, ...] = ()
    razones: tuple[str, ...] = field(default=())

    @property
    def necesita_ocr(self) -> bool:
        return self.verdict is not TextVerdict.USABLE


def _sin_tildes(texto: str) -> str:
    """Quita tildes para contar letras: 'ó' cuenta como 'o'."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


_TOKEN = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def assess(
    texto: str,
    *,
    min_caracteres: int = 200,
    min_ratio_funcionales: float = 0.18,
    max_ratio_fragmentacion: float = 0.12,
) -> TextQuality:
    """Evalua si un texto extraido se puede usar.

    ``min_caracteres`` replica el umbral del proyecto hermano para detectar un
    PDF sin capa de texto.
    """
    razones: list[str] = []
    limpio = texto.replace("\f", " ")
    tokens = [t.lower() for t in _TOKEN.findall(limpio)]
    n_tokens = len(tokens)
    caracteres = len(limpio.strip())

    if caracteres < min_caracteres or n_tokens < 30:
        return TextQuality(
            verdict=TextVerdict.SIN_CAPA_DE_TEXTO,
            caracteres=caracteres,
            palabras=n_tokens,
            ratio_funcionales=0.0,
            ratio_fragmentacion=0.0,
            razones=(f"solo {caracteres} caracteres y {n_tokens} palabras",),
        )

    # 1. Letras que la capa de texto se esta comiendo
    letras = Counter(c for c in _sin_tildes(limpio).lower() if c.isalpha() and c.isascii())
    total_letras = sum(letras.values())
    desaparecidas: list[str] = []
    if total_letras >= 500:
        for letra, esperado in FRECUENCIA_ESPANOL.items():
            if esperado < UMBRAL_VIGILANCIA:
                continue
            observado = 100.0 * letras.get(letra, 0) / total_letras
            if observado < esperado * FRACCION_SOSPECHOSA:
                desaparecidas.append(letra)
        if desaparecidas:
            razones.append(
                "letras casi ausentes frente a lo esperado en espanol: "
                + ", ".join(sorted(desaparecidas))
            )

    # 2. Palabras funcionales
    n_funcionales = sum(1 for t in tokens if t in FUNCIONALES)
    ratio_funcionales = n_funcionales / n_tokens
    if ratio_funcionales < min_ratio_funcionales:
        razones.append(
            f"solo {ratio_funcionales:.1%} de palabras funcionales "
            f"(minimo {min_ratio_funcionales:.0%}): no se lee como prosa"
        )

    # 3. Fragmentacion tipo OCR de escaner
    fragmentos = sum(
        1 for t in tokens if len(t) == 1 and t not in UNILETRAS_VALIDAS
    ) + sum(1 for t in tokens if len(t) == 2 and t not in BILETRAS_VALIDAS)
    ratio_fragmentacion = fragmentos / n_tokens
    if ratio_fragmentacion > max_ratio_fragmentacion:
        razones.append(
            f"{ratio_fragmentacion:.1%} de tokens sueltos de una o dos letras: "
            "el texto parece partido"
        )

    verdict = TextVerdict.SOSPECHOSO if razones else TextVerdict.USABLE
    return TextQuality(
        verdict=verdict,
        caracteres=caracteres,
        palabras=n_tokens,
        ratio_funcionales=ratio_funcionales,
        ratio_fragmentacion=ratio_fragmentacion,
        letras_desaparecidas=tuple(sorted(desaparecidas)),
        razones=tuple(razones),
    )
