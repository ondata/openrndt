"""Le verifiche di `scripts/build_ipa_registry.py`, che proteggono l'anagrafica pubblicata (#38)."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_ipa_registry.py"
spec = importlib.util.spec_from_file_location("build_ipa_registry", SCRIPT)
assert spec and spec.loader
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)

HEADER = "Codice_IPA,Denominazione_ente,Acronimo,Altro\n"


def ipa_text(*rows: str) -> str:
    return HEADER + "".join(r + "\n" for r in rows)


def test_reduce_keeps_three_fields_lowercase_and_sorted():
    rows = registry.reduce(ipa_text("R_PIEMON,Regione Piemonte,,x", "arpa,Agenzia Regionale,ARPAE ER,y"))
    assert rows == [["arpa", "Agenzia Regionale", "ARPAE ER"], ["r_piemon", "Regione Piemonte", ""]]


def test_reduce_rejects_missing_columns():
    with pytest.raises(SystemExit, match="colonne mancanti"):
        registry.reduce("Codice_IPA,Nome\nx,y\n")


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([["a", "A", ""]], "meno di"),
        ([["a", "A", ""], ["a", "B", ""]], "ripetuti"),
        ([["a b", "A", ""], ["c", "C", ""]], "non validi"),
        ([["a", "", ""], ["b", "B", ""]], "senza denominazione"),
    ],
)
def test_verify_rejects_bad_registry(rows, message):
    with pytest.raises(SystemExit, match=message):
        registry.verify(rows, min_rows=2)


def test_verify_accepts_good_registry():
    registry.verify([["a", "A", ""], ["b", "B", "BB"]], min_rows=2)


def run_main(monkeypatch, out: Path, text: str, min_rows: int) -> None:
    monkeypatch.setattr(registry, "download", lambda: text)
    monkeypatch.setattr(sys, "argv", ["build_ipa_registry.py", str(out), "--min-rows", str(min_rows)])
    registry.main()


def test_main_writes_verified_registry(monkeypatch, tmp_path):
    out = tmp_path / "ipa-enti.csv"
    run_main(monkeypatch, out, ipa_text("b,B,,", "a,A,AA,"), min_rows=2)
    assert out.read_text(encoding="utf-8").splitlines() == ["codice_ipa,denominazione,acronimo", "a,A,AA", "b,B,"]


def test_main_leaves_existing_file_when_verification_fails(monkeypatch, tmp_path):
    out = tmp_path / "ipa-enti.csv"
    out.write_text("copia buona\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        run_main(monkeypatch, out, ipa_text("a,A,,"), min_rows=2)
    assert out.read_text(encoding="utf-8") == "copia buona\n"
