"""Cliente HTTP educado: limite de tasa, cache, presupuesto y fallo cerrado.

Portado de un cliente anterior de recoleccion documental, con type hints e
inyeccion de reloj y de transporte para poder probarlo sin red ni esperas
reales.

Politica deliberada: **el throttling visible detiene la corrida, no la hace
insistir.** Dos 429/503 seguidos abortan. Nunca se rota user-agent ni IP: eso
seria evadir un control, y esta prohibido.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from observatorio_gt.manifest import FetchRecord
from observatorio_gt.net.cache import DiskCache
from observatorio_gt.net.checks import Expectation, FetchOutcome, evaluate
from observatorio_gt.net.robots import RobotsGate

log = structlog.get_logger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
THROTTLE_STATUS = frozenset({429, 503})


@dataclass(frozen=True)
class HttpPolicy:
    user_agent: str
    requests_per_second: float = 0.5
    jitter: float = 0.2
    timeout_s: float = 30.0
    max_attempts: int = 3
    backoff_base_s: float = 2.0
    backoff_max_s: float = 60.0
    honor_crawl_delay: bool = True
    max_requests_per_run: int = 100
    max_consecutive_throttles: int = 2

    @property
    def min_interval_s(self) -> float:
        if self.requests_per_second <= 0:
            return 0.0
        return 1.0 / self.requests_per_second


class RequestBudgetExceeded(RuntimeError):
    """El cortacircuitos anti-scraping-masivo se activo."""


class ThrottledError(RuntimeError):
    """La fuente esta limitando la tasa. Se detiene la corrida."""


class RobotsDisallowed(RuntimeError):
    """robots.txt no permite esta URL para nuestro user-agent."""


class PoliteClient:
    def __init__(
        self,
        policy: HttpPolicy,
        cache: DiskCache | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self.policy = policy
        self.cache = cache
        self._clock = clock
        self._sleep = sleep
        self._rng = rng or random.Random(0)
        self._last_request_at: float | None = None
        self._requests_made = 0
        self._consecutive_throttles = 0
        self._client = httpx.Client(
            headers={
                "User-Agent": policy.user_agent,
                # Este servidor anuncia a veces una compresion que el cuerpo no
                # trae, y httpx revienta al descomprimir ("incorrect header
                # check"). Comprobado el 29-08-2026 en la API de listado al
                # paginar. Pedir sin comprimir cuesta ancho de banda y evita
                # perder documentos por un defecto del servidor.
                "Accept-Encoding": "identity",
            },
            timeout=policy.timeout_s,
            transport=transport,
            follow_redirects=True,
        )
        # El gate usa este mismo cliente: robots.txt se baja con NUESTRO UA.
        self.robots = RobotsGate(fetch=self._raw_get_for_robots, user_agent=policy.user_agent)
        self._crawl_delay_s: float | None = None

    # -- ciclo de vida -----------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def requests_made(self) -> int:
        return self._requests_made

    # -- internals ---------------------------------------------------------
    def _raw_get_for_robots(self, url: str) -> httpx.Response:
        """robots.txt se pide sin pasar por el propio gate (seria circular)."""
        self._throttle_wait()
        self._spend_budget()
        return self._client.get(url)

    def _spend_budget(self) -> None:
        if self._requests_made >= self.policy.max_requests_per_run:
            raise RequestBudgetExceeded(
                f"presupuesto agotado: {self.policy.max_requests_per_run} peticiones por corrida"
            )
        self._requests_made += 1

    def _interval(self) -> float:
        interval = self.policy.min_interval_s
        if self.policy.honor_crawl_delay and self._crawl_delay_s:
            interval = max(interval, self._crawl_delay_s)
        return interval

    def _throttle_wait(self) -> None:
        interval = self._interval()
        if interval <= 0:
            self._last_request_at = self._clock()
            return
        now = self._clock()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            wait = interval - elapsed
            if wait > 0:
                jitter = 1.0 + self._rng.uniform(-self.policy.jitter, self.policy.jitter)
                self._sleep(wait * jitter)
        self._last_request_at = self._clock()

    def _backoff(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return float(min(float(retry_after), self.policy.backoff_max_s))
            except ValueError:
                pass  # Retry-After en formato fecha: se ignora y se usa el backoff
        base = self.policy.backoff_base_s * (2 ** (attempt - 1))
        return float(min(base, self.policy.backoff_max_s)) * self._rng.uniform(0.5, 1.0)

    def _check_robots(self, url: str) -> None:
        decision = self.robots.decision_for(url)
        if decision.crawl_delay_s:
            self._crawl_delay_s = decision.crawl_delay_s
        if not decision.allowed:
            raise RobotsDisallowed(f"{url}: {decision.note or 'no permitido por robots.txt'}")

    # -- API publica -------------------------------------------------------
    def request(
        self,
        method: str,
        url: str,
        *,
        expect: Expectation,
        json_body: dict[str, Any] | None = None,
        use_cache: bool = True,
        check_robots: bool = True,
        headers: dict[str, str] | None = None,
    ) -> tuple[httpx.Response, FetchRecord]:
        if check_robots:
            self._check_robots(url)

        requested_at = datetime.now(UTC)
        cache_key = self.cache.key(method, url, json_body) if self.cache else None

        if use_cache and self.cache and cache_key:
            hit = self.cache.get(cache_key)
            if hit is not None:
                cached_response = httpx.Response(
                    status_code=hit.status_code,
                    headers=hit.headers,
                    content=hit.content,
                    request=httpx.Request(method, url),
                )
                outcome, note = evaluate(cached_response, expect)
                record = FetchRecord(
                    url=url,
                    method="POST" if method.upper() == "POST" else "GET",
                    requested_at=requested_at,
                    http_status=hit.status_code,
                    content_length=len(hit.content),
                    content_type=hit.headers.get("content-type"),
                    from_cache=True,
                    attempts=0,
                    outcome=outcome,
                    note=note,
                )
                log.info("http", url=url, from_cache=True, outcome=str(outcome))
                return cached_response, record

        last_exc: Exception | None = None
        response: httpx.Response | None = None
        attempts = 0
        elapsed_ms: int | None = None

        for attempt in range(1, self.policy.max_attempts + 1):
            attempts = attempt
            self._throttle_wait()
            self._spend_budget()
            started = self._clock()
            try:
                response = self._client.request(
                    method, url, json=json_body, headers=headers
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                log.warning("http_error", url=url, attempt=attempt, error=str(exc))
                if attempt == self.policy.max_attempts:
                    break
                self._sleep(self._backoff(attempt, None))
                continue

            elapsed_ms = int((self._clock() - started) * 1000)

            if response.status_code in THROTTLE_STATUS:
                self._consecutive_throttles += 1
                if self._consecutive_throttles >= self.policy.max_consecutive_throttles:
                    raise ThrottledError(
                        f"{self._consecutive_throttles} respuestas de limite de tasa seguidas "
                        f"(ultima: HTTP {response.status_code} en {url}). Corrida detenida."
                    )
            else:
                self._consecutive_throttles = 0

            if response.status_code in RETRYABLE_STATUS and attempt < self.policy.max_attempts:
                wait = self._backoff(attempt, response.headers.get("retry-after"))
                log.warning(
                    "http_retry", url=url, status=response.status_code, attempt=attempt, wait_s=wait
                )
                self._sleep(wait)
                continue
            break

        if response is None:
            record = FetchRecord(
                url=url,
                method="POST" if method.upper() == "POST" else "GET",
                requested_at=requested_at,
                outcome=FetchOutcome.NOT_CHECKED,
                attempts=attempts,
                note=f"sin respuesta: {type(last_exc).__name__}: {last_exc}",
            )
            raise httpx.HTTPError(str(last_exc)) from last_exc

        outcome, note = evaluate(response, expect)

        if outcome is FetchOutcome.OK and use_cache and self.cache and cache_key:
            self.cache.put(
                cache_key,
                response.status_code,
                dict(response.headers),
                response.content,
                request_summary=f"{method} {url}",
            )

        record = FetchRecord(
            url=url,
            method="POST" if method.upper() == "POST" else "GET",
            requested_at=requested_at,
            http_status=response.status_code,
            content_length=len(response.content),
            content_type=response.headers.get("content-type"),
            elapsed_ms=elapsed_ms,
            from_cache=False,
            attempts=attempts,
            outcome=outcome,
            note=note,
        )
        log.info(
            "http",
            url=url,
            status=response.status_code,
            bytes=len(response.content),
            outcome=str(outcome),
            attempts=attempts,
        )
        return response, record

    def get(
        self,
        url: str,
        *,
        expect: Expectation,
        use_cache: bool = True,
        check_robots: bool = True,
        headers: dict[str, str] | None = None,
    ) -> tuple[httpx.Response, FetchRecord]:
        return self.request(
            "GET",
            url,
            expect=expect,
            use_cache=use_cache,
            check_robots=check_robots,
            headers=headers,
        )

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        expect: Expectation,
        use_cache: bool = True,
        check_robots: bool = True,
    ) -> tuple[httpx.Response, FetchRecord]:
        return self.request(
            "POST",
            url,
            expect=expect,
            json_body=payload,
            use_cache=use_cache,
            check_robots=check_robots,
        )
