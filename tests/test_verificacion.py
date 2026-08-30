"""Verificacion de evidencia: que la cita exista de verdad en el documento.

Un campo con una cita *parecida* al documento es tan peligroso como uno
inventado, y se ve igual de bien en un JSON.
"""

from __future__ import annotations

from observatorio_gt.extractors.schema import (
    Citation,
    Evidence,
    Extracted,
    JudicialOfficer,
    Provenance,
    ResolutionFacts,
)
from observatorio_gt.extractors.verificacion import (
    VerificationStatus,
    aparece,
    marcar_no_verificados,
    normalizar,
    verificar,
)

# Pie de firmas real: partido por un salto de pagina, como en el corpus.
DOCUMENTO = (
    "===PAGINA 3===\n"
    "III) Notifíquese y con certificación de lo resuelto devuélvase los antecedentes.\n\n"
    "JOSE ARTURO SIERRA GONZALEZ\n\nPRESIDENTE A.I.\n\n"
    "===PAGINA 4===\n"
    "LUIS FELIPE SAENZ JUAREZ\n\nMAGISTRADO\n\n"
    "ALEJANDRO MALDONADO AGUIRRE\n\nMAGISTRADO\n"
    "D) Remisión de antecedentes: expediente del amparo trescientos ochenta y nueve.\n"
)


def hechos_con_magistrados(*nombres: str) -> ResolutionFacts:
    return ResolutionFacts(
        magistrados=Extracted[list[JudicialOfficer]](
            value=[JudicialOfficer(name=n) for n in nombres],
            confidence=0.9,
            provenance=Provenance.LLM,
            evidence=Evidence(page=3, quote="bloque de firmas"),
        )
    )


def test_normalizar_quita_marcas_de_pagina_y_tildes() -> None:
    assert "===pagina" not in normalizar(DOCUMENTO)
    assert "notifiquese" in normalizar(DOCUMENTO)


def test_aparece_ignora_saltos_de_linea_y_tildes() -> None:
    doc = normalizar(DOCUMENTO)
    assert aparece("Notifíquese y con certificación", doc)
    assert aparece("notifiquese  y  con  certificacion", doc)


def test_los_nombres_se_comprueban_uno_por_uno() -> None:
    """El bloque de firmas viene partido por un salto de pagina.

    Exigir que aparezca contiguo descartaria extracciones correctas; exigir cada
    nombre entero sigue atrapando a un magistrado inventado.
    """
    resultados = verificar(
        hechos_con_magistrados(
            "JOSE ARTURO SIERRA GONZALEZ", "LUIS FELIPE SAENZ JUAREZ"
        ),
        DOCUMENTO,
    )
    (magistrados,) = [r for r in resultados if r.field == "magistrados"]
    assert magistrados.status is VerificationStatus.VERIFICADA


def test_un_magistrado_inventado_se_detecta() -> None:
    """Un nombre que no aparece es una persona que no firmo."""
    resultados = verificar(
        hechos_con_magistrados("JOSE ARTURO SIERRA GONZALEZ", "PERSONA INEXISTENTE"),
        DOCUMENTO,
    )
    (magistrados,) = [r for r in resultados if r.field == "magistrados"]
    assert magistrados.status is VerificationStatus.NO_ENCONTRADA
    assert "PERSONA INEXISTENTE" in (magistrados.detail or "")


def test_cita_que_no_esta_en_el_documento() -> None:
    hechos = ResolutionFacts(
        ponente=Extracted[str](
            value="Alguien",
            confidence=0.9,
            provenance=Provenance.LLM,
            evidence=Evidence(page=1, quote="una frase que el documento no dice"),
        )
    )
    (resultado,) = [r for r in verificar(hechos, DOCUMENTO) if r.field == "ponente"]
    assert resultado.status is VerificationStatus.NO_ENCONTRADA


def test_valor_sin_cita_se_marca_como_sin_evidencia() -> None:
    hechos = ResolutionFacts(
        ponente=Extracted[str](value="Alguien", confidence=0.9, provenance=Provenance.LLM)
    )
    (resultado,) = [r for r in verificar(hechos, DOCUMENTO) if r.field == "ponente"]
    assert resultado.status is VerificationStatus.SIN_EVIDENCIA


