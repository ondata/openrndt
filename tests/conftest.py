"""Fixture pytest condivise."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def search_response_json() -> dict:
    return json.loads((FIXTURES / "search_response.json").read_text(encoding="utf-8"))


@pytest.fixture()
def item_response_json() -> dict:
    return json.loads((FIXTURES / "item.json").read_text(encoding="utf-8"))


@pytest.fixture()
def item_response_xml() -> str:
    return (FIXTURES / "item.xml").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_base_url():
    from openrndt import config

    config.set_base_url(None)
    yield
    config.set_base_url(None)


@pytest.fixture(autouse=True)
def _reset_timeout():
    from openrndt import config

    config.set_timeout(None)
    yield
    config.set_timeout(None)


@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """Nessuna risoluzione DNS reale nei test: ogni hostname risolve a un IP pubblico.

    I test che vogliono un esito diverso (host privato, risoluzione fallita)
    rifanno il monkeypatch al proprio interno, che ha la precedenza.

    Riguarda solo i test basati su hostname: quelli su IP literal non passano
    da `getaddrinfo`, quindi lo stub non incide sul loro esito.
    """

    def _fake_getaddrinfo(host, port, *args, **kwargs):  # type: ignore[no-untyped-def]
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port or 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


@pytest.fixture(autouse=True)
def _reset_output_mode():
    from openrndt import output

    output.set_mode("json")
    yield
    output.set_mode("json")
