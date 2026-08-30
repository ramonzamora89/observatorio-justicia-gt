from __future__ import annotations

import httpx

from observatorio_gt.net.robots import RobotsGate, parse_directives
from tests.conftest import UA


def gate_for(body: str, status: int = 200, record: list[str] | None = None) -> RobotsGate:
    def fetch(url: str) -> httpx.Response:
        if record is not None:
            record.append(url)
        return httpx.Response(
            status_code=status,
            headers={"content-type": "text/plain"},
            content=body.encode(),
            request=httpx.Request("GET", url),
        )

    return RobotsGate(fetch=fetch, user_agent=UA)


def test_nuestro_ua_esta_permitido(robots_txt: str) -> None:
    gate = gate_for(robots_txt)
    assert gate.allows("https://jurisprudencia.cc.gob.gt/ptmp/Expediente.aspx")
    assert gate.allows(
        "https://jurisprudencia.cc.gob.gt/coredataretriever/api/jurisprudencia/expedientes/v1"
    )


def test_claudebot_esta_bloqueado(robots_txt: str) -> None:
    """Prueba de regresion: el parser LEE el archivo, no da nada por hecho.

    Si este test se pusiera verde con un robots.txt vacio, el gate no estaria
    haciendo nada.
    """
    gate = RobotsGate(
        fetch=lambda url: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=robots_txt.encode(),
            request=httpx.Request("GET", url),
        ),
        user_agent="ClaudeBot",
    )
    assert not gate.allows("https://jurisprudencia.cc.gob.gt/ptmp/Expediente.aspx")


def test_robots_se_baja_con_nuestro_ua(robots_txt: str) -> None:
    """No se usa RobotFileParser.read(), que pediria con el UA de urllib."""
    visitados: list[str] = []
    gate = gate_for(robots_txt, record=visitados)
    gate.allows("https://jurisprudencia.cc.gob.gt/ptmp/Expediente.aspx")
    assert visitados == ["https://jurisprudencia.cc.gob.gt/robots.txt"]


def test_falla_cerrado_si_no_se_puede_leer() -> None:
    gate = gate_for("", status=500)
    decision = gate.decision_for("https://jurisprudencia.cc.gob.gt/x")
    assert decision.allowed is False
    assert "no comprobado" in (decision.note or "")


def test_excepcion_de_red_tambien_falla_cerrado() -> None:
    def boom(url: str) -> httpx.Response:
        raise httpx.ConnectError("sin ruta al host")

    gate = RobotsGate(fetch=boom, user_agent=UA)
    decision = gate.decision_for("https://jurisprudencia.cc.gob.gt/x")
    assert decision.allowed is False
    assert "no comprobado" in (decision.note or "")


def test_404_es_ausencia_comprobada_y_permite() -> None:
    gate = gate_for("", status=404)
    decision = gate.decision_for("https://ejemplo.invalid/x")
    assert decision.allowed is True
    assert "404" in (decision.note or "")


def test_content_signal_se_conserva_con_hash(robots_txt: str) -> None:
    """`ai-train=no` es una reserva expresa de derechos: hay que registrarla."""
    gate = gate_for(robots_txt)
    decision = gate.decision_for("https://jurisprudencia.cc.gob.gt/ptmp/")
    assert decision.content_signal == "search=yes,ai-train=no,use=reference"
    assert decision.robots_sha256 and len(decision.robots_sha256) == 64


def test_crawl_delay_se_extrae() -> None:
    body = "User-agent: *\nCrawl-delay: 7\nAllow: /\n"
    delay, signal = parse_directives(body, UA)
    assert delay == 7.0
    assert signal is None


def test_grupo_especifico_gana_sobre_wildcard() -> None:
    body = (
        "User-agent: *\nCrawl-delay: 1\n\n"
        "User-agent: observatoriojusticiagt\nCrawl-delay: 9\n"
    )
    delay, _ = parse_directives(body, UA)
    assert delay == 9.0
