"""OCR de respaldo, para cuando la capa de texto no sirve o no existe.

Se usa ``ocrmypdf`` con ``--force-ocr``, que descarta cualquier capa de texto
previa y rehace el reconocimiento sobre la imagen. Es deliberado: la regla
heredada dice que el OCR del propio tribunal puede ser peor que el nuestro, y
conservar una capa defectuosa "por si acaso" es como se cuelan los nombres
partidos en pedazos.

El resultado **no reemplaza al original**. El PDF de ``data/raw/`` es inmutable;
el OCR se escribe aparte.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from observatorio_gt.parsers.pdf import PdfToolError

IDIOMA_POR_DEFECTO = "spa"


def ocr_pdf(
    origen: Path,
    destino: Path,
    *,
    idioma: str = IDIOMA_POR_DEFECTO,
    timeout: float = 900.0,
) -> Path:
    """Rehace el OCR de ``origen`` y lo escribe en ``destino``."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--language", idioma,
        "--output-type", "pdf",
        "--quiet",
        str(origen),
        str(destino),
    ]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise PdfToolError("ocrmypdf no esta instalado") from exc
    except subprocess.TimeoutExpired as exc:
        raise PdfToolError(f"ocrmypdf excedio {timeout}s en {origen.name}") from exc
    if done.returncode != 0:
        raise PdfToolError(f"ocrmypdf fallo en {origen.name}: {done.stderr[:400]}")
    return destino
