from __future__ import annotations

import pytest

from observatorio_gt.postulante import RESIDUAL, clasificar, promovente


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        (
            "en la acción constitucional de amparo promovida por Grupo Eco, Sociedad Anónima, "
            "por medio del Mandatario Especial, contra la Sala Tercera.",
            "Grupo Eco, Sociedad Anónima",
        ),
        (
            "en la acción constitucional de amparo promovida porInter, Sociedad Anónima, "
            "por medio de su gerente, contra laSala Tercera.",
            "Inter, Sociedad Anónima",
        ),
        (
            "en la acción constitucional de amparo que promovió la Comisión Internacional "
            "contra la Impunidad en Guatemala por medio de sus Mandatarias, contra la Sala.",
            "la Comisión Internacional contra la Impunidad en Guatemala",
        ),
        (
            "la acción constitucional homónima que Pantaleón, Sociedad Anónima, promovió contra "
            "la Comisión Nacional de Energía Eléctrica.",
            "Pantaleón, Sociedad Anónima",
        ),
        (
            "en la acción de amparo promovida por Delfina Olivares Retana, quien actuó con la "
            "dirección del abogado David Sentes Luna.",
            "Delfina Olivares Retana",
        ),
    ],
)
def test_promovente(texto: str, esperado: str) -> None:
    assert promovente(texto) == esperado


def test_promovido_va_antes_que_interpuesto() -> None:
    """«interpuesto por» puede ser el recurso de otra parte, no el amparo."""
    texto = (
        "Se conoce el recurso de apelación interpuesto por el Ministerio Público contra la "
        "sentencia dictada en el amparo promovido por Claudio Ramírez Pérez contra el Juez."
    )
    assert promovente(texto) == "Claudio Ramírez Pérez"


def test_sin_forma_reconocible_es_none() -> None:
    assert promovente("Sentencia sin el párrafo de apertura habitual.") is None


@pytest.mark.parametrize(
    ("nombre", "categoria"),
    [
        ("el Ministerio Público", "Ministerio Público"),
        ("Leopoldo Liu González, en calidad de Fiscal Especial del Ministerio Público",
         "Ministerio Público"),
        ("el Estado de Guatemala", "PGN / Estado"),
        ("el Banco de Guatemala", "Otra entidad pública"),
        ("Banco Agromercantil de Guatemala, Sociedad Anónima", "Empresa"),
        ("la Cámara de Industria de Guatemala", "Gremial / cámara"),
        ("la Asociación de la Industria del Vestuario y Textiles", "Gremial / cámara"),
        ("Unipharm, S. A.", "Empresa"),
        ("Amelia Galicia Alvizures", RESIDUAL),
        (None, "Vacío"),
    ],
)
def test_clasificar(nombre: str | None, categoria: str) -> None:
    c = clasificar(nombre)
    assert c.categoria == categoria
    assert (c.coincidencia is None) == (categoria in (RESIDUAL, "Vacío"))
