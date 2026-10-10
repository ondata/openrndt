"""`scripts/build_ipa_vocabulary.py` senza rete: intestazione dell'anagrafica, categoria, file scritti (#44)."""

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_ipa_vocabulary.py"
spec = importlib.util.spec_from_file_location("build_ipa_vocabulary", SCRIPT)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

REGISTRY = (
    "codice_ipa,denominazione,acronimo,categoria,nome_categoria\n"
    "c_l219,Comune di Torino,,L6,Comuni e loro Consorzi e Associazioni\n"
    "r_sardeg,Regione Autonoma della Sardegna,RAS,L4,Regioni\n"
)
SCAN = "id,prefisso,ente\nc_l219:1,c_l219,Comune di Torino\nR_SARDEG:2,R_SARDEG,Regione Sardegna\nr_sardeg:3,r_sardeg,\nistgemil:4,istgemil,\n"


def test_registry_text_rejects_registry_without_category(tmp_path):
    old = tmp_path / "old.csv"
    old.write_text("codice_ipa,denominazione,acronimo\nc_l219,Comune di Torino,\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="ipa-registry"):
        builder.registry_text(None, old)


def test_build_adds_category_from_registry():
    rows = [("c_l219:1", "c_l219", "Comune di Torino"), ("x:2", "istgemil", "")]
    codes = {c["codice"]: c for c in builder.build(rows, builder.ipa_registry(REGISTRY))["codici"]}
    assert (codes["c_l219"]["categoria"], codes["c_l219"]["nome_categoria"]) == ("L6", "Comuni e loro Consorzi e Associazioni")
    assert codes["istgemil"]["ipa"] is False
    assert codes["istgemil"]["categoria"] is None


def test_main_writes_vocabulary_and_gzip_registry(monkeypatch, tmp_path):
    (tmp_path / "scan.csv").write_text(SCAN, encoding="utf-8")
    (tmp_path / "registry.csv").write_text(REGISTRY, encoding="utf-8")
    out = tmp_path / "data" / "ipa.json"
    monkeypatch.setattr(builder, "OUT", out)
    monkeypatch.setattr(builder, "REGISTRY_OUT", out.with_name("ipa-enti.csv.gz"))
    monkeypatch.setattr(
        sys, "argv", ["build_ipa_vocabulary.py", "--scan", str(tmp_path / "scan.csv"), "--registry", str(tmp_path / "registry.csv")]
    )
    builder.main()
    vocabulary = json.loads(out.read_text(encoding="utf-8"))
    sardeg = next(c for c in vocabulary["codici"] if c["codice"] == "r_sardeg")
    assert (sardeg["schede"], sardeg["grafie"], sardeg["categoria"]) == (2, ["R_SARDEG", "r_sardeg"], "L4")
    gz = out.with_name("ipa-enti.csv.gz").read_bytes()
    assert gzip.decompress(gz).decode("utf-8") == REGISTRY
    # mtime=0: stessa anagrafica, stesso file.
    assert gz == gzip.compress(REGISTRY.encode("utf-8"), compresslevel=9, mtime=0)


def test_registry_text_from_release_drops_crlf():
    # `csv.writer` scrive CRLF nella release: senza normalizzare, il gzip cambierebbe secondo la fonte.
    class Client:
        def get(self, url, follow_redirects):
            return type("R", (), {"content": REGISTRY.replace("\n", "\r\n").encode(), "raise_for_status": lambda self: None})()

    assert builder.registry_text(Client(), None) == REGISTRY
