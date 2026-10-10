"""Codici IPA: vocabolario offline, anagrafica nel pacchetto e filtro sul prefisso dell'id (#38, #44)."""

import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

from openrndt import (
    find_ipa,
    find_ipa_registry,
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
    assert set(codes["pcm"]) == {"codice", "ipa", "nome_ipa", "acronimo", "categoria", "nome_categoria", "enti", "schede", "grafie"}
    assert (codes["c_l219"]["categoria"], codes["c_l219"]["nome_categoria"]) == ("L6", "Comuni e loro Consorzi e Associazioni")
    assert codes["istgemil"]["categoria"] is None


def test_find_ipa_registry_finds_entities_without_records():
    # Il Comune di Palermo è nell'Indice PA ma non ha schede nel RNDT (2026-10-10).
    assert find_ipa("comune di palermo") == []
    found = find_ipa_registry("Comune di Palermo")
    assert [c["codice"] for c in found] == ["c_g273"]
    assert found[0] == {
        "codice": "c_g273", "ipa": True, "nome_ipa": "Comune di Palermo", "acronimo": None,
        "categoria": "L6", "nome_categoria": "Comuni e loro Consorzi e Associazioni",
        "enti": [], "schede": 0, "grafie": [],
    }
    assert find_ipa_registry("  ") == []


def test_find_ipa_registry_skips_vocabulary_and_puts_publishing_categories_first():
    assert "c_l219" not in [c["codice"] for c in find_ipa_registry("torino")]
    # Prima il Comune e la Città metropolitana, poi le categorie che non pubblicano sul RNDT.
    assert [c["codice"] for c in find_ipa_registry("palermo")[:2]] == ["c_g273", "p_pa"]


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


def test_geolibre_search_url_translates_ipa():
    link = geolibre_search_url(q="catasto", ipa="R_SARDEG, arpa_ve")
    assert link["url"].endswith("&rndt=catasto&rndtIpa=R_SARDEG,arpa_ve")
    assert link["untranslated"] == []


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


def test_cli_discover_ipa_falls_back_on_registry():
    result = runner.invoke(app, ["--format", "json", "discover", "--what", "ipa", "--match", "comune di palermo"])
    assert result.exit_code == 0, result.output
    assert [c["codice"] for c in json.loads(result.stdout)["codici"]] == ["c_g273"]
    assert "Dall'anagrafica IPA, 1 ente senza schede nel RNDT" in result.stderr


@respx.mock
def test_cli_search_org_zero_results_names_registry_entity():
    respx.get(f"{DEFAULT_BASE_URL}/rest/metadata/search").mock(return_value=httpx.Response(200, json=EMPTY))
    result = runner.invoke(app, ["search", "--org", "comune di palermo"])
    assert result.exit_code == 0, result.output
    assert "nell'Indice PA ma senza schede nel RNDT: c_g273 (Comune di Palermo)" in result.stderr
