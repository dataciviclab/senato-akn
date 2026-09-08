"""Classificazione documenti legislativi in famiglie.

Regex semplice su tipologia + doc_title. 11 famiglie.
Non richiede ML — basta una mappa regole.
"""
from __future__ import annotations

import re

# Regole: (keyword, label) ordinate per specificità decrescente
_RULES: list[tuple[str, str]] = [
    # Bilancio
    ("bilancio di previsione", "bilancio"),
    ("rendiconto generale", "bilancio"),
    ("assestamento del bilancio", "bilancio"),
    # Decreto-legge e urgenza
    ("decreto-legge", "decreto_like"),
    ("conversione in legge", "decreto_like"),
    ("disposizioni urgenti", "decreto_like"),
    ("misure urgenti", "decreto_like"),
    # Ratifiche
    ("ratifica", "ratifica"),
    ("esecuzione del", "ratifica"),
    # Delega
    ("delega al governo", "delega"),
    ("deleghe al governo", "delega"),
    ("delega", "delega"),
    # Codici e testi unici
    ("codice", "codice"),
    ("testo unico", "codice"),
    # Istituzioni
    ("istituzione", "istituzione"),
    # Lavoro
    ("lavoro", "lavoro"),
    ("occupazione", "lavoro"),
    ("lavoratori", "lavoro"),
    ("previdenza", "lavoro"),
    # Modifiche
    ("modifiche alla legge", "modifica"),
    ("modifiche al decreto", "modifica"),
    ("modifica all'articolo", "modifica"),
    ("abrogazione", "modifica"),
    ("sostituzione", "modifica"),
    # Proroghe
    ("proroga", "proroga"),
    ("differimento", "proroga"),
    # Norme generali (catch-all)
    ("norme in materia", "norme_generali"),
    ("norme per", "norme_generali"),
    ("disciplina", "norme_generali"),
    ("riordino", "norme_generali"),
    ("riforma", "norme_generali"),
    ("semplificazione", "norme_generali"),
    ("disposizioni in materia", "norme_generali"),
    ("disposizioni per", "norme_generali"),
    ("misure", "norme_generali"),
]


def classify(title: str) -> list[str]:
    """Classifica un titolo in famiglie legislative.

    Args:
        title: Titolo del documento (doc_title o tipologia).

    Returns:
        Lista di label di famiglia (può essere vuota se nessuna regola matcha).
    """
    t = title.lower()
    return list(dict.fromkeys(
        label for keyword, label in _RULES if keyword in t
    ))
