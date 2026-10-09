"""Fechas en letras. Una fecha mal leida corre plazos falsos."""

from __future__ import annotations

from datetime import date

import pytest

from observatorio_gt.extractors.fechas import (
    fecha_de_presentacion,
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


# -- el año no se traga lo que sigue a la «y» ------------------------------
@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        # Leidos antes como 2009 y 2026: plausibles y falsos.
        ("el veintisiete de junio de dos mil siete y dos de julio", date(2007, 6, 27)),
        ("el veintidós de diciembre de dos mil veintiuno y cinco de enero", date(2021, 12, 22)),
        ("treinta y uno de agosto de mil novecientos noventa y ocho", date(1998, 8, 31)),
        ("el dieciséis de mayo del dos mil cinco.", date(2005, 5, 16)),
        ("el dieciséis de diciembre dos mil diecinueve, en esta Corte", date(2019, 12, 16)),
        ("presentado eltres de junio de dos mil dieciséis,en el Centro", date(2016, 6, 3)),
    ],
)
def test_anio_con_gramatica(texto: str, esperado: date) -> None:
    resultado = parse_fecha(texto)
    assert resultado is not None and resultado[0] == esperado


# -- fecha de presentacion ------------------------------------------------
APELACION = (
    "ANTECEDENTES I. EL AMPARO A) Interposición y autoridad: presentado el\n"
    "veinticuatro de febrero de dos mil siete, en el Juzgado Primero de Paz de Turno y,\n"
    "posteriormente, remitido a la Sala. B) Acto reclamado: resolución de diez de\n"
    "enero de dos mil siete."
)


def test_presentacion_lee_su_apartado_no_el_acto_reclamado() -> None:
    p = fecha_de_presentacion(APELACION)
    assert p is not None
    assert p.fecha == date(2007, 2, 24)
    assert p.ante_la_cc is False
    assert "Acto reclamado" not in p.apartado


def test_presentacion_en_unica_instancia_es_ante_la_cc() -> None:
    texto = (
        "A) Solicitud y autoridad: presentado el siete de julio de dos mil diecisiete, "
        "en esta Corte. B) Acto reclamado: resolución de diez de abril de dos mil diecisiete."
    )
    p = fecha_de_presentacion(texto)
    assert p is not None and p.fecha == date(2017, 7, 7) and p.ante_la_cc is True


def test_varias_acciones_no_eligen_una_fecha() -> None:
    texto = (
        "A) Solicitud y autoridad: presentados, respectivamente, el veinte y treinta y uno "
        "de agosto de dos mil quince, en esta Corte. B) Actos reclamados: ..."
    )
    p = fecha_de_presentacion(texto)
    assert p is not None and p.varias is True and p.fecha is None


def test_sin_apartado_no_cae_a_otra_fecha() -> None:
    """Una inconstitucionalidad no trae el apartado; la primera fecha es otra cosa."""
    texto = (
        "ANTECEDENTES I. FUNDAMENTOS JURÍDICOS DE LA IMPUGNACIÓN a) el veintiséis de "
        "febrero de mil novecientos noventa y ocho, el Congreso aprobó el Decreto 15-98."
    )
    assert fecha_de_presentacion(texto) is None
