from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from observatorio_gt.manifest import RobotsDecision
from observatorio_gt.net.cache import DiskCache
from observatorio_gt.net.client import HttpPolicy, PoliteClient

FIXTURES = Path(__file__).parent / "fixtures" / "cc_ptmp"

UA = "ObservatorioJusticiaGT/0.1 (+https://example.invalid/repo)"


@pytest.fixture
def robots_txt() -> str:
    return (FIXTURES / "robots.txt").read_text(encoding="utf-8")


@pytest.fixture
def atributos_html() -> str:
    return (FIXTURES / "atributo_798734.html").read_text(encoding="utf-8")


@pytest.fixture
def api_ok() -> dict[str, Any]:
    return json.loads((FIXTURES / "api_expedientes_ok.json").read_text(encoding="utf-8"))


class FakeClock:
    """Reloj y sleep falsos: la suite no duerme de verdad."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_client(
    handler: Any,
    *,
    clock: FakeClock,
    tmp_path: Path | None = None,
    policy: HttpPolicy | None = None,
) -> PoliteClient:
    cache = DiskCache(tmp_path / "cache", ttl_s=3600) if tmp_path else None
    return PoliteClient(
        policy or HttpPolicy(user_agent=UA, requests_per_second=0.5),
        cache,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleep=clock.sleep,
    )


@pytest.fixture
def allowed_robots() -> RobotsDecision:
    return RobotsDecision(
        robots_url="https://jurisprudencia.cc.gob.gt/robots.txt",
        fetched_at=datetime.now(UTC),
        robots_sha256="0" * 64,
        user_agent=UA,
        allowed=True,
        content_signal="search=yes,ai-train=no,use=reference",
    )
