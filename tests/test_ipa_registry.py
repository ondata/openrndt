"""Le verifiche di `scripts/build_ipa_registry.py`, che proteggono l'anagrafica pubblicata (#38, #44)."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_ipa_registry.py"
spec = importlib.util.spec_from_file_location("build_ipa_registry", SCRIPT)
assert spec and spec.loader
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)

HEADER = "Codice_IPA,Denominazione_ente,Acronimo,Codice_Categoria,Altro\n"
CATEGORIES = "Codice_categoria,Nome_categoria,Tipologia_categoria\nL4,Regioni,PA\nL6,Comuni ,PA\n"
NAMES = {"L4": "Regioni", "L6": "Comuni"}


def ipa_text(*rows: str) -> str:
    return HEADER + "".join(r + "\n" for r in rows)


def test_categories_strip_names():
    assert registry.categories(CATEGORIES) == NAMES


def test_reduce_keeps_fields_lowercase_and_sorted_with_category_name():
    rows = registry.reduce(ipa_text("R_PIEMON,Regione Piemonte,,L4,x", "c_l219,Comune di Torino,,L6,y"), NAMES)
    assert rows == [["c_l219", "Comune di Torino", "", "L6", "Comuni"], ["r_piemon", "Regione Piemonte", "", "L4", "Regioni"]]


def test_reduce_rejects_missing_columns():
    with pytest.raises(SystemExit, match="colonne mancanti"):
        registry.reduce("Codice_IPA,Nome\nx,y\n", NAMES)
    with pytest.raises(SystemExit, match="colonne mancanti"):
        registry.categories("Codice,Nome\nx,y\n")


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([["a", "A", "", "L6", "Comuni"]], "meno di"),
        ([["a", "A", "", "L6", "Comuni"], ["a", "B", "", "L6", "Comuni"]], "ripetuti"),
        ([["a b", "A", "", "L6", "Comuni"], ["c", "C", "", "L6", "Comuni"]], "non validi"),
        ([["a", "", "", "L6", "Comuni"], ["b", "B", "", "L6", "Comuni"]], "senza denominazione"),
        ([["a", "A", "", "X9", ""], ["b", "B", "", "L6", "Comuni"]], "categorie senza nome"),
    ],
)
def test_verify_rejects_bad_registry(rows, message):
    with pytest.raises(SystemExit, match=message):
        registry.verify(rows, min_rows=2)


def test_verify_accepts_good_registry():
    registry.verify([["a", "A", "", "L6", "Comuni"], ["b", "B", "BB", "L4", "Regioni"]], min_rows=2)


def run_main(monkeypatch, out: Path, text: str, min_rows: int) -> None:
    pages = {registry.IPA_CSV: text, registry.CATEGORIES_CSV: CATEGORIES}
    monkeypatch.setattr(registry, "download", lambda url: pages[url])
    monkeypatch.setattr(sys, "argv", ["build_ipa_registry.py", str(out), "--min-rows", str(min_rows)])
    registry.main()


def test_main_writes_verified_registry(monkeypatch, tmp_path):
    out = tmp_path / "ipa-enti.csv"
    run_main(monkeypatch, out, ipa_text("b,B,,L4,", "a,A,AA,L6,"), min_rows=2)
    assert out.read_text(encoding="utf-8").splitlines() == [
        "codice_ipa,denominazione,acronimo,categoria,nome_categoria",
        "a,A,AA,L6,Comuni",
        "b,B,,L4,Regioni",
    ]


def test_main_leaves_existing_file_when_verification_fails(monkeypatch, tmp_path):
    out = tmp_path / "ipa-enti.csv"
    out.write_text("copia buona\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        run_main(monkeypatch, out, ipa_text("a,A,,L6,"), min_rows=2)
    assert out.read_text(encoding="utf-8") == "copia buona\n"
