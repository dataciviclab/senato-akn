# Stato del progetto

Data: 2026-08-16
Slug: `senato-akn`
Stato: `public-exploration`
Kind: `corpus-project`

## Scope attuale

- fonte: `SenatoDellaRepubblica/AkomaNtosoBulkData` (clone git, `git_source`)
- legislatura: `Leg19` (149.059 file XML, ~2,1 GB)
- tipologie parsate: `ddlpres`, `emend`, `emendc`, `ddlmess`, `ddlcomm`
  (63.082 file) — `resaula`/`sommcomm` (dibattito) in attesa del parser `an:debate`
- unità di record: documento

## Artefatti canonici

Script:
- `scripts/extract.py` (estrazione da git, `--incremental` per il delta)
- `scripts/build_summaries.py` (aggregazioni famiglia/mese)

Derived (gitignored, GitHub Artifact):
- `data/derived/leg19_<tipi>_v0.parquet` (parquet zstd + `.manifest.json`)
- `data/raw/akn/` — clone git upstream (la "cache" dei file XML)

Toolkit:
- `datasets/senato-corpus/` — layer raw→clean→mart (raw: parquet derivato)

## Cosa regge

- ingest completa del corpus via git (la GitHub tree API tronca oltre ~100k
  entry: l'estrazione HTTP scopriva solo ~46% dei file)
- ddlpres completo: **1.978 righe** (era 1.059 con la discovery troncata)
- delta incrementale (`--incremental`): manifest path→sha + merge col parquet
  precedente — funziona su runner effimero (lo stato è il manifest, ~94 KB)
- layer toolkit `senato_corpus`: raw qs=100, clean qs=95, mart qs=100 (2/2),
  1.889 atti con testo (1.891 totali nel mart_per_atto)

## Finding

Poche famiglie di testi concentrano una quota sproporzionata del testo:
`decreto_like` ~33% del testo, `bilancio` ~8% — coi numeri del corpus completo.

## Prossimo passo

- workflow `sync` incrementale (publish parquet+manifest)
- GCS publish + registry (decisione credenziali)
- parser `an:debate` per i resoconti (resaula, sommcomm)
- incrocio con italia-corpus: proposto (Senato) vs legge (vigente)
