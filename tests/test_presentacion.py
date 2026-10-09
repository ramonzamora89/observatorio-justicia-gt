from __future__ import annotations

from datetime import date

import pytest

from observatorio_gt.extractors.fechas import parse_fecha
from observatorio_gt.presentacion import alertas, anio_expediente


@pytest.mark.parametrize(
    ("exp", "anio"), [("5187-2016", 2016), ("293-98", 1998), ("12-05", 2005), ("sin año", None)]
)
def test_anio_expediente(exp: str, anio: int | None) -> None:
    assert anio_expediente(exp) == anio


def test_fecha_plausible_no_alerta() -> None:
    assert alertas(date(2016, 3, 1), date(2017, 5, 2), "5187-2016") == []


def test_alertas_marcan_sin_corregir() -> None:
    assert alertas(date(1002, 10, 31), None, "1523-2001")[0] == "anio_de_presentacion_imposible"
    assert "presentacion_posterior_a_la_resolucion" in alertas(
        date(2004, 6, 1), date(2004, 2, 2), "1173-2004"
    )
    assert "presentacion_posterior_al_anio_del_expediente" in alertas(
        date(2019, 1, 5), None, "100-2018"
    )
    assert alertas(date(2003, 3, 22), None, "3171-2011") == [
        "presentacion_mas_de_5_anios_antes_del_expediente"
    ]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("el treinta de diciembrede dos mil quince", date(2015, 12, 30)),
        ("elveintiocho de marzodedos mil dieciséis, enla Sala", date(2016, 3, 28)),
        ("el ocho de junio del año dos mil uno", date(2001, 6, 8)),
    ],
)
def test_erratas_del_corpus(texto: str, esperado: date) -> None:
    r = parse_fecha(texto)
    assert r is not None and r[0] == esperado


def test_fecha_relativa_no_se_adivina() -> None:
    assert parse_fecha("el catorce de marzo del año en curso") is None
