"""Codici IPA degli enti del RNDT: vocabolario offline e filtro sul prefisso dell'id (#38).

Il prefisso dell'id di ogni scheda è il codice IPA dell'ente titolare (AgID,
2026-09-04). Il campo distingue maiuscole e minuscole e i prefissi non sono
uniformi (`PCM` 731 schede, `pcm` 0; `R_SARDEG` 404 e `r_sardeg` 362), quindi il
filtro usa le classi di lettere. Il vocabolario lo rigenera
`scripts/build_ipa_vocabulary.py` prima di ogni release.
"""

from __future__ import annotations

import copy
import json
import re
from functools import cache
from importlib import resources
from typing import Any

IPA_FIELD = "apiso_Identifier_s"
_CODE_RE = re.compile(r"^[A-Za-z0-9_]+$")


@cache
def _vocabulary() -> dict[str, Any]:
    text = resources.files("openrndt").joinpath("data/ipa.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


def ipa_vocabulary() -> list[dict[str, Any]]:
    """I codici del vocabolario, dal più grande: ``codice``, ``ipa`` (è nell'Indice PA),
    ``nome_ipa``, ``acronimo``, ``enti`` (i nomi in ``EnteResponsabile_s``), ``schede``, ``grafie``."""
    # Copia profonda: chi modifica `enti` o `grafie` non tocca la cache.
    return copy.deepcopy(_vocabulary()["codici"])


def ipa_vocabulary_date() -> str:
    """Data di generazione del vocabolario (``yyyy-mm-dd``)."""
    return str(_vocabulary()["generato"])


def find_ipa(text: str) -> list[dict[str, Any]]:
    """Codici il cui codice, nome IPA, acronimo o nome di ente contiene ``text`` (senza maiuscole)."""
    needle = text.strip().lower()
    if not needle:
        return []
    found = []
    for code in ipa_vocabulary():
        names = [code["codice"], code["nome_ipa"] or "", code["acronimo"] or "", *code["enti"]]
        if any(needle in name.lower() for name in names):
            found.append(code)
    return found


def _prefix_regex(code: str) -> str:
    letters = "".join(f"[{c.lower()}{c.upper()}]" if c.isalpha() else c for c in code)
    return f"/{letters}:.*/"


def ipa_clause(codes: str) -> str:
    """Clausola Lucene per uno o più codici IPA separati da virgola, senza distinzione di maiuscole.

    ``r_sardeg`` → ``apiso_Identifier_s:/[rR]_[sS]…:.*/`` (766 schede, contro 362 con il
    solo minuscolo). Un codice con caratteri diversi da lettere, cifre e ``_`` è un errore.
    """
    items = [c.strip() for c in codes.split(",") if c.strip()]
    if not items:
        raise ValueError("`ipa` non può essere vuoto.")
    bad = [c for c in items if not _CODE_RE.match(c)]
    if bad:
        raise ValueError(f"Codice IPA non valido: {', '.join(bad)} (solo lettere, cifre e `_`).")
    regexes = [_prefix_regex(c) for c in items]
    return f"{IPA_FIELD}:{regexes[0]}" if len(regexes) == 1 else f"{IPA_FIELD}:({' OR '.join(regexes)})"
