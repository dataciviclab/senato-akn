# Stato del progetto

Data: 2026-10-31
Slug: `senato-akn`
Stato: `active`
Kind: `corpus-project`

## Scope attuale

- fonte: `SenatoDellaRepubblica/AkomaNtosoBulkData` (clone git, `git_source`)
- legislature: `Leg14`–`Leg19`
- tipologie parsate: `ddlpres`, `emend`, `emendc`, `ddlmess`, `ddlcomm`, `resaula`, `sommcomm`
- unità di record: documento (corpus/emendamenti), intervento (dibattito)
- refresh: mensile, completo (clone + parse, ~25 min)

## Copertura reale

| Tipologia | Legislature | Note |
|---|---|---|
| `ddlpres` | Leg16–Leg19 | Leg16 solo 14 atti |
| `ddlmess`, `ddlcomm` | Leg17–Leg19 | — |
| `emend`, `emendc` | Leg14–Leg19 | — |
| `resaula` | Leg17–Leg19 | Leg17: 3 file upstream (1 seduta) |
| `sommcomm` | Leg18–Leg19 | Leg17: 0 file upstream |

## Artefatti canonici

Script:
- `scripts/extract.py` (estrazione da git, `--incremental` per il delta)
- `scripts/union_legislatures.py` (unione parquet per-legislatura)
- `scripts/findings.py` (ricalcola il finding per famiglia — `make findings`)

Pubblicato su GCS (clean + mart):
- `senato_corpus` — atti (ddlpres/ddlmess/ddlcomm) con famiglia, testo, articoli
- `senato_dibattito` — un intervento per riga, con oratore
- `senato_emendamenti` — un emendamento per riga, con fase dell'atto

Locale (gitignored, effimero):
- `data/derived/leg{leg}_{tipi}_v0.parquet` + `.manifest.json`
- `data/raw/akn/` — clone git upstream

Toolkit:
- `datasets/senato-corpus/`, `datasets/senato-dibattito/`, `datasets/senato-emendamenti/`
- `mart_famiglie` esplode `famiglia` (multi-valore): quote non esclusive

## Dashboard

7 pagine Streamlit (Panoramica, Famiglie, Emendamenti, Sedute, Oratori,
Scheda Atto, SQL). Risolve i parquet da GCS con prefisso `senato-akn/` e anno
letto dal registry; cache 1h.

## Cosa regge

- ingest completa del corpus via git (la tree API tronca oltre ~100k entry)
- multi-legislatura con union automatica
- layer toolkit per 3 dataset, pubblicati su GCS e consumati da open-politica,
  legal-graph ed Explorer
- bridge a `senato_ddl` (atto_num) e `senato_anagrafica` (persona_id)

## Debito noto

- `senato_akn/summarize.py` non è più usato (target `make summarize` no-op)
- 10 documenti Leg17 con `work_date` pre-2013 (probabile errore upstream)
- ruff/mypy non sono in CI (2 + 7 errori noti)
- `leg_unified_ddlpres_v0.parquet` contiene anche ddlmess/ddlcomm (nome storico)

## Prossimi passi

- F5: incrocio proposto (Senato) vs legge vigente (italia-corpus)
- pulizia debito noto (vedi sopra)
