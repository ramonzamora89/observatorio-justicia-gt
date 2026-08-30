"""Capa deterministica y capa de modelo. Sin red, sin clave, sin gasto."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from observatorio_gt.extractors.deterministic import extraer, literal_desde_sentido
from observatorio_gt.extractors.llm import (
    ExtractionInvalid,
    ModelClient,
    RespuestaLLM,
    extraer_con_modelo,
    resumen_conocido,
)
from observatorio_gt.extractors.prompts import PROMPT_V1
from observatorio_gt.extractors.schema import (
    Extracted,
    LiteralOutcome,
    Provenance,
    ResolutionFacts,
)

DOCUMENTO = (
    "===PAGINA 1===\n"
    "EXPEDIENTE No. 894-98\n"
    "APELACIÓN DE SENTENCIA DE AMPARO\n"
    "CORTE DE CONSTITUCIONALIDAD: Guatemala, tres de marzo de mil novecientos noventa y nueve\n"
    "En apelación y con sus antecedentes se examina la sentencia de diecisiete de noviembre "
    "de mil novecientos noventa y ocho dictada por el Juzgado Segundo de Primera Instancia "
    "del Ramo Civil del departamento de Guatemala, constituido en tribunal de Amparo.\n"
    "===PAGINA 2===\n"
    "POR TANTO: se confirma la sentencia apelada.\n"
)

ATRIBUTOS = {
    "No. Expediente": "894-98",
    "Sentido de la sentencia": "Sin Lugar -Ausencia de agravio",
    "Postulante": "Rodrigo Enrique Franco López",
    "Por tipo de expediente": "Apelación de Sentencia de Amparo",
    "Tribunal de amparo de primer grado": "",
}


# -- capa deterministica -------------------------------------------------
def test_expediente_y_fecha_del_documento() -> None:
    hechos = extraer(DOCUMENTO, {})
    assert hechos.expediente.value == "894-98"
    assert hechos.expediente.provenance is Provenance.DETERMINISTICO
    assert hechos.fecha_resolucion.value == date(1999, 3, 3)


def test_la_fecha_trae_su_cita() -> None:
    """Una conclusion que no puede volver al documento no es una conclusion."""
    hechos = extraer(DOCUMENTO, {})
    evidencia = hechos.fecha_resolucion.evidence
    assert evidencia is not None and evidencia.quote
    assert "mil novecientos noventa y nueve" in evidencia.quote


def test_organo_de_origen() -> None:
    hechos = extraer(DOCUMENTO, {})
    assert hechos.organo_origen.value is not None
    assert "Juzgado Segundo de Primera Instancia" in hechos.organo_origen.value


def test_lo_que_publica_el_portal_se_marca_como_del_portal() -> None:
    hechos = extraer(DOCUMENTO, ATRIBUTOS)
    assert hechos.literal_outcome.value is LiteralOutcome.SIN_LUGAR
    assert hechos.literal_outcome.provenance is Provenance.PORTAL
    assert hechos.postulante.provenance is Provenance.PORTAL


def test_campo_vacio_en_el_portal_no_se_toma_como_valor() -> None:
    """El portal publica el rotulo sin valor; eso no es un dato de contenido."""
    hechos = extraer(DOCUMENTO, ATRIBUTOS)
    assert not hechos.tercero_interesado.consta


@pytest.mark.parametrize(
    ("sentido", "esperado"),
    [
        ("Con Lugar -Derecho de Propiedad", LiteralOutcome.CON_LUGAR),
        ("Sin Lugar -Ausencia de agravio", LiteralOutcome.SIN_LUGAR),
        ("Sin Lugar -Extemporaneidad", LiteralOutcome.SIN_LUGAR),
    ],
)
def test_mapeo_del_sentido_publicado(sentido: str, esperado: LiteralOutcome) -> None:
    assert literal_desde_sentido(sentido) is esperado


def test_sentido_desconocido_no_se_fuerza_a_la_taxonomia() -> None:
    hechos = extraer(DOCUMENTO, {"Sentido de la sentencia": "Algo que no existe"})
    assert not hechos.literal_outcome.consta
    assert "no encaja" in (hechos.literal_outcome.note or "")


def test_los_tres_rotulos_del_mismo_concepto() -> None:
    """El portal escribe 'Sentido de la sentencia', 'Sentido' y 'Fallo'."""
    for rotulo in ("Sentido de la sentencia", "Sentido", "Fallo"):
        hechos = extraer(DOCUMENTO, {rotulo: "Con Lugar -algo"})
        assert hechos.literal_outcome.value is LiteralOutcome.CON_LUGAR, rotulo


# -- capa de modelo ------------------------------------------------------
class ClienteFalso:
    """Cliente de mentira: devuelve lo que se le programe, sin red ni clave."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.llamadas: list[tuple[str, str, dict[str, Any]]] = []

    def extract(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, int]]:
        self.llamadas.append((system, user, schema))
        return self.payload, {"input_tokens": 1000, "output_tokens": 200}


