"""Prueba de OCR de punta a punta, contra verdad de referencia.

Opt-in: `uv run pytest -m ocr`. Necesita ocrmypdf, tesseract con espanol,
poppler y un documento del corpus en `data/raw/`.

**Por que se fabrica el caso.** Los 20 documentos del corpus tienen capa de texto
nativa de Word: ninguno necesita OCR. Probar OCR sobre ellos no probaria nada.
Asi que se rasteriza uno bueno hasta convertirlo en imagen -- lo que hace un
escaner -- y se mide el OCR **contra el texto del original**, que es la verdad de
referencia. Sin ese contraste, "el OCR funciono" es una impresion.
"""

from __future__ import annotations

import difflib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from observatorio_gt.parsers.pdf import extract_pages, full_text
from observatorio_gt.parsers.pipeline import ParseRoute, parse_document
from observatorio_gt.parsers.quality import TextVerdict, assess

pytestmark = pytest.mark.ocr

CORPUS = Path("data/raw")


def herramientas_disponibles() -> bool:
    if not all(shutil.which(x) for x in ("ocrmypdf", "pdftotext", "pdftoppm", "tesseract")):
        return False
    langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    return "spa" in langs.stdout.split()


@pytest.fixture(scope="module")
def documento_real() -> Path:
    if not herramientas_disponibles():
        pytest.skip("faltan ocrmypdf/poppler/tesseract-spa")
    pdfs = sorted(CORPUS.rglob("*.pdf"))
    if not pdfs:
        pytest.skip("no hay corpus en data/raw (ejecuta 'obsgt cc-ptmp discover')")
    return pdfs[0]


@pytest.fixture(scope="module")
def escaneado(documento_real: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Rasteriza un PDF bueno hasta dejarlo sin capa de texto."""
    PIL = pytest.importorskip("PIL.Image")
    destino = tmp_path_factory.mktemp("ocr") / "escaneado.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["pdftoppm", "-r", "200", "-gray", "-jpeg", "-jpegopt", "quality=85",
             str(documento_real), str(Path(tmp) / "p")],
            check=True,
        )
        imgs = sorted(Path(tmp).glob("p-*.jpg"))
        hojas = [PIL.open(i).convert("L") for i in imgs]
        hojas[0].save(destino, save_all=True, append_images=hojas[1:], resolution=200.0)
    return destino


@pytest.fixture(scope="module")
def verdad(documento_real: Path) -> str:
    return full_text(extract_pages(documento_real))


def test_el_documento_rasterizado_no_tiene_capa_de_texto(escaneado: Path) -> None:
    q = assess(full_text(extract_pages(escaneado)))
    assert q.verdict is TextVerdict.SIN_CAPA_DE_TEXTO
    assert q.necesita_ocr


def test_el_pipeline_lo_enruta_a_ocr_y_recupera_texto_usable(
    escaneado: Path, tmp_path: Path
) -> None:
    resultado = parse_document(escaneado, ocr_dir=tmp_path)
    assert resultado.route is ParseRoute.OCR_POR_AUSENCIA
    assert resultado.usable
    assert resultado.quality is not None
    assert resultado.quality.verdict is TextVerdict.USABLE
    assert "===PAGINA 1===" in resultado.text


def test_exactitud_del_ocr_contra_la_verdad_de_referencia(
    escaneado: Path, verdad: str, tmp_path: Path
) -> None:
    """Medido el 29-08-2026: 99.8% de recuperacion de palabras."""
    resultado = parse_document(escaneado, ocr_dir=tmp_path)
    tokenizar = lambda t: re.findall(r"[\w\-áéíóúüñÁÉÍÓÚÑ]+", t.lower())  # noqa: E731
    esperado = tokenizar(verdad)
    obtenido = tokenizar(resultado.text.replace("===PAGINA", " "))
    sm = difflib.SequenceMatcher(None, esperado, obtenido, autojunk=False)
    recuperacion = sum(b.size for b in sm.get_matching_blocks()) / len(esperado)
    assert recuperacion > 0.95, f"solo {recuperacion:.1%} de palabras recuperadas"


def test_el_numero_de_expediente_sobrevive_al_ocr(
    escaneado: Path, verdad: str, tmp_path: Path
) -> None:
    """Un expediente mal leido es un documento atribuido a otra persona."""
    expedientes = set(re.findall(r"\b\d{1,5}-(?:19|20)?\d{2}\b", verdad))
    if not expedientes:
        pytest.skip("el documento de prueba no trae numero de expediente legible")
    resultado = parse_document(escaneado, ocr_dir=tmp_path)
    assert expedientes & set(re.findall(r"\b\d{1,5}-(?:19|20)?\d{2}\b", resultado.text))


def test_no_se_pierden_paginas(escaneado: Path, documento_real: Path, tmp_path: Path) -> None:
    resultado = parse_document(escaneado, ocr_dir=tmp_path)
    assert resultado.pages == len(extract_pages(documento_real))
