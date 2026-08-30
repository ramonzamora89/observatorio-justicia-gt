"""Lectura de PDF: perfil del archivo y extraccion de texto por pagina.

Se usan las herramientas de poppler (``pdfinfo``, ``pdftotext``, ``pdftoppm``)
en vez de una biblioteca embebida: son las mismas que se usan para cotejar a
mano, asi que lo que ve el pipeline es lo que ve quien revisa.

**El texto se conserva por pagina.** Una cita sin numero de pagina no es
verificable, y ``evidence_spans`` del modelo de datos exige la pagina.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

#: Productores de capa de texto que delatan un escaner. Regla heredada: el OCR
#: del propio tribunal puede ser peor que el nuestro, y un PDF con texto no es
#: un PDF con texto usable.
PRODUCTORES_DE_ESCANER: tuple[str, ...] = (
    "leanscan", "scanner", "scansnap", "xerox", "kyocera", "ricoh", "canon",
    "epson", "hp digital sending", "toshiba", "sharp", "abbyy", "finereader",
    "tesseract", "ocrmypdf",
)


class PdfToolError(RuntimeError):
    """Una herramienta de poppler fallo o no esta instalada."""


@dataclass(frozen=True)
class PdfProfile:
    path: Path
    pages: int | None
    producer: str | None
    creator: str | None

    @property
    def producido_por_escaner(self) -> bool:
        """¿La capa de texto la hizo un escaner o un OCR ajeno?"""
        campos = " ".join(x.lower() for x in (self.producer, self.creator) if x)
        return any(marca in campos for marca in PRODUCTORES_DE_ESCANER)


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def _run(cmd: list[str], timeout: float = 120.0) -> str:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise PdfToolError(f"herramienta no encontrada: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise PdfToolError(f"{cmd[0]} excedio {timeout}s") from exc
    if done.returncode != 0:
        raise PdfToolError(f"{cmd[0]} salio con codigo {done.returncode}: {done.stderr[:300]}")
    return done.stdout


def profile(path: Path) -> PdfProfile:
    salida = _run(["pdfinfo", str(path)])
    campos: dict[str, str] = {}
    for linea in salida.splitlines():
        clave, _, valor = linea.partition(":")
        campos[clave.strip().lower()] = valor.strip()
    paginas: int | None
    try:
        paginas = int(campos.get("pages", ""))
    except ValueError:
        paginas = None
    return PdfProfile(
        path=path,
        pages=paginas,
        producer=campos.get("producer") or None,
        creator=campos.get("creator") or None,
    )


def extract_pages(path: Path, *, layout: bool = True) -> list[PageText]:
    """Texto por pagina. ``pdftotext`` separa paginas con salto de pagina."""
    cmd = ["pdftotext"]
    if layout:
        cmd.append("-layout")
    cmd += [str(path), "-"]
    crudo = _run(cmd)
    partes = crudo.split("\f")
    if partes and not partes[-1].strip():
        partes.pop()
    return [PageText(page=i, text=t) for i, t in enumerate(partes, start=1)]


def join_pages(pages: list[PageText]) -> str:
    """Une conservando un marcador de pagina citable."""
    return "\n".join(f"===PAGINA {p.page}===\n{p.text}" for p in pages)


def full_text(pages: list[PageText]) -> str:
    return "\n".join(p.text for p in pages)
