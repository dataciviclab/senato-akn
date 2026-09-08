# Stato del progetto

Data: 2026-09-08
Slug: `senato-akn`
Stato: `active`
Kind: `corpus-project`

## Scope attuale

- fonte: `SenatoDellaRepubblica/AkomaNtosoBulkData` (clone git, `git_source`)
- legislature: `Leg14`–`Leg19` (multi-legislatura)
- tipologie parsate: `ddlpres`, `emend`, `emendc`, `ddlmess`, `ddlcomm`, `resaula`, `sommcomm`
- unità di record: documento

## Artefatti canonici

Script:
- `scripts/extract.py` (estrazione da git, `--incremental` per il delta)
- `scripts/union_legislatures.py` (unione parquet per-legislatura)

Derived (gitignored, GitHub Artifact):
- `data/derived/leg{leg}_{tipi}_v0.parquet` (parquet zstd + `.manifest.json`)
- `data/derived/leg_unified_{tipi}_v0.parquet` (unificati multi-legislatura)
- `data/raw/akn/` — clone git upstream (la "cache" dei file XML)

Toolkit:
- `datasets/senato-corpus/` — layer raw→clean→mart
- `datasets/senato-dibattito/` — layer raw→clean→mart
- `datasets/senato-emendamenti/` — layer raw→clean→mart

## Dashboard

7 pagine Streamlit:
- Panoramica, Famiglie, Emendamenti, Sedute, Oratori, Scheda Atto, SQL
- Fonte dati: lab_connectors.duckdb.queries (path resolution GCS/locale)
- Cache: `@st.cache_data(ttl=3600)` su tutte le query

## Cosa regge

- ingest completa del corpus via git (la GitHub tree API tronca oltre ~100k entry)
- multi-legislatura: Leg14–Leg19 con union automatica
- layer toolkit per 3 dataset: raw→clean→mart
- bridge a senato_ddl (atto_num → fase) e senato_anagrafica (senatore_id → persona_id)

## Prossimi passi

- Validare i fix eseguendo la pipeline completa (extract → clean → mart)
- Materializzare nodi mancanti nel graph (senatore, norma)
- Estendere coverage di `urn_normattiva` in open-politica
