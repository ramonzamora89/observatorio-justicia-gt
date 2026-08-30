"""La comprobacion de plausibilidad lexica, probada contra sus modos de fallo.

Cada test corresponde a una forma real de que un texto extraido parezca completo
y no lo este.
"""

from __future__ import annotations

import random

import pytest

from observatorio_gt.parsers.quality import TextVerdict, assess

# Prosa juridica en espanol, del estilo del corpus real. Se repite para superar
# el minimo de letras que exige el analisis de frecuencias.
PARRAFO = (
    "CORTE DE CONSTITUCIONALIDAD: Guatemala, treinta y uno de octubre de dos mil "
    "trece. En apelacion y con sus antecedentes, se examina la sentencia dictada "
    "por la Sala Tercera de la Corte de Apelaciones de Trabajo, constituida en "
    "Tribunal de Amparo, en la accion constitucional de amparo promovida por el "
    "Estado de Guatemala contra el Juez Sexto de Primera Instancia del Ramo Civil "
    "del departamento de Guatemala. El amparo se otorga porque la autoridad "
    "impugnada omitio fundamentar su decision, con lo que vulnero el derecho de "
    "defensa que garantiza la Constitucion Politica de la Republica. "
)
SANO = PARRAFO * 6


def fragmentar(texto: str, prob: float, semilla: int = 7) -> str:
    """Reproduce el destrozo de un OCR de escaner: «M ARLLOR Y CH ACO N»."""
    rnd = random.Random(semilla)
    salida = []
    for palabra in texto.split():
        if len(palabra) > 2 and rnd.random() < prob:
            trozos, i = [], 0
            while i < len(palabra):
                n = rnd.choice((1, 1, 2, 3))
                trozos.append(palabra[i : i + n])
                i += n
            salida.append(" ".join(trozos))
        else:
            salida.append(palabra)
    return " ".join(salida)


# -- control -------------------------------------------------------------
def test_prosa_sana_es_usable() -> None:
    q = assess(SANO)
    assert q.verdict is TextVerdict.USABLE
    assert q.ratio_funcionales > 0.30
    assert q.ratio_fragmentacion < 0.05
    assert q.letras_desaparecidas == ()


# -- capa de texto que se come letras -----------------------------------
def test_el_caso_heredado_de_las_letras_que_faltan() -> None:
    """`pdftotext` devolvia «agree ent», «kno ing»: omitia cada m, g y w.

    Pasaba todas las comprobaciones que no consisten en leer.
    """
    corrupto = SANO.translate(str.maketrans("", "", "mgwMGW"))
    q = assess(corrupto)
    assert q.verdict is TextVerdict.SOSPECHOSO
    assert set(q.letras_desaparecidas) >= {"g", "m"}
    # y sigue teniendo casi todas las palabras: por eso un contador no lo ve
    assert q.palabras > assess(SANO).palabras * 0.95


@pytest.mark.parametrize("letra", ["m", "g", "c", "d", "l", "p"])
def test_una_sola_letra_frecuente_que_desaparece(letra: str) -> None:
    q = assess(SANO.translate(str.maketrans("", "", letra + letra.upper())))
    assert q.verdict is TextVerdict.SOSPECHOSO
    assert letra in q.letras_desaparecidas


def test_la_w_es_el_limite_declarado() -> None:
    """El espanol usa la w un 0.01%: su ausencia es indetectable por frecuencia.

    Se documenta en vez de fingir que el modulo cubre el caso completo.
    """
    q = assess(SANO.translate(str.maketrans("", "", "wW")))
    assert q.verdict is TextVerdict.USABLE
    assert "w" not in q.letras_desaparecidas


# -- fragmentacion tipo escaner -----------------------------------------
def test_fragmentacion_fuerte_se_detecta() -> None:
    q = assess(fragmentar(SANO, 0.5))
    assert q.verdict is TextVerdict.SOSPECHOSO
    assert q.ratio_fragmentacion > 0.12


def test_fragmentacion_leve_pasa_y_esta_documentado() -> None:
    """Por debajo de ~8% de palabras afectadas no se detecta. Es el piso real."""
    assert assess(fragmentar(SANO, 0.02)).verdict is TextVerdict.USABLE


def test_palabras_de_dos_letras_legitimas_no_son_fragmentos() -> None:
    """'de', 'la', 'en' son de las mas frecuentes en prosa juridica."""
    q = assess("de la en el un se " * 60 + SANO)
    assert q.ratio_fragmentacion < 0.05


# -- ausencia de capa ----------------------------------------------------
def test_sin_capa_de_texto() -> None:
    q = assess("")
    assert q.verdict is TextVerdict.SIN_CAPA_DE_TEXTO
    assert q.necesita_ocr


def test_texto_minimo_es_ausencia_de_capa() -> None:
    """Un PDF escaneado suele dar unas pocas basuras, no cero."""
    q = assess("1\n\f2\n\f3\n")
    assert q.verdict is TextVerdict.SIN_CAPA_DE_TEXTO


def test_texto_que_no_es_prosa() -> None:
    """Muchas palabras, ninguna funcional: una tabla de cifras, no un texto."""
    q = assess(" ".join(f"registro{i} valor{i}" for i in range(400)))
    assert q.verdict is TextVerdict.SOSPECHOSO
    assert any("prosa" in r for r in q.razones)


def test_las_tildes_cuentan_como_su_letra_base() -> None:
    """'ó' es una o: si no, el analisis de frecuencias se descalibra."""
    assert assess(SANO.replace("o", "ó")).verdict is TextVerdict.USABLE
