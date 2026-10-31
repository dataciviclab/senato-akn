# senato-akn — Il lavoro del Senato in formato strutturato

[![test](https://github.com/dataciviclab/senato-akn/actions/workflows/test.yml/badge.svg)](https://github.com/dataciviclab/senato-akn/actions/workflows/test.yml)

**La decretazione d'urgenza pesa circa un terzo del testo legislativo del Senato pur essendo meno del 10% degli atti. I bilanci, quasi invisibili nel conteggio, pesano oltre dieci volte il loro numero.**

Questo progetto estrae ed esplora il corpus legislativo del Senato in formato
Akoma Ntoso (XML) per misurare il lavoro legislativo per **peso documentale**,
struttura e contenuto dei testi — non solo per numero di atti.

## Cosa contiene

| | |
|---|---|
| **Fonte** | SenatoDellaRepubblica/AkomaNtosoBulkData (clone git, XML Akoma Ntoso) |
| **Legislature** | Leg14–Leg19 (2001–oggi) |
| **Disegni di legge** | ~7.700 `ddlpres` (Leg16–Leg19) |
| **Messaggi e commissione** | ~1.350 `ddlmess` (Leg17–Leg19) + ~900 `ddlcomm` (Leg16–Leg19) |
| **Emendamenti** | ~386.000 Aula (`emend`) + ~378.000 Commissione (`emendc`) |
| **Dibattito** | ~370.000 interventi (Aula `resaula` + Commissione `sommcomm`) |
| **Totale** | ≈1,14 milioni di righe pubblicate, ~11 GB di XML upstream |

Conteggi arrotondati: i valori puntuali dello snapshot corrente sono in
[`registry/registry.json`](registry/registry.json) (`output_rows.clean`).
Gli emendamenti sono deduplicati dalle copie che l'upstream replica in più
directory `Atto` (−24% righe, fino a 57 copie sullo stesso documento); la
`fase` (S.NNN) è la chiave dell'atto. Corpus e dibattito restano a livello di
documento/intervento.

La copertura non è uniforme: Leg14–15 hanno solo emendamenti, Leg16 14
`ddlpres` e 9 `ddlcomm`, Leg17 ha 1 sola seduta d'Aula pubblicata (3 resoconti
nell'upstream) e nessun resoconto di Commissione. Il dettaglio è in
[`project.yml`](project.yml).

## Il finding principale

Nel corpus `Leg19/ddlpres` poche famiglie concentrano una quota sproporzionata
della massa documentale:

| Famiglia | % documenti | % testo | Rapporto |
|---|---|---|---|
| **Bilancio** | <1% | ≈8% | **≈11×** |
| **Decreto-like** | ≈9% | ≈1/3 | **≈3,7×** |
| Delega | ≈7% | ≈9% | ≈1,3× |
| Istituzione | ≈14% | ≈7% | ≈0,5× |
| Ratifica | ≈5% | ≈1% | ≈0,2× |

Le cifre sono volutamente **arrotondate e senza data**: il corpus si aggiorna
ogni mese (schedule il 1°), quindi i valori puntuali decadono. Lo snapshot è
tracciato da `updated_at` in [`registry/registry.json`](registry/registry.json);
la tabella esatta si rigenera in un comando:

```bash
make findings ARGS="--parquet https://storage.googleapis.com/dataciviclab-clean/senato-akn/senato_corpus/2026/senato_corpus_2026_clean.parquet"
```

Le famiglie sono multi-valore (`delega;norme_generali`): un documento può
appartenere a più famiglie, quindi le percentuali **non sono esclusive** e la
loro somma può superare il 100%. In alcuni mesi i decreti superano il 60% del
testo: è accaduto ad aprile 2024 (≈67%) e giugno 2023 (≈63%).

## Esempi di domande

- **Quanto pesa davvero la decretazione d'urgenza rispetto alle leggi ordinarie?**
- **Quali tipologie di atti producono più volume testuale per singolo documento?**
- **Come varia il lavoro legislativo mese per mese?**
- **Quali proposte di legge diventano effettivamente legge?**
- **Chi parla, e quanto, nelle aule e nelle commissioni?**

## Tre modi per accedere ai dati

### 1. Catalogo e MCP del Lab

- [Explorer](https://explorer.dataciviclab.org): `senato_corpus`, `senato_dibattito`
  e `senato_emendamenti` sono nel catalogo e nella ricerca
- MCP: `gcs_query(slug="senato_corpus", sql="SELECT count(*) AS n FROM _data")`

### 2. SQL sui parquet pubblicati

Clean su `gs://dataciviclab-clean/senato-akn/`, mart aggregati su
`gs://dataciviclab-mart/senato-akn/` (percorsi canonici in
`registry/registry.json`), leggibili via HTTPS:

```python
import duckdb
duckdb.sql("""
    SELECT famiglia, n_documenti, pct_testo
    FROM read_parquet('https://storage.googleapis.com/dataciviclab-mart/senato-akn/senato_corpus/2026/mart_famiglie.parquet')
    ORDER BY pct_testo DESC
""").show()
```

### 3. Estrazione locale

La sorgente è un clone git dell'upstream (`git_source`): il primo run clona
e materializza la legislatura (download via pack, ~2 min), i successivi fanno
`git fetch` (delta) e parsano da disco (~1 ms/file).

```bash
pip install -e ".[dev]"
python3 scripts/extract.py              # Leg19/ddlpres (clone git + parse)
python3 scripts/extract.py --tipologie ddlpres,emend,emendc,ddlmess,ddlcomm
python3 scripts/extract.py --incremental   # delta: solo i file cambiati
```

## Partecipa

**Hai una domanda sul lavoro del Senato?** Apri una
[Discussion](https://github.com/orgs/dataciviclab/discussions/new?category=Domanda) —
per bug e parsing, issue e PR sono aperte.

## Stato

- **Ingest via git** (`git_source`): clone `blob:none` + sparse. La tree API
  di GitHub tronca oltre ~100k entry (via HTTP si copriva ~46% dei file);
  con git il corpus è completo.
- **Multi-legislatura**: Leg14–Leg19 estratte e unificate; `sparse-checkout add`
  per aggiungere legislature senza perdere le altre.
- **Parser**: `ddlpres`, `ddlmess`, `ddlcomm`, `emend`, `emendc`, `resaula`,
  `sommcomm` (namespace CSD02 per Leg13–Leg16, CSD03 per Leg17+).
- **Layer toolkit**: 3 dataset raw→clean→mart su GCS, con bridge verso
  `senato_ddl` (atto_num) e `senato_anagrafica` (persona_id).
- **Refresh**: mensile e completo (clone + parse, ~25 min): i parquet derivati
  non sopravvivono al runner, quindi l'estrazione è full, non incrementale.

**Prossimi passi**: bridge dibattito → interventi in open-politica; incrocio
proposto (Senato) vs legge vigente con italia-corpus — [F5](https://github.com/dataciviclab/senato-akn/issues/15).

## Architettura

```
scripts/          # extract.py, union_legislatures.py, findings.py
senato_akn/       # core: extract, git_source, parser, classifier
datasets/         # 3 dataset.yml (senato-corpus, senato-dibattito, senato-emendamenti)
dashboard/        # Streamlit (7 pagine) su GCS via lab-connectors
data/raw/akn/     # clone git upstream (gitignored) — il "download" è via pack
data/derived/     # parquet + manifest generati (gitignored, effimeri)
.github/workflows/# test (CI), pipeline (estrazione → toolkit → GCS → registry)
```

## Licenza

MIT — salvo la fonte originale (Senato della Repubblica, CC BY 3.0).

Progetto del [DataCivicLab](https://github.com/dataciviclab) — corpus-based
autonomo, perché il formato XML Akoma Ntoso richiede un approccio diverso
dalle pipeline tabellari standard.
