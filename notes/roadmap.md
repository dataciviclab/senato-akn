# Roadmap — collegare i pezzi (senato-akn → open-politica → diritto)

Data: 2026-08-16
Stato: pianificazione — ogni fase è tracciata come issue

## Principio guida (dai dati misurati)

L'operazione costosa è il download/parse XML (risolta con git: clone via
pack + parsing da disco ~1 ms/file). Tutto il resto sono join tabellari
economici su parquet. Ogni pezzo pubblica parquet su **GCS** (il bus), gli
altri lo consumano — nessuno ri-estrae.

## Fasi

- **F0 — Consolidare senato-akn**: merge PR #10 (ingest git + corpus
  completo + layer toolkit). Aprire i follow-up come issue.
- **F1 — Stabilizzare e GCS** (senato-akn): workflow `sync` incrementale,
  GCS publish (parquet + manifest), registry, estensione del layer
  `senato_corpus` a tutte le tipologie parsate.
- **F2 — open-politica consuma il corpus** (dopo GCS): compose
  `senato_corpus_parlamento` con raw `http_file` GCS (niente sibling
  checkout), join `atto_num` ↔ `senato_ddl`, arricchimento `decreti-legge`
  col peso documentale.
- **F3 — Emendamenti → iter**: parsi emend+emendc, mart
  `emendamenti_per_atto` (n°, target, testo), hook su `fase` (S.NNN);
  KPI "intensità emendativa" in open-politica.
- **F4 — Dibattito → interventi**: parser `an:debate` (resaula/sommcomm),
  bridge su `osr:Persona` (stessa namespace di `senato_anagrafica`);
  testo degli interventi in open-politica.
- **F5 — Proposto ↔ vigente**: senato-akn (proposto) ↔ italia-corpus
  (vigente, Normattiva): "questo ddl è diventato legge? cosa è cambiato?".
  Da fare a valle, con i dati stabili.
- **F6 — Costituzione → processo**: estendere `costituzione-mapping.yaml`
  agli articoli del processo legislativo (gli indicatori già leggono il
  registry del Lab).

## Dipendenze

```
F0 merge #10
  └→ F1 GCS+sync (stabilizza akn)
       └→ F2 open-politica legge GCS (niente sibling)
       ├→ F3 emendamenti → iter
       └→ F4 dibattito → interventi
F1 + italia-corpus → F5 proposto↔vigente
F2 + F3/F4 → F6 Costituzione → processo
```

## Ponti tra i dataset (le chiavi)

| Ponte | Da | A | Chiave |
|---|---|---|---|
| Testo atti → iter | senato_corpus | senato_ddl | `atto_num` ↔ `ddl_url` (/ddl/N) |
| Emendamenti → atto | emend/emendc | senato_ddl | `fase` (S.NNN) / FRBRuri `Emend/S/N/...` |
| Dibattito → persona | resaula/sommcomm | senato_anagrafica | `osr:Persona` (#pNNNN) |
| Dibattito → commissione | sommcomm | senato_commissioni | commissione |
| Proposto → vigente | senato-akn | italia-corpus | numero legge / titolo |
