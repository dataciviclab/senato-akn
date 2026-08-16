# Decisione: ingest via clone git (git_source)

Data: 2026-08-16
Status: adottata

## Problema

L'estrazione HTTP per-file (1 richiesta per XML) era il collo e la GitHub
**tree API tronca** le risposte oltre una soglia:

- `git/trees/<sha>?recursive=1` restituisce `"truncated": true` per i tree
  grandi (Leg19 → solo 73.873 entry su ~153k reali).
- Conseguenza: l'estrazione scopriva solo **~46% dei file** (ddlpres 1.095 su
  1.978 reali). I numeri dell'audit basati sulla tree API erano tutti
  sottostimati (~2×).

## Misurazioni (Leg19/ddlpres, 1.978 file reali)

| Approccio | Tempo |
|---|---|
| HTTP sequenziale | ~12 min (0,64 s/file) |
| HTTP parallelo (8 worker) | ~2,6 min |
| **Git** (clone blob:none + sparse, poi parse da disco) | **9-13 s** |
| Clone iniziale Leg19 (2,1 GB via pack) | ~3,4 min (una tantum) |
| `git fetch` (aggiornamento delta) | ~11 s |
| Full repo (1M XML, tutte le legislature) | ~14 GB via pack |

Il git pack è ~30× più veloce delle richieste singole e risolve la truncation
(il working tree è completo e autoritativo).

## Design

- `git_source.ensure_repo`: `clone --depth 1 --filter=blob:none --sparse
  --no-checkout` + sparse-checkout della legislatura; aggiornamento con
  `fetch` + `reset --hard FETCH_HEAD`. Repo locale senza remote (test/copie)
  usato così com'è.
- `git_source.list_entries`: elenco path→sha da `git ls-tree` (completo,
  path relativi alla legislatura — compatibili con `parse_xml`).
- `run_extract`: parse da disco (~1 ms/file, parallelo); manifest path→sha
  + `--incremental` = delta (merge col parquet precedente).

## Rimosso (obsoleto)

- `fetch_content`/`discover_*`/`_dir_sha` (tree API + HTTP)
- `scripts/extract_leg19_ddlpres.py`, `scripts/explore_leg19.py`
- dipendenza `lab-connectors` (non più usata)
- flag `--cache`/`--sleep-ms` (sostituiti da `--repo-dir`/`--incremental`)

## Trade-off

- **Pro**: completezza, velocità, delta gratuito (lo stato è il manifest).
- **Contro**: richiede `git` sul runner (ubiquitous); il clone iniziale di una
  legislatura è ~minuti; per più legislature il disco cresce (~2 GB/leg).
- **Open**: la persistenza del clone su runner effimero (actions/cache o GCS)
  è il follow-up del workflow `pipeline` (mode incremental).
