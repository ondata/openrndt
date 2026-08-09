"""Test della versione: fonte unica e nessuna deriva fra i punti che la espongono."""

from __future__ import annotations

from typer.testing import CliRunner

import openrndt
from openrndt._version import __version__
from openrndt.cli import app
from openrndt.client import USER_AGENT

runner = CliRunner()


def test_version_flag_prints_version_and_exits_zero():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == f"openrndt {__version__}"


def test_version_short_flag():
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == f"openrndt {__version__}"


def test_user_agent_derives_from_package_version():
    # Il User-Agent restava indietro a mano (era fermo a 0.1 con il pacchetto a 1.0.0):
    # ora deriva dalla versione, quindi la deriva non è più possibile.
    assert USER_AGENT == f"openrndt/{__version__} (+https://geodati.gov.it/RNDT)"


def test_package_exports_same_version():
    assert openrndt.__version__ == __version__


def test_version_is_resolved_not_placeholder():
    assert __version__ != "0.0.0+unknown"
