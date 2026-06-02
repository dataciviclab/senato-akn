# Stato del progetto

Data: 2026-06-02
Slug: `senato-akn`
Stato: `public-exploration`
Kind: `corpus-project`

## Scope attuale

- fonte: `SenatoDellaRepubblica/AkomaNtosoBulkData`
- legislatura: `Leg19`
- tipologia: `ddlpres`
- unita' di record: documento

## Artefatti canonici

Script:
- `scripts/extract_leg19_ddlpres.py`
- `scripts/build_summaries.py`

Derived:
- `data/derived/leg19_ddlpres_v0.csv`
- `data/derived/leg19_ddlpres_v0_nonzero.csv`
- `data/derived/families_summary.csv`
- `data/derived/decreto_monthly_summary.csv`

## Cosa regge

- accesso reale alla fonte ufficiale
- parsing locale del corpus `Leg19/ddlpres`
- corpus document-level pulito con `1058` righe non vuote
- summary locali abbastanza leggibili per domande esplorative

## Finding interno piu' forte

Poche famiglie di testi concentrano una quota sproporzionata della massa documentale.

In particolare:
- `decreto_like`: `6.99%` degli atti ma `29.96%` del testo
- `bilancio`: `0.57%` degli atti ma `7.58%` del testo

## Prossimo passo

Validare il finding via discussione pubblica e valutare espansione:
- ad altre tipologie documentali (emend, sommcomm)
- ad altre legislature (Leg17, Leg18)
- o integrazione con flussi Camera (votazioni, atti di controllo)
