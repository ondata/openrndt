"""HTTP client per il RNDT con retry esponenziale."""

from __future__ import annotations

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from openrndt.config import get_base_url

USER_AGENT = "openrndt/0.1 (+https://geodati.gov.it/RNDT)"
DEFAULT_TIMEOUT = 30.0


def rndt_request(path: str, params: dict | None = None, *, timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """GET su un endpoint RNDT con retry su timeout e 5xx."""
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
