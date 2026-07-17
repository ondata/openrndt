"""Configurazione: base URL ed env var override."""

from __future__ import annotations

import os

DEFAULT_BASE_URL = "https://geodati.gov.it/RNDT"
ENV_BASE_URL = "OPENRNDT_BASE_URL"
DEFAULT_TIMEOUT = 30.0

_override: str | None = None
_timeout: float = DEFAULT_TIMEOUT


def get_base_url() -> str:
    if _override:
        return _override.rstrip("/")
    return os.environ.get(ENV_BASE_URL, DEFAULT_BASE_URL).rstrip("/")


def set_base_url(url: str | None) -> None:
    global _override
    _override = url


def get_timeout() -> float:
    return _timeout


def set_timeout(timeout: float | None) -> None:
    global _timeout
    _timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
