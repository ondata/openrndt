"""HTTP client per il RNDT con retry esponenziale."""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from openrndt.config import get_base_url, get_timeout

USER_AGENT = "openrndt/0.1 (+https://geodati.gov.it/RNDT)"


def rndt_request(path: str, params: dict[str, Any] | None = None, *, timeout: float | None = None) -> httpx.Response:
    """GET su un endpoint RNDT con retry su timeout e 5xx.

    Se `timeout` è `None` (default), usa il timeout configurato globalmente
    (`config.set_timeout()` / `--timeout` in CLI, default 30 secondi).
    """
    if timeout is None:
        timeout = get_timeout()
    base = get_base_url()
    url = f"{base}{path}"
    headers = {"User-Agent": USER_AGENT}

    for attempt in Retrying(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        reraise=True,
    ):
        with attempt:
            response = httpx.get(url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
            if response.status_code >= 500:
                response.raise_for_status()
            return response
    raise RuntimeError("rndt_request: unreachable")  # pragma: no cover
