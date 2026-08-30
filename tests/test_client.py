from __future__ import annotations

import gzip

import httpx
import pytest

from observatorio_gt.net.checks import EXPECT_API, Expectation, FetchOutcome
from observatorio_gt.net.client import (
    HttpPolicy,
    PoliteClient,
    RequestBudgetExceeded,
    ThrottledError,
)
from tests.conftest import UA, FakeClock, make_client

ROBOTS = b"User-agent: *\nAllow: /\n"
API_BODY = b'{"documentos": [], "recordsTotal": 0, "recordsFiltered": 0, "draw": 1}'
EXPECT_ANY = Expectation(kind="text", min_bytes=1)


def handler_factory(calls: list[httpx.Request], responses: list[httpx.Response]):  # noqa: ANN201
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"}, content=ROBOTS)
        return responses.pop(0) if responses else httpx.Response(
            200, headers={"content-type": "application/json"}, content=API_BODY
        )

    return handler


def test_ua_viaja_en_todas_las_peticiones_incluida_robots(clock: FakeClock) -> None:
    calls: list[httpx.Request] = []
    client = make_client(handler_factory(calls, []), clock=clock)
    with client:
        client.post_json("https://x.invalid/api", {}, expect=EXPECT_API, use_cache=False)
    assert len(calls) == 2
    assert all(c.headers["user-agent"] == UA for c in calls)
    assert calls[0].url.path == "/robots.txt"


def test_intervalo_minimo_respetado(clock: FakeClock) -> None:
    calls: list[httpx.Request] = []
    client = make_client(handler_factory(calls, []), clock=clock)
    with client:
        for _ in range(3):
            client.post_json("https://x.invalid/api", {}, expect=EXPECT_API, use_cache=False)
    # 1 robots + 3 peticiones = 4; las esperas deben rondar los 2 s (0.5 req/s)
    assert len(calls) == 4
    assert len(clock.slept) >= 3
    assert all(1.0 < s < 3.0 for s in clock.slept)


def test_429_con_retry_after_espera_lo_indicado(clock: FakeClock) -> None:
    calls: list[httpx.Request] = []
    responses = [
        httpx.Response(429, headers={"retry-after": "5", "content-type": "application/json"},
                       content=b"{}"),
        httpx.Response(200, headers={"content-type": "application/json"}, content=API_BODY),
    ]
    client = make_client(handler_factory(calls, responses), clock=clock)
    with client:
        _, record = client.post_json(
            "https://x.invalid/api", {}, expect=EXPECT_API, use_cache=False
        )
    assert record.attempts == 2
    assert 5.0 in clock.slept


def test_404_no_se_reintenta(clock: FakeClock) -> None:
    calls: list[httpx.Request] = []
    responses = [httpx.Response(404, headers={"content-type": "text/html"}, content=b"nope")]
    client = make_client(handler_factory(calls, responses), clock=clock)
    with client:
        _, record = client.get("https://x.invalid/y", expect=EXPECT_ANY, use_cache=False)
    assert record.attempts == 1
    assert record.outcome is FetchOutcome.HTTP_ERROR


def test_dos_throttles_seguidos_detienen_la_corrida(clock: FakeClock) -> None:
    """El throttling visible detiene el spike, no lo hace insistir."""
    calls: list[httpx.Request] = []
    responses = [
        httpx.Response(503, headers={"content-type": "text/html"}, content=b"busy"),
        httpx.Response(503, headers={"content-type": "text/html"}, content=b"busy"),
    ]
    client = make_client(handler_factory(calls, responses), clock=clock)
    with client, pytest.raises(ThrottledError):
        client.get("https://x.invalid/y", expect=EXPECT_ANY, use_cache=False)


def test_presupuesto_duro(clock: FakeClock) -> None:
    calls: list[httpx.Request] = []
    policy = HttpPolicy(user_agent=UA, requests_per_second=0.5, max_requests_per_run=3)
    client = make_client(handler_factory(calls, []), clock=clock, policy=policy)
    with client, pytest.raises(RequestBudgetExceeded):
        for _ in range(5):
            client.post_json("https://x.invalid/api", {}, expect=EXPECT_API, use_cache=False)


def test_cache_no_repite_peticion(clock: FakeClock, tmp_path) -> None:  # noqa: ANN001
    calls: list[httpx.Request] = []
    client = make_client(handler_factory(calls, []), clock=clock, tmp_path=tmp_path)
    with client:
        _, first = client.post_json("https://x.invalid/api", {"q": 1}, expect=EXPECT_API)
        _, second = client.post_json("https://x.invalid/api", {"q": 1}, expect=EXPECT_API)
    api_calls = [c for c in calls if c.url.path != "/robots.txt"]
    assert len(api_calls) == 1
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.attempts == 0


def test_robots_prohibitivo_bloquea(clock: FakeClock) -> None:
    from observatorio_gt.net.client import RobotsDisallowed

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, headers={"content-type": "text/plain"},
                content=b"User-agent: *\nDisallow: /\n",
            )
        return httpx.Response(200, content=b"no deberia llegar aqui")

    client = PoliteClient(
        HttpPolicy(user_agent=UA), None, transport=httpx.MockTransport(handler),
        clock=clock, sleep=clock.sleep,
    )
    with client, pytest.raises(RobotsDisallowed):
        client.get("https://x.invalid/y", expect=EXPECT_ANY)


def test_cache_no_guarda_cabecera_de_codificacion(clock: FakeClock, tmp_path) -> None:  # noqa: ANN001
    """El cuerpo se guarda descomprimido: conservar content-encoding lo corrompe."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, headers={"content-type": "text/plain"}, content=ROBOTS)
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "content-encoding": "gzip"},
            content=gzip.compress(API_BODY),
        )

    client = make_client(handler, clock=clock, tmp_path=tmp_path)
    with client:
        client.post_json("https://x.invalid/api", {"q": 1}, expect=EXPECT_API)
        response, record = client.post_json("https://x.invalid/api", {"q": 1}, expect=EXPECT_API)
    assert record.from_cache is True
    assert record.outcome is FetchOutcome.OK
    assert response.content == API_BODY  # legible, no un cuerpo corrupto
    assert "content-encoding" not in response.headers
