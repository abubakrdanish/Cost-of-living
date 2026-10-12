"""Polite HTTP downloads: clear User-Agent, timeouts, retries with backoff, rate limit."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.config import USER_AGENT

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 10
READ_TIMEOUT_S = 120
MIN_INTERVAL_S = 2.0  # minimum gap between requests to the same client


def build_session(user_agent: str = USER_AGENT, total_retries: int = 5) -> requests.Session:
    """Session that retries connection errors, 429 and 5xx with exponential backoff.

    Backoff waits roughly 2, 4, 8, 16... seconds and honours `Retry-After`.
    """
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


@dataclass
class Downloaded:
    """Body and provenance of one HTTP response."""

    url: str
    content: bytes
    content_type: str
    last_modified: str | None


@dataclass
class PoliteClient:
    """Wraps a session and enforces a minimum interval between requests."""

    session: requests.Session = field(default_factory=build_session)
    min_interval_s: float = MIN_INTERVAL_S
    _last_request_at: float = 0.0

    def get(self, url: str, accept: str | None = None) -> Downloaded:
        """GET a URL and return its body. Raises for non-2xx after retries."""
        self._wait_for_slot()
        headers = {"Accept": accept} if accept else {}
        log.info("GET %s", url)
        started = time.monotonic()
        response = self.session.get(
            url, headers=headers, timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S)
        )
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        log.info(
            "  -> %s, %d bytes in %.1fs",
            response.status_code,
            len(response.content),
            self._last_request_at - started,
        )
        return Downloaded(
            url=url,
            content=response.content,
            content_type=response.headers.get("Content-Type", ""),
            last_modified=response.headers.get("Last-Modified"),
        )

    def _wait_for_slot(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if self._last_request_at and elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
