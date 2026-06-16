"""Classificazione dei documenti legislativi in famiglie tematiche.

Logica pura: prende un titolo, restituisce una lista di famiglie.
Nessun I/O, nessuna dipendenza esterna.

Le regole sono ordinate per specificità: le keyword più specifiche prima,
in modo che match più precisi abbiano priorità su quelli generici.
Un documento può avere più famiglie (es. "delega al governo per il lavoro").
"""
from __future__ import annotations

# Regole: (keyword, label) ordinate per specificità decrescente.
# Vengono valutate tutte: un documento può stare in più famiglie.
# Usa dict.fromkeys per deduplicare preservando l'ordine.
_RULES: list[tuple[str, str]] = [
    # -- Bilancio (pochi atti, molto specifici)
    ("bilancio di previsione", "bilancio"),
    ("rendiconto generale", "bilancio"),
    ("assestamento del bilancio", "bilancio"),
    # -- Decreto-legge e urgenza
    ("decreto-legge", "decreto_like"),
    ("decretolegge", "decreto_like"),          # senza trattino nei titoli reali
    ("conversione in legge", "decreto_like"),
    ("conversione del decreto", "decreto_like"),
    ("disposizioni urgenti", "decreto_like"),   # strettamente collegato
    ("misure urgenti", "decreto_like"),
    # -- Ratifiche internazionali
    ("ratifica", "ratifica"),
    ("esecuzione del", "ratifica"),             # "esecuzione del trattato/protocollo/accordo"
    # -- Delega al governo
    ("delega al governo", "delega"),
    ("deleghe al governo", "delega"),
    ("delega", "delega"),                       # catch generico
    # -- Codici e testi unici
    ("codice penale", "codice"),
    ("codice della strada", "codice"),
    ("codice civile", "codice"),
    ("codice del processo", "codice"),
    ("codice dei contratti", "codice"),
    ("codice dell'amministrazione", "codice"),
    ("codice", "codice"),                       # altri codici
    ("testo unico", "codice"),
    # -- Istituzioni e organi
    ("istituzione", "istituzione"),
    ("costituzione della", "istituzione"),      # "costituzione della commissione..."
    # -- Lavoro
    ("lavoro", "lavoro"),
    ("occupazione", "lavoro"),
    ("lavoratori", "lavoro"),
    ("previdenza", "lavoro"),                   # previdenza sociale
    # -- Modifiche a leggi esistenti
    ("modifiche alla legge", "modifica"),
    ("modifiche al decreto", "modifica"),
    ("modifica all'articolo", "modifica"),
    ("modifiche all'articolo", "modifica"),
    ("modificazioni alla", "modifica"),
    ("modifica della legge", "modifica"),
    ("modifiche della legge", "modifica"),
    ("abrogazione", "modifica"),
    ("sostituzione", "modifica"),
    # -- Proroghe
    ("proroga", "proroga"),
    ("differimento", "proroga"),
    ("riapertura dei termini", "proroga"),
    # -- Misure e disposizioni generali
    ("norme in materia", "norme_generali"),
    ("norme per", "norme_generali"),
    ("norme concernenti", "norme_generali"),
    ("disciplina", "norme_generali"),
    ("riordino", "norme_generali"),
    ("riorganizzazione", "norme_generali"),
    ("riforma", "norme_generali"),
    ("semplificazione", "norme_generali"),
    ("coordinamento", "norme_generali"),
    ("disposizioni in materia", "norme_generali"),
    ("disposizioni per", "norme_generali"),
    ("misure", "norme_generali"),
    # -- Interpretazione autentica
    ("interpretazione autentica", "chiarimento"),
    ("interpretazione", "chiarimento"),
    ("disposizioni interpretative", "chiarimento"),
]


def classify(title: str) -> list[str]:
    """Classifica un titolo in famiglie legislative.

    Args:
        title: Titolo del documento (``doc_title`` o ``short_title``).

    Returns:
        Lista di label di famiglia (può essere vuota se nessuna regola matcha).
    """
    t = title.lower()
    return list(dict.fromkeys(
        label for keyword, label in _RULES if keyword in t
    ))
