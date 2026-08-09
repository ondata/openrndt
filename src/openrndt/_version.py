"""Versione del pacchetto, letta dai metadati della distribuzione.

Fonte unica: il campo `version` di `pyproject.toml`. Questo modulo non importa
nulla di interno, così può essere usato anche da `client.py` senza creare un
ciclo con `openrndt/__init__.py`.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openrndt")
except PackageNotFoundError:  # pragma: no cover - solo se eseguito da sorgente non installato
    __version__ = "0.0.0+unknown"
