"""Censo del universo publicado: el denominador."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from observatorio_gt.censo import (
    CC_PRIMER_ANIO,
    PREFIJOS,
    anio_de,
    resumir_desde_archivo,
)


# -- derivacion del anio -------------------------------------------------
@pytest.mark.parametrize(
    ("expediente", "esperado"),
    [
        ("5577-2015", "2015"),
        ("61-98", "1998"),
        ("11-87", "1987"),
        ("1920-2003", "2003"),
        ("1-2020", "2020"),
    ],
)
def test_anio_de_expedientes_validos(expediente: str, esperado: str) -> None:
    anio, motivo = anio_de(expediente)
    assert anio == esperado and motivo is None


def test_espacio_al_borde_es_ruido_de_formato_no_errata() -> None:
    """La fuente entrega '1670-2001 '. Tratarlo como error perdia 2.180."""
    assert anio_de("1670-2001 ") == ("2001", None)
    assert anio_de(" 61-98 ") == ("1998", None)


def test_anio_fuera_del_periodo_de_la_corte_no_se_inventa() -> None:
    """La CC existe desde 1986. Un '-69' no es 2069: es una errata.

    Sin este limite se colaba en la serie temporal como si fuera un dato.
    """
    anio, motivo = anio_de("196-69")
    assert anio is None
    assert motivo is not None and "fuera del periodo" in motivo


def test_anio_malformado_se_reporta_no_se_adivina() -> None:
    for expediente in ("1298-200", "1298-20158", "1014-1996a", "sin-guion-aqui"):
        anio, motivo = anio_de(expediente)
        assert anio is None, expediente
        assert motivo, expediente


def test_el_corte_del_siglo_sale_de_cuando_existe_la_corte() -> None:
    assert CC_PRIMER_ANIO == 1986
    assert anio_de("1-86")[0] == "1986"
    assert anio_de("1-99")[0] == "1999"
    assert anio_de("1-00")[0] == "2000"


# -- cobertura de los prefijos -------------------------------------------
def test_los_nueve_prefijos_cubren_y_no_se_solapan() -> None:
    """Todo numero de expediente empieza por un digito del 1 al 9."""
    assert PREFIJOS == ("1", "2", "3", "4", "5", "6", "7", "8", "9")
    assert "0" not in PREFIJOS, "se comprobo que el prefijo 0 devuelve cero"


# -- resumen desde disco -------------------------------------------------
def test_resumir_sin_red(tmp_path: Path) -> None:
    censo = tmp_path / "censo.jsonl"
    filas = [
        {"id": "1", "expedientes": ["100-2015"], "tipoExpediente": "Amparo",
         "fechaSentencia": "2015-01-01T00:00:00Z"},
        {"id": "2", "expedientes": ["200-2015"], "tipoExpediente": "Amparo",
         "fechaSentencia": None},
        # acumulado: un documento con dos expedientes de anios distintos
        {"id": "3", "expedientes": ["300-2016", "400-2017"], "tipoExpediente": "Inconst.",
         "fechaSentencia": "2017-05-05T00:00:00Z"},
    ]
    censo.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
    r = resumir_desde_archivo(censo)
    assert r.documentos_unicos == 3
    assert r.expedientes_unicos == 4
    assert r.por_anio == {"2015": 2, "2016": 1, "2017": 1}
    assert r.sin_fecha_sentencia == 1


def test_un_documento_acumulado_no_se_cuenta_dos_veces(tmp_path: Path) -> None:
    """Un expediente acumulado '1920-2003 y 2014-2003' coincide con el prefijo
    1 y con el 2. Sin deduplicar por id, el universo sale inflado."""
    censo = tmp_path / "censo.jsonl"
    fila = {"id": "42", "expedientes": ["1920-2003", "2014-2003"],
            "tipoExpediente": "Amparo", "fechaSentencia": "2004-03-01T00:00:00Z"}
    censo.write_text(json.dumps(fila) + "\n" + json.dumps(fila) + "\n", encoding="utf-8")
    r = resumir_desde_archivo(censo)
    assert r.documentos_unicos == 1
    assert r.expedientes_unicos == 2
    assert r.por_anio == {"2003": 1}, "un documento cuenta una vez por anio"


def test_el_resumen_lleva_su_advertencia() -> None:
    """Publicado no es lo mismo que dictado, y el resumen debe decirlo."""
    from observatorio_gt.censo import CensoResumen

    advertencia = CensoResumen().advertencia
    assert "PUBLICADAS" in advertencia
    assert "seleccionada" in advertencia