def test_lo_que_publica_el_portal_no_se_verifica_contra_el_texto() -> None:
    """El portal es otra fuente: su dato no tiene por que estar en el PDF."""
    hechos = ResolutionFacts(
        postulante=Extracted[str](
            value="Juan Perez", confidence=1.0, provenance=Provenance.PORTAL
        )
    )
    assert [r for r in verificar(hechos, DOCUMENTO) if r.field == "postulante"] == []


def test_citas_jurisprudenciales_se_cotejan() -> None:
    hechos = ResolutionFacts(
        citas=Extracted[list[Citation]](
            value=[Citation(citation_text="expediente del amparo trescientos ochenta y nueve")],
            confidence=0.7,
            provenance=Provenance.LLM,
        )
    )
    (resultado,) = [r for r in verificar(hechos, DOCUMENTO) if r.field == "citas"]
    assert resultado.status is VerificationStatus.VERIFICADA


def test_los_no_verificados_se_marcan_pero_no_se_borran() -> None:
    """Que el modelo proponga sin respaldo es una medida de su fiabilidad."""
    hechos = ResolutionFacts(
        ponente=Extracted[str](
            value="Alguien",
            confidence=0.9,
            provenance=Provenance.LLM,
            evidence=Evidence(quote="frase inexistente"),
        )
    )
    avisos = marcar_no_verificados(hechos, verificar(hechos, DOCUMENTO))
    assert hechos.ponente.value == "Alguien", "no se borra"
    assert "EVIDENCIA" in (hechos.ponente.note or "")
    assert avisos and "ponente" in avisos[0]


def test_un_guion_partido_por_el_salto_de_linea_no_invalida_la_cita() -> None:
    """`pdftotext` deja «setenta y dos-\\nnoventa» como «setenta y dos- noventa».

    Quien cita el pasaje escribe «dos-noventa». Exigir ese espacio marcaba como
    inventada una cita textualmente fiel.
    """
    doc = normalizar("en el expediente setenta y dos- noventa y dos, consta que")
    assert aparece("expediente setenta y dos-noventa y dos", doc)


def test_la_licencia_del_guion_no_afloja_lo_demas() -> None:
    """Sigue sin aceptar sinonimos, reordenamientos ni elisiones."""
    doc = normalizar(DOCUMENTO)
    assert not aparece("Notifíquese ... devuélvase los antecedentes", doc), "sin elisiones"
    assert not aparece("devuélvase los antecedentes y notifíquese", doc), "sin reordenar"
    assert not aparece("SIERRA GONZALES", doc), "sin ortografia distinta"


# -- regla heredada: un termino puede contarse desde el nombre del organo --
def test_campos_tematicos_y_campos_de_organo_no_son_lo_mismo() -> None:
    """Buscar «antejuicio» en toda la ficha daba 2.136; 2.036 eran el nombre de
    un tribunal («Cámara de Amparo y Antejuicio»), no casos de antejuicio."""
    from observatorio_gt.atributos import CAMPOS_DE_ORGANO, CAMPOS_TEMATICOS

    assert "Tribunal de amparo de primer grado" in CAMPOS_DE_ORGANO
    assert "Autoridad impugnada" in CAMPOS_DE_ORGANO
    assert "Por tipo de antecedente" in CAMPOS_TEMATICOS
    assert not (set(CAMPOS_TEMATICOS) & set(CAMPOS_DE_ORGANO)), "no se solapan"


def test_contar_materia_solo_mira_campos_tematicos() -> None:
    from observatorio_gt.atributos import materia_aparece

    ficha_falsa = {"Tribunal de amparo de primer grado":
                   "Corte Suprema de Justicia -Cámara de Amparo y Antejuicio"}
    ficha_real = {"Por tipo de antecedente": "Penal -Diligencias de antejuicio"}
    assert not materia_aparece(ficha_falsa, "antejuicio")
    assert materia_aparece(ficha_real, "antejuicio")
