"""Carga de credenciales desde `.env`, que nunca se versiona.

El SDK de Anthropic lee la clave del entorno. En una sesion donde las variables
no persisten entre comandos, o en una maquina nueva, `.env` es el lugar
razonable para dejarla una vez.

**Nada de este modulo escribe, registra ni devuelve el valor de una clave.**
Solo la pone en el entorno del proceso. `.gitignore` ya excluye `.env`.
"""

from __future__ import annotations

import os
from pathlib import Path

CLAVES_CONOCIDAS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")


def cargar_env(ruta: Path = Path(".env")) -> list[str]:
    """Carga `.env` en el entorno. Devuelve los NOMBRES cargados, nunca los valores.

    Una variable ya presente en el entorno gana: lo explicito manda sobre el
    archivo.
    """
    if not ruta.exists():
        return []
    cargadas: list[str] = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or "=" not in limpia:
            continue
        nombre, _, valor = limpia.partition("=")
        nombre = nombre.strip().removeprefix("export ").strip()
        valor = valor.strip().strip("'\"")
        if not nombre or nombre in os.environ:
            continue
        os.environ[nombre] = valor
        cargadas.append(nombre)
    return cargadas


def credencial_disponible() -> bool:
    return any(os.environ.get(c) for c in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"))
