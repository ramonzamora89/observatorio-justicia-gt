"""Decide como obtener el texto de cada documento, y deja constancia de por que.

El orden de preferencia de PIPELINE.md es: texto nativo, luego PDF con capa de
texto, y OCR **solo cuando sea necesario**. Aqui "necesario" no se decide por
corazonada sino por dos comprobaciones:

1. **Quien produjo la capa de texto.** Si viene de un escaner o de un OCR ajeno,
   se descarta sin mirarla. La regla heredada es explicita: el OCR del propio
   tribunal puede ser peor que el nuestro, y conservar una capa defectuosa "por
   si acaso" es como se cuelan los nombres partidos en pedazos.
2. **Si el texto se lee como prosa.** La comprobacion de plausibilidad lexica de
   ``quality.py``.

Cuando el OCR tampoco produce texto usable, **no se descarta el documento**: se
marca para revision humana. Un documento que no se pudo leer no es un documento
vacio.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from observatorio_gt.parsers.ocr import ocr_pdf
from observatorio_gt.parsers.pdf import (
    PdfProfile,
    PdfToolError,
    extract_pages,
    full_text,
    join_pages,
    profile,
)
from observatorio_gt.parsers.quality import TextQuality, TextVerdict, assess

PARSER_VERSION = "poppler+ocrmypdf/0.1.0"


class ParseRoute(StrEnum):
    #: La capa de texto del documento sirve.
    CAPA_NATIVA = "capa_nativa"
    #: Habia capa, pero no se leia como prosa. Se rehizo el OCR.
    OCR_POR_CALIDAD = "ocr_por_calidad"
    #: No habia capa de texto en absoluto.
    OCR_POR_AUSENCIA = "ocr_por_ausencia"
    #: La capa venia de un escaner. Se descarto sin mirarla.
    OCR_POR_PRODUCTOR = "ocr_por_productor"
    #: Ni la capa ni el OCR dieron texto usable. Revision humana.
    REVISION_HUMANA = "revision_humana"
    #: No se pudo procesar. No significa que el documento este vacio.
    NO_COMPROBADO = "no_comprobado"


@dataclass(frozen=True)
class ParseResult:
    source_path: Path
    route: ParseRoute
    parser_version: str
    pages: int
    text: str
    quality: TextQuality | None
    quality_antes: TextQuality | None
    pdf_profile: PdfProfile | None
    ocr_path: Path | None = None
    note: str | None = None

    @property
    def usable(self) -> bool:
        return self.route not in (ParseRoute.REVISION_HUMANA, ParseRoute.NO_COMPROBADO)


def parse_document(
    pdf: Path,
    *,
    ocr_dir: Path,
    idioma: str = "spa",
    permitir_ocr: bool = True,
) -> ParseResult:
    """Obtiene el texto de un PDF, con OCR de respaldo si hace falta."""
    try:
        prof = profile(pdf)
    except PdfToolError as exc:
        return ParseResult(
            pdf, ParseRoute.NO_COMPROBADO, PARSER_VERSION, 0, "", None, None, None,
            note=f"pdfinfo fallo: {exc}",
        )

    quality_antes: TextQuality | None = None
    motivo_ocr: ParseRoute | None = None

    if prof.producido_por_escaner:
        # No se mira siquiera: la capa viene de un escaner.
        motivo_ocr = ParseRoute.OCR_POR_PRODUCTOR
    else:
        try:
            paginas = extract_pages(pdf)
        except PdfToolError as exc:
            return ParseResult(
                pdf, ParseRoute.NO_COMPROBADO, PARSER_VERSION, prof.pages or 0, "", None,
                None, prof, note=f"pdftotext fallo: {exc}",
            )
        quality_antes = assess(full_text(paginas))
        if quality_antes.verdict is TextVerdict.USABLE:
            return ParseResult(
                pdf, ParseRoute.CAPA_NATIVA, PARSER_VERSION, len(paginas),
                join_pages(paginas), quality_antes, quality_antes, prof,
            )
        motivo_ocr = (
            ParseRoute.OCR_POR_AUSENCIA
            if quality_antes.verdict is TextVerdict.SIN_CAPA_DE_TEXTO
            else ParseRoute.OCR_POR_CALIDAD
        )

    if not permitir_ocr:
        return ParseResult(
            pdf, ParseRoute.REVISION_HUMANA, PARSER_VERSION, prof.pages or 0, "",
            quality_antes, quality_antes, prof, note="OCR desactivado",
        )

    destino = ocr_dir / f"{pdf.stem}.ocr.pdf"
    try:
        ocr_path = ocr_pdf(pdf, destino, idioma=idioma)
        paginas = extract_pages(ocr_path)
    except PdfToolError as exc:
        return ParseResult(
            pdf, ParseRoute.NO_COMPROBADO, PARSER_VERSION, prof.pages or 0, "",
            quality_antes, quality_antes, prof, note=f"OCR fallo: {exc}",
        )

    quality = assess(full_text(paginas))
    if quality.verdict is not TextVerdict.USABLE:
        return ParseResult(
            pdf, ParseRoute.REVISION_HUMANA, PARSER_VERSION, len(paginas),
            join_pages(paginas), quality, quality_antes, prof, ocr_path=ocr_path,
            note="ni la capa original ni el OCR dieron texto usable: "
                 + "; ".join(quality.razones),
        )
    return ParseResult(
        pdf, motivo_ocr, PARSER_VERSION, len(paginas), join_pages(paginas),
        quality, quality_antes, prof, ocr_path=ocr_path,
    )
