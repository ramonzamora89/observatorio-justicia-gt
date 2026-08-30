"""Perfil de PDF y enrutado del pipeline de parsing. Sin subprocesos reales."""

from __future__ import annotations

from pathlib import Path

import pytest

from observatorio_gt.parsers import pdf as pdfmod
from observatorio_gt.parsers import pipeline as pipemod
from observatorio_gt.parsers.pdf import PageText, PdfProfile, PdfToolError, join_pages
from observatorio_gt.parsers.pipeline import ParseRoute, parse_document
from tests.test_quality import SANO

PDFINFO = """Title:          Sentencia
Pages:          5
Producer:       Microsoft(R) Word 2016
Creator:        Microsoft(R) Word 2016
Page size:      612 x 792 pts
"""


def test_profile_lee_pdfinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdfmod, "_run", lambda *a, **k: PDFINFO)
    prof = pdfmod.profile(Path("x.pdf"))
    assert prof.pages == 5
    assert prof.producer == "Microsoft(R) Word 2016"
    assert prof.producido_por_escaner is False


@pytest.mark.parametrize(
    "producer",
    ["LeanScan 3.5", "ABBYY FineReader 12", "Xerox WorkCentre", "Tesseract 5.3.0"],
)
def test_detecta_capa_hecha_por_escaner(producer: str) -> None:
    """El OCR del propio tribunal puede ser peor que el nuestro."""
    prof = PdfProfile(Path("x.pdf"), 3, producer, None)
    assert prof.producido_por_escaner


def test_pdf_sin_productor_no_se_acusa_de_escaner() -> None:
    assert not PdfProfile(Path("x.pdf"), 3, None, None).producido_por_escaner


def test_paginas_se_conservan_citables() -> None:
    texto = join_pages([PageText(1, "primera"), PageText(2, "segunda")])
    assert "===PAGINA 1===" in texto
    assert "===PAGINA 2===" in texto


# -- enrutado ------------------------------------------------------------
def routes(monkeypatch: pytest.MonkeyPatch, *, producer: str | None, texto: str,
           texto_ocr: str | None = None) -> object:
    monkeypatch.setattr(
        pipemod, "profile", lambda p: PdfProfile(p, 5, producer, None)
    )
    estado = {"ocr": False}

    def fake_extract(path: Path, **kw: object) -> list[PageText]:
        contenido = texto_ocr if estado["ocr"] else texto
        return [PageText(1, contenido or "")]

    def fake_ocr(origen: Path, destino: Path, **kw: object) -> Path:
        if texto_ocr is None:
            raise PdfToolError("ocrmypdf fallo")
        estado["ocr"] = True
        return destino

    monkeypatch.setattr(pipemod, "extract_pages", fake_extract)
    monkeypatch.setattr(pipemod, "ocr_pdf", fake_ocr)
    return parse_document(Path("x.pdf"), ocr_dir=Path("/tmp/ocr"))


def test_capa_nativa_buena_no_se_toca(monkeypatch: pytest.MonkeyPatch) -> None:
    r = routes(monkeypatch, producer="Microsoft Word", texto=SANO)
    assert r.route is ParseRoute.CAPA_NATIVA  # type: ignore[attr-defined]
    assert r.ocr_path is None  # type: ignore[attr-defined]


def test_capa_de_escaner_se_descarta_sin_mirarla(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aunque el texto del escaner fuera perfecto, se rehace igual."""
    r = routes(monkeypatch, producer="LeanScan 3.5", texto=SANO, texto_ocr=SANO)
    assert r.route is ParseRoute.OCR_POR_PRODUCTOR  # type: ignore[attr-defined]
    assert r.quality_antes is None  # type: ignore[attr-defined]


def test_sin_capa_de_texto_va_a_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    r = routes(monkeypatch, producer="Word", texto="", texto_ocr=SANO)
    assert r.route is ParseRoute.OCR_POR_AUSENCIA  # type: ignore[attr-defined]


def test_capa_defectuosa_va_a_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    corrupto = SANO.translate(str.maketrans("", "", "mgMG"))
    r = routes(monkeypatch, producer="Word", texto=corrupto, texto_ocr=SANO)
    assert r.route is ParseRoute.OCR_POR_CALIDAD  # type: ignore[attr-defined]
    assert r.quality_antes is not None  # type: ignore[attr-defined]


def test_si_el_ocr_tampoco_sirve_va_a_revision_humana(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un documento que no se pudo leer no es un documento vacio."""
    r = routes(monkeypatch, producer="Word", texto="", texto_ocr="basura")
    assert r.route is ParseRoute.REVISION_HUMANA  # type: ignore[attr-defined]
    assert not r.usable  # type: ignore[attr-defined]


def test_ocr_que_falla_es_no_comprobado(monkeypatch: pytest.MonkeyPatch) -> None:
    r = routes(monkeypatch, producer="Word", texto="", texto_ocr=None)
    assert r.route is ParseRoute.NO_COMPROBADO  # type: ignore[attr-defined]
    assert "OCR fallo" in (r.note or "")  # type: ignore[attr-defined]


def test_sin_ocr_se_marca_para_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipemod, "profile", lambda p: PdfProfile(p, 5, "Word", None))
    monkeypatch.setattr(pipemod, "extract_pages", lambda p, **k: [PageText(1, "")])
    r = parse_document(Path("x.pdf"), ocr_dir=Path("/tmp/ocr"), permitir_ocr=False)
    assert r.route is ParseRoute.REVISION_HUMANA