def campo(value: str, *, quote: str | None = "cita textual", conf: float = 0.9) -> dict[str, Any]:
    return {"value": value, "confidence": conf, "page": 2, "quote": quote}


def test_el_modelo_completa_solo_lo_que_falta() -> None:
    hechos = ResolutionFacts(
        literal_outcome=Extracted[LiteralOutcome](
            value=LiteralOutcome.SIN_LUGAR, confidence=1.0, provenance=Provenance.PORTAL
        )
    )
    cliente: ModelClient = ClienteFalso(
        {"literal_outcome": campo("con_lugar"), "ponente": campo("Juan Perez")}
    )
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, hechos, cliente)
    assert resultado.literal_outcome.value is LiteralOutcome.SIN_LUGAR, (
        "una capa mas confiable nunca se sobrescribe"
    )
    assert resultado.literal_outcome.provenance is Provenance.PORTAL
    assert resultado.ponente.value == "Juan Perez"
    assert resultado.ponente.provenance is Provenance.LLM


def test_un_valor_sin_cita_se_descarta() -> None:
    """Si el modelo no puede señalar donde lo leyo, no lo leyo."""
    cliente: ModelClient = ClienteFalso({"ponente": campo("Alguien", quote=None)})
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert not resultado.ponente.consta
    assert "sin citar evidencia" in (resultado.ponente.note or "")


def test_null_es_una_respuesta_valida() -> None:
    cliente: ModelClient = ClienteFalso({"ponente": {"value": None, "confidence": 0.0}})
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert not resultado.ponente.consta
    assert resultado.ponente.note is None


def test_valor_no_convertible_no_se_acepta_a_medias() -> None:
    cliente: ModelClient = ClienteFalso({"fecha_ingreso": campo("el martes pasado")})
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert not resultado.fecha_ingreso.consta
    assert "no convertible" in (resultado.fecha_ingreso.note or "")


def test_respuesta_fuera_del_esquema_se_rechaza() -> None:
    cliente: ModelClient = ClienteFalso({"campo_inventado": "x"})
    with pytest.raises(ExtractionInvalid):
        extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)


def test_magistrados_sin_cita_se_descartan_con_aviso() -> None:
    cliente: ModelClient = ClienteFalso({"magistrados": [{"name": "Ana Lopez"}]})
    resultado, _uso, avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert not resultado.magistrados.consta
    assert any("sin cita" in a for a in avisos)


def test_documento_demasiado_largo_no_se_trunca_en_silencio() -> None:
    cliente = ClienteFalso({})
    _hechos, _uso, avisos = extraer_con_modelo("x" * 200_000, ResolutionFacts(), cliente)
    assert cliente.llamadas == [], "no debe llamarse al modelo con el texto recortado"
    assert any("no se envio al modelo" in a for a in avisos)


def test_al_modelo_se_le_dice_que_ya_se_sabe() -> None:
    hechos = extraer(DOCUMENTO, ATRIBUTOS)
    resumen = resumen_conocido(hechos)
    assert "expediente" in resumen and "894-98" in resumen
    assert "literal_outcome" in resumen


def test_el_prompt_prohibe_valorar_conducta() -> None:
    """CLAUDE.md: no pedir al modelo que determine si un juez es corrupto."""
    system = PROMPT_V1.system.lower()
    assert "no valores la conducta" in system
    assert "corrupcion" in system
    assert "null" in system


def test_el_prompt_esta_versionado_y_con_hash() -> None:
    assert PROMPT_V1.version == "extraccion-cc/v1"
    assert len(PROMPT_V1.sha256) == 64


def test_el_esquema_del_modelo_no_admite_campos_extra() -> None:
    esquema = RespuestaLLM.model_json_schema()
    assert esquema.get("additionalProperties") is False
