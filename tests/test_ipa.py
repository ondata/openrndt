"""Codici IPA: vocabolario offline e filtro sul prefisso dell'id (#38)."""

import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

from openrndt import (
    find_ipa,
    geolibre_search_url,
    ipa_clause,
    ipa_vocabulary,
    ipa_vocabulary_date,
    search,
)
from openrndt.cli import app
from openrndt.config import DEFAULT_BASE_URL

runner = CliRunner()
EMPTY = {"total": {"value": 0, "relation": "eq"}, "num": 0, "start": 1, "results": []}


def test_ipa_clause_ignores_case_and_anchors_on_prefix():
    # R_SARDEG 404 + r_sardeg 362 = 766 dal vivo, il 2026-10-10.
    assert ipa_clause("r_sardeg") == "apiso_Identifier_s:/[rR]_[sS][aA][rR][dD][eE][gG]:.*/"
    assert ipa_clause(" PCM ") == "apiso_Identifier_s:/[pP][cC][mM]:.*/"


def test_ipa_clause_several_codes_in_or():
    assert ipa_clause("r_piemon, cmto") == "apiso_Identifier_s:(/[rR]_[pP][iI][eE][mM][oO][nN]:.*/ OR /[cC][mM][tT][oO]:.*/)"
    assert ipa_clause("40b59awr") == "apiso_Identifier_s:/40[bB]59[aA][wW][rR]:.*/"


@pytest.mark.parametrize("bad", ["", " , ", "r_x!", "c_f205:x", "a b"])
def test_ipa_clause_rejects_invalid_codes(bad):
    with pytest.raises(ValueError):
        ipa_clause(bad)


def test_vocabulary_shape_and_known_codes():
    codes = {c["codice"]: c for c in ipa_vocabulary()}
    assert len(codes) > 150
    assert ipa_vocabulary_date()
    assert codes["arpa_ve"]["acronimo"] == "ARPAV"
    assert "ARPAV" in codes["arpa_ve"]["enti"]
    assert codes["pcm"]["grafie"] == ["PCM"]
    assert codes["istgemil"]["ipa"] is False
    assert set(codes["pcm"]) == {"codice", "ipa", "nome_ipa", "acronimo", "enti", "schede", "grafie"}


def test_vocabulary_returns_independent_copies():
    first = ipa_vocabulary()
    first[0]["enti"].clear()
    first[0]["grafie"].append("X")
    again = ipa_vocabulary()[0]
    assert again["enti"] and "X" not in again["grafie"]


def test_find_ipa_by_acronym_name_and_code():
    assert [c["codice"] for c in find_ipa("arpae")] == ["arpa"]  # acronimo IPA «ARPAE ER»
    assert "r_sardeg" in [c["codice"] for c in find_ipa("sardegna")]
    assert [c["codice"] for c in find_ipa("CMTO")] == ["cmto"]
    assert find_ipa("  ") == []


@respx.mock
def test_search_sends_ipa_clause_in_and():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(return_value=httpx.Response(200, json=EMPTY))
    search(q="catasto", ipa="r_sardeg", num=1)
    assert route.calls.last.request.url.params["q"] == "(catasto) AND apiso_Identifier_s:/[rR]_[sS][aA][rR][dD][eE][gG]:.*/"


def test_geolibre_search_url_leaves_ipa_out():
    link = geolibre_search_url(q="catasto", ipa="r_sardeg")
    assert "r_sardeg" not in link["url"]
    assert link["untranslated"] == ["ipa"]


@respx.mock
def test_cli_search_and_footprints_ipa():
    route = respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(return_value=httpx.Response(200, json=EMPTY))
    for command in ("search", "footprints"):
        result = runner.invoke(app, [command, "--ipa", "pcm"])
        assert result.exit_code == 0, result.output
        assert route.calls.last.request.url.params["q"] == "apiso_Identifier_s:/[pP][cC][mM]:.*/"


def test_cli_search_invalid_ipa_exits_2():
    result = runner.invoke(app, ["search", "--ipa", "r_x!"])
    assert result.exit_code == 2
    assert "Codice IPA non valido" in result.output


def test_cli_discover_ipa_match():
    result = runner.invoke(app, ["--format", "json", "discover", "--what", "ipa", "--match", "arpae"])
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert [c["codice"] for c in out["codici"]] == ["arpa"]
    assert out["generato"] == ipa_vocabulary_date()
    assert runner.invoke(app, ["discover", "--what", "sort_values", "--match", "x"]).exit_code == 2


@respx.mock
def test_cli_org_zero_suggests_ipa_code():
    """`--org arpae` dà 0 (l'ente è per esteso), ma il vocabolario conosce l'acronimo."""
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(return_value=httpx.Response(200, json=EMPTY))
    result = runner.invoke(app, ["search", "--org", "arpae"])
    assert result.exit_code == 0, result.output
    assert "codici IPA nel vocabolario: --ipa arpa (" in result.output
