"""Classificazione dei documenti legislativi in famiglie tematiche.

Logica pura: prende un titolo, restituisce una lista di famiglie.
Nessun I/O, nessuna dipendenza esterna.
"""
from __future__ import annotations

# Regole di classificazione: (keyword, label)
# Una lista di keyword *ordinali* — la prima match viene assegnata.
# Se servono match multipli (un documento può stare in più famiglie),
# si possono ripetere label diverse.
_RULES: list[tuple[str, str]] = [
    ("bilancio di previsione", "bilancio"),
    ("rendiconto", "bilancio"),
    ("decreto-legge", "decreto_like"),
    ("conversione in legge", "decreto_like"),
    ("ratifica", "ratifica"),
    ("delega", "delega"),
    ("istituzione", "istituzione"),
    ("lavoro", "lavoro"),
]


def classify(title: str) -> list[str]:
    """Classifica un titolo in famiglie legislative.

    Args:
        title: Titolo del documento (``doc_title`` o ``short_title``).

    Returns:
        Lista di label di famiglia (può essere vuota se nessuna regola matcha).
    """
    t = title.lower()
    # dict.fromkeys preserva ordine e deduplica
    return list(dict.fromkeys(label for keyword, label in _RULES if keyword in t))
