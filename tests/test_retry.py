"""Test della logica retry in client.rndt_request."""

from __future__ import annotations

import httpx
import pytest
import respx

from openrndt.client import rndt_request
from openrndt.config import DEFAULT_BASE_URL

PATH = "/rest/metadata/search"
URL = f"{DEFAULT_BASE_URL}{PATH}"


@respx.mock
def test_retry_succeeds_after_503():
    """Un 503 seguito da 200 deve restituire la risposta finale."""
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(200, json={"total": 0, "results": []}),
    ]
    response = rndt_request(PATH)
    assert response.status_code == 200
    assert route.call_count == 2


@respx.mock
def test_retry_raises_after_three_503():
    """Tre 503 consecutivi devono propagare HTTPStatusError dopo i retry."""
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(503),
    ]
    with pytest.raises(httpx.HTTPStatusError):
        rndt_request(PATH)
    assert route.call_count == 3
