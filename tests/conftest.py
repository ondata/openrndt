"""Fixture pytest condivise."""

from __future__ import annotations

import json
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
def _reset_output_mode():
    from openrndt import output

    output.set_mode("json")
    yield
    output.set_mode("json")
