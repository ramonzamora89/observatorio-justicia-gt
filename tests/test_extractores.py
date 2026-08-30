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
from observatorio_gt.extractors.prompts import PROMPT_ACTUAL as PROMPT_V1
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


def test_el_prompt_exige_cita_contigua_y_literal() -> None:
    """El modelo eligio elidir el centro con puntos suspensivos; el cotejo lo
    rechazo. Pedirlo explicitamente evita gastar la llamada."""
    system = PROMPT_V1.system.lower()
    assert "contiguo" in system
    assert "puntos suspensivos" in system


def test_el_prompt_prohibe_valorar_conducta() -> None:
    """CLAUDE.md: no pedir al modelo que determine si un juez es corrupto."""
    system = PROMPT_V1.system.lower()
    assert "no valores la conducta" in system
    assert "corrupcion" in system
    assert "null" in system


def test_el_prompt_esta_versionado_y_con_hash() -> None:
    assert PROMPT_V1.version.startswith("extraccion-cc/v")
    assert len(PROMPT_V1.sha256) == 64


def test_el_esquema_del_modelo_no_admite_campos_extra() -> None:
    esquema = RespuestaLLM.model_json_schema()
    assert esquema.get("additionalProperties") is False


# -- carga de credenciales -----------------------------------------------
def test_env_carga_nombres_y_no_devuelve_valores(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """Un modulo que maneja claves no debe devolverlas ni registrarlas."""
    from observatorio_gt.secrets import cargar_env

    env = tmp_path / ".env"
    env.write_text(
        "# comentario\nANTHROPIC_API_KEY=sk-ant-secreto\nOTRA='valor'\n", encoding="utf-8"
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OTRA", raising=False)
    cargadas = cargar_env(env)
    assert set(cargadas) == {"ANTHROPIC_API_KEY", "OTRA"}
    assert "sk-ant-secreto" not in str(cargadas)


def test_lo_explicito_del_entorno_gana_sobre_el_archivo(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    from observatorio_gt.secrets import cargar_env

    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=del-archivo\n", encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "del-entorno")
    assert cargar_env(env) == []
    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "del-entorno"


def test_sin_archivo_no_falla(tmp_path) -> None:
    from observatorio_gt.secrets import cargar_env

    assert cargar_env(tmp_path / "no-existe") == []


def test_el_esquema_que_viaja_no_lleva_cotas_numericas() -> None:
    """La API responde 400: "For 'number' type, properties maximum, minimum
    are not supported". La validacion del rango se queda de nuestro lado."""
    import json

    from observatorio_gt.extractors.llm import esquema_para_api

    limpio = json.dumps(esquema_para_api(RespuestaLLM.model_json_schema()))
    assert "minimum" not in limpio and "maximum" not in limpio
    # y la funcion quita las cotas venga de donde venga el esquema
    con_cotas = {"properties": {"c": {"type": "number", "minimum": 0, "maximum": 1}}}
    assert esquema_para_api(con_cotas) == {"properties": {"c": {"type": "number"}}}


def test_confianza_fuera_de_rango_se_acota_y_se_deja_constancia() -> None:
    """Que el modelo se salga del rango es en si un dato, no un detalle."""
    from observatorio_gt.extractors.llm import acotar_confianza

    assert acotar_confianza(0.9) == (0.9, None)
    valor, aviso = acotar_confianza(1.4)
    assert valor == 1.0 and aviso and "fuera de rango" in aviso
    valor, aviso = acotar_confianza(-0.2)
    assert valor == 0.0 and aviso is not None


def test_una_confianza_absurda_no_tumba_la_extraccion() -> None:
    cliente: ModelClient = ClienteFalso({"ponente": campo("Ana Lopez", conf=1.7)})
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert resultado.ponente.value == "Ana Lopez"
    assert resultado.ponente.confidence == 1.0
    assert "fuera de rango" in (resultado.ponente.note or "")


# -- conversion: el modelo copia literal, el codigo normaliza -------------
def test_fecha_en_letras_del_modelo_se_convierte() -> None:
    """El prompt le prohibe normalizar. Exigirle ISO era contradecirlo."""
    cliente: ModelClient = ClienteFalso(
        {"fecha_ingreso": campo("diez de diciembre de mil novecientos noventa y seis")}
    )
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert resultado.fecha_ingreso.value == date(1996, 12, 10)


def test_fecha_iso_tambien_se_acepta() -> None:
    cliente: ModelClient = ClienteFalso({"fecha_ingreso": campo("1996-12-10")})
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert resultado.fecha_ingreso.value == date(1996, 12, 10)


@pytest.mark.parametrize(
    ("clausula", "esperado"),
    [
        ("I) deniega el amparo solicitado; II) condena en costas", LiteralOutcome.DENEGADO),
        ("confirma la sentencia venida en grado", LiteralOutcome.CONFIRMADO),
        ("I) sin lugar los recursos de apelación", LiteralOutcome.SIN_LUGAR),
        ("por notoriamente improcedente, deniega", LiteralOutcome.RECHAZADO),
    ],
)
def test_clausula_resolutiva_se_traduce_a_la_taxonomia(
    clausula: str, esperado: LiteralOutcome
) -> None:
    cliente: ModelClient = ClienteFalso({"literal_outcome": campo(clausula)})
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, ResolutionFacts(), cliente)
    assert resultado.literal_outcome.value is esperado


def test_gana_el_termino_que_resuelve_el_fondo() -> None:
    """«I) deniega el amparo; II) condena en costas»: manda lo primero."""
    from observatorio_gt.extractors.deterministic import literal_desde_resolutivo

    assert literal_desde_resolutivo(
        "I) deniega el amparo; II) confirma lo demas"
    ) is LiteralOutcome.DENEGADO


def test_el_efecto_procesal_no_se_le_pregunta_al_modelo() -> None:
    """Es taxonomia, no lectura: depende de si habia decision inferior."""
    from observatorio_gt.extractors.schema import NormalizedEffect

    cliente: ModelClient = ClienteFalso(
        {
            "literal_outcome": campo("confirma la sentencia apelada"),
            "normalized_effect": campo("confirma_con_modificacion"),
        }
    )
    hechos = ResolutionFacts(
        tipo_proceso=Extracted[str](
            value="Apelación de Sentencia de Amparo",
            confidence=1.0,
            provenance=Provenance.PORTAL,
        )
    )
    resultado, _uso, _avisos = extraer_con_modelo(DOCUMENTO, hechos, cliente)
    assert resultado.normalized_effect.value is NormalizedEffect.MANTIENE_DECISION_INFERIOR
    assert resultado.normalized_effect.provenance is Provenance.DETERMINISTICO


def test_sin_revision_previa_el_efecto_queda_sin_derivar() -> None:
    """En amparo en unica instancia no hay decision inferior que mantener."""
    from observatorio_gt.extractors.deterministic import efecto_procesal

    assert efecto_procesal(LiteralOutcome.CONFIRMADO, "Amparo en Única Instancia") is None


def test_la_respuesta_cruda_se_conserva() -> None:
    """Corregir la conversion no debe obligar a volver a pagarle al modelo."""
    from observatorio_gt.extractors.llm import extraer_con_modelo_crudo

    payload = {"ponente": campo("Ana Lopez"), "campo_futuro": None}
    cliente: ModelClient = ClienteFalso({"ponente": campo("Ana Lopez")})
    _h, _u, _a, crudo = extraer_con_modelo_crudo(DOCUMENTO, ResolutionFacts(), cliente)
    assert crudo == {"ponente": campo("Ana Lopez")}
    assert payload  # el crudo es lo que devolvio el cliente, sin recortar


def test_reprocesar_no_necesita_al_modelo() -> None:
    """`aplicar_respuesta` es pura: la misma que usa `extract reprocess`.

    Corregir la conversion de un campo debe poder aplicarse sobre lo que el
    modelo ya dijo, sin volver a pagarlo.
    """
    from observatorio_gt.extractors.llm import aplicar_respuesta

    crudo = {"fecha_ingreso": campo("diez de diciembre de mil novecientos noventa y seis")}
    hechos, _avisos = aplicar_respuesta(crudo, ResolutionFacts())
    assert hechos.fecha_ingreso.value == date(1996, 12, 10)


@pytest.mark.parametrize(
    ("literal", "esperado"),
    [
        (LiteralOutcome.SIN_LUGAR, "mantiene_decision_inferior"),
        (LiteralOutcome.DENEGADO, "mantiene_decision_inferior"),
        (LiteralOutcome.CONFIRMADO, "mantiene_decision_inferior"),
        (LiteralOutcome.CON_LUGAR, "altera_decision_inferior"),
        (LiteralOutcome.REVOCADO, "altera_decision_inferior"),
    ],
)
def test_efecto_en_instancia_de_revision(literal: LiteralOutcome, esperado: str) -> None:
    """Rechazar el recurso deja en pie lo recurrido; acogerlo lo altera."""
    from observatorio_gt.extractors.deterministic import efecto_procesal

    efecto = efecto_procesal(literal, "Apelación de Sentencia de Amparo")
    assert efecto is not None and efecto.value == esperado


def test_lo_que_no_es_inequivoco_se_queda_sin_valor() -> None:
    """Completar la taxonomia a ojo seria convertir inferencia en hecho."""
    from observatorio_gt.extractors.deterministic import efecto_procesal

    assert efecto_procesal(LiteralOutcome.OTRO, "Apelación de Sentencia de Amparo") is None
    assert efecto_procesal(None, "Apelación de Sentencia de Amparo") is None
