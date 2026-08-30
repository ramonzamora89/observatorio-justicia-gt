"""Fechas en letras. Una fecha mal leida corre plazos falsos."""

from __future__ import annotations

from datetime import date

import pytest

from observatorio_gt.extractors.fechas import (
    fecha_de_resolucion,
    numero_en_letras,
    parse_fecha,
    plano,
)


@pytest.mark.parametrize(
    ("frase", "esperado"),
    [
        ("dos mil trece", 2013),
        ("dos mil cuatro", 2004),
        ("mil novecientos noventa y ocho", 1998),
        ("mil novecientos ochenta y siete", 1987),
        ("dos mil dieciseis", 2016),
        ("treinta y uno", 31),
        ("veintitres", 23),
        ("primero", 1),
    ],
)
def test_numeros_en_letras(frase: str, esperado: int) -> None:
    assert numero_en_letras(frase) == esperado


def test_frase_no_reconocida_devuelve_none() -> None:
    """Adivinar un ano es peor que no tenerlo."""
    assert numero_en_letras("aproximadamente dos mil") is None
    assert numero_en_letras("") is None


def test_plegado_de_acentos_conserva_la_longitud() -> None:
    """Si cambiara la longitud, las citas se recortarian desalineadas."""
    original = "veintitrés de febrero de dos mil dieciséis"
    assert len(plano(original)) == len(original)
    assert "veintitres" in plano(original)


def test_fecha_con_acentos() -> None:
    """«dieciséis» con tilde no encajaba: el vocabulario esta sin tildes."""
    resultado = parse_fecha("Guatemala, veintitrés de febrero de dos mil dieciséis.")
    assert resultado is not None
    assert resultado[0] == date(2016, 2, 23)
    assert "veintitrés" in resultado[1], "la cita debe conservar la ortografia original"


def test_fecha_sin_punto_final() -> None:
    """Exigir puntuacion costo una fecha equivocada en el corpus real."""
    texto = "Guatemala, tres de marzo de mil novecientos noventa y nueve En apelación"
    resultado = parse_fecha(texto)
    assert resultado is not None
    assert resultado[0] == date(1999, 3, 3)


def test_fecha_numerica_de_respaldo() -> None:
    resultado = parse_fecha("Resolucion de 01/03/2004 del tribunal")
    assert resultado is not None and resultado[0] == date(2004, 3, 1)


def test_fecha_imposible_se_ignora() -> None:
    assert parse_fecha("treinta y uno de febrero de dos mil trece") is None


# -- lo que de verdad importa: cual de las fechas del documento -----------
DOS_FECHAS = (
    "APELACIÓN DE SENTENCIA DE AMPARO\n"
    "CORTE DE CONSTITUCIONALIDAD: Guatemala, veintitrés de febrero de dos mil dieciséis. "
    "En apelación y con sus antecedentes, se examina la sentencia de seis de noviembre "
    "de dos mil quince, dictada por la Sala Primera."
)


def test_toma_la_fecha_del_tribunal_no_la_de_la_sentencia_apelada() -> None:
    """En 3 de 20 documentos, la primera fecha es la del fallo recurrido."""
    resultado = fecha_de_resolucion(DOS_FECHAS)
    assert resultado is not None
    fecha, _cita, anclada = resultado
    assert fecha == date(2016, 2, 23), "no debe tomar la fecha de la sentencia apelada"
    assert anclada is True


def test_encabezado_con_calidad_de_tribunal_extraordinario() -> None:
    """El corpus trae dos redacciones del encabezado."""
    texto = (
        "CORTE DE CONSTITUCIONALIDAD, EN CALIDAD DE TRIBUNAL EXTRAORDINARIO DE AMPARO: "
        "Guatemala, veintidós de abril de mil novecientos noventa y siete. Se tiene a la vista."
    )
    resultado = fecha_de_resolucion(texto)
    assert resultado is not None and resultado[0] == date(1997, 4, 22)
    assert resultado[2] is True


def test_sin_encabezado_cae_a_la_primera_pero_lo_declara() -> None:
    """Sirve, con menos confianza, y el registro dice que no venia anclada."""
    resultado = fecha_de_resolucion("Sentencia de tres de marzo de dos mil diez.")
    assert resultado is not None
    assert resultado[0] == date(2010, 3, 3)
    assert resultado[2] is False
