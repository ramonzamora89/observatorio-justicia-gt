from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from observatorio_gt.integracion import Magistrado, cargar_lista, integracion

LISTA = Path("sources/cc/magistrados.csv")


@pytest.fixture(scope="module")
def lista() -> list[Magistrado]:
    return cargar_lista(LISTA)


def test_firma_digital(lista: list[Magistrado]) -> None:
    texto = (
        "II) Notifíquese. Firmado digitalmente por ROBERTO MOLINA BARRETO Fecha: 21/09/2023 "
        "Firmado digitalmente por DINA JOSEFINA OCHOA ESCRIBA Fecha: 21/09/2023"
    )
    assert set(integracion(texto, date(2023, 9, 21), lista)) == {
        "Roberto Molina Barreto", "Dina Josefina Ochoa Escribá"
    }


def test_palabras_partidas_y_columnas_intercaladas(lista: list[Magistrado]) -> None:
    partidas = "Notifíquese. DIN A JOSEFIN A OCH OA ESCR IBÁ MAGISTRADA"
    assert integracion(partidas, date(2019, 5, 6), lista) == ["Dina Josefina Ochoa Escribá"]
    intercaladas = "Notifíquese. ROBERTO DINA MOLINA JOSEFINA BARRETO MAGISTRADO"
    assert "Roberto Molina Barreto" in integracion(intercaladas, date(2024, 3, 1), lista)


def test_apellidos_sueltos_no_inventan_a_un_tercero(lista: list[Magistrado]) -> None:
    """«FLORES» de un magistrado y «HERNANDEZ» del secretario no son Flores Hernández."""
    texto = (
        "Notifíquese. JUAN FRANCISCO FLORES JUÁREZ PRESIDENTE LUIS DE JESÚS HERNÁNDEZ "
        "TORRES SECRETARIO GENERAL"
    )
    assert integracion(texto, date(2005, 8, 23), lista) == ["Juan Francisco Flores Juárez"]


def test_solo_quien_estaba_en_funciones(lista: list[Magistrado]) -> None:
    texto = "Notifíquese. JULIA MARISOL RIVERA AGUILAR MAGISTRADA"
    assert integracion(texto, date(2010, 1, 1), lista) == []
    assert integracion(texto, date(2026, 6, 1), lista) == ["Julia Marisol Rivera Aguilar"]


def test_cambio_de_magistratura_el_14_de_abril(lista: list[Magistrado]) -> None:
    texto = "Notifíquese. JULIA MARISOL RIVERA AGUILAR MAGISTRADA"
    assert integracion(texto, date(2026, 4, 13), lista) == []
    assert integracion(texto, date(2026, 4, 14), lista) == ["Julia Marisol Rivera Aguilar"]


def test_variantes_de_grafia(lista: list[Magistrado]) -> None:
    texto = "Notifíquese. GLORIA MELGAR DE AGUILAR MAGISTRADA"
    assert integracion(texto, date(2005, 1, 1), lista) == [
        "Gloria Evangelina Melgar Rojas de Aguilar"
    ]
