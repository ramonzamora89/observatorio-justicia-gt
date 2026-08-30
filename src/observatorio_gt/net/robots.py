"""Lectura y evaluacion de robots.txt.

Dos decisiones que no son obvias:

1. **robots.txt se descarga con NUESTRO user-agent.** ``RobotFileParser.read()``
   usa el user-agent de ``urllib``, y si el sitio se lo rechaza el parser niega
   todo en silencio: el collector concluye "prohibido" sin que nadie lo haya
   prohibido. Aqui se baja con el cliente del proyecto y se le entrega el cuerpo
   ya leido a ``parse()``.
2. **Falla cerrado.** Si robots.txt no se puede leer, ``allowed`` es ``False`` y
   la nota dice "no comprobado". No se asume permiso por no haber podido mirar.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from observatorio_gt.manifest import RobotsDecision


def _robots_url_for(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def parse_directives(body: str, user_agent: str) -> tuple[float | None, str | None]:
    """Extrae ``Crawl-delay`` y ``Content-Signal`` del grupo aplicable.

    ``RobotFileParser`` ignora ``Content-Signal`` por completo, y es justamente
    el campo donde la CC expresa ``ai-train=no``. Se lee aparte, con un parser
    minimo: se acumulan los user-agents de cada grupo y se toman las directivas
    del grupo que aplica a nuestro UA, con ``*`` como respaldo.
    """
    ua = user_agent.lower()
    groups: list[tuple[list[str], dict[str, str]]] = []
    current_agents: list[str] = []
    current: dict[str, str] = {}
    previous_was_agent = False

    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if not previous_was_agent and current_agents:
                groups.append((current_agents, current))
                current_agents, current = [], {}
            current_agents.append(value.lower())
            previous_was_agent = True
            continue
        previous_was_agent = False
        if current_agents:
            current[key] = value
    if current_agents:
        groups.append((current_agents, current))

    specific: dict[str, str] | None = None
    wildcard: dict[str, str] | None = None
    for agents, directives in groups:
        for agent in agents:
            if agent == "*":
                wildcard = wildcard or directives
            elif agent and agent in ua:
                specific = specific or directives

    chosen = specific if specific is not None else (wildcard or {})
    delay: float | None = None
    if "crawl-delay" in chosen:
        try:
            delay = float(chosen["crawl-delay"])
        except ValueError:
            delay = None
    return delay, chosen.get("content-signal")


class RobotsGate:
    """Decide, por host, si nuestro user-agent puede pedir una URL."""

    def __init__(
        self,
        fetch: Callable[[str], httpx.Response],
        user_agent: str,
    ) -> None:
        self._fetch = fetch
        self._user_agent = user_agent
        self._cache: dict[str, RobotsDecision] = {}
        self._parsers: dict[str, RobotFileParser] = {}

    def decision_for(self, url: str) -> RobotsDecision:
        robots_url = _robots_url_for(url)
        cached = self._cache.get(robots_url)
        if cached is not None:
            if cached.allowed and robots_url in self._parsers:
                parser = self._parsers[robots_url]
                allowed = parser.can_fetch(self._user_agent, url)
                return cached.model_copy(update={"allowed": allowed})
            return cached

        now = datetime.now(UTC)
        try:
            response = self._fetch(robots_url)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo es "no comprobado"
            decision = RobotsDecision(
                robots_url=robots_url,
                fetched_at=now,
                robots_sha256=None,
                user_agent=self._user_agent,
                allowed=False,
                note=f"robots.txt no comprobado: {type(exc).__name__}: {exc}",
            )
            self._cache[robots_url] = decision
            return decision

        body = response.content
        if response.status_code == 404:
            # Ausencia comprobada de robots.txt: el estandar la trata como
            # permiso. Es un negativo verificado, no un fallo de lectura.
            decision = RobotsDecision(
                robots_url=robots_url,
                fetched_at=now,
                robots_sha256=hashlib.sha256(body).hexdigest(),
                user_agent=self._user_agent,
                allowed=True,
                note="sin robots.txt (HTTP 404): permitido por omision",
            )
            self._cache[robots_url] = decision
            return decision

        if response.status_code != 200 or not body:
            decision = RobotsDecision(
                robots_url=robots_url,
                fetched_at=now,
                robots_sha256=None,
                user_agent=self._user_agent,
                allowed=False,
                note=(
                    f"robots.txt no comprobado: HTTP {response.status_code}, "
                    f"{len(body)} bytes"
                ),
            )
            self._cache[robots_url] = decision
            return decision

        text = body.decode("utf-8", errors="replace")
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        self._parsers[robots_url] = parser
        delay, signal = parse_directives(text, self._user_agent)

        decision = RobotsDecision(
            robots_url=robots_url,
            fetched_at=now,
            robots_sha256=hashlib.sha256(body).hexdigest(),
            user_agent=self._user_agent,
            allowed=parser.can_fetch(self._user_agent, url),
            crawl_delay_s=delay,
            content_signal=signal,
        )
        self._cache[robots_url] = decision
        return decision

    def allows(self, url: str) -> bool:
        return self.decision_for(url).allowed
