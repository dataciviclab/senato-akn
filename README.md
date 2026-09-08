# senato-akn — Il lavoro del Senato in formato strutturato

**La decretazione d'urgenza occupa quasi un terzo del testo legislativo del Senato, pur essendo solo il 7% degli atti. Lo vediamo perché misuriamo il lavoro parlamentare non per numero, ma per peso.**

Questo progetto estrae ed esplora il corpus legislativo del Senato della
Repubblica in formato standard Akoma Ntoso (XML). L'obiettivo è capire cosa
contiene davvero il lavoro legislativo — misurato per **peso documentale**,
struttura e contenuto dei testi.

## Cosa contiene

| | |
|---|---|
| **Fonte** | SenatoDellaRepubblica/AkomaNtosoBulkData |
| **Legislature** | Leg14–Leg19 (2001-oggi) |
| **Documenti estratti** | ddlpres (7.654) · emend (1.002.476) · emendc ( vari) · ddlmess (952) · ddlcomm (699) |
| **Dibattito** | resaula (1.753) · sommcomm (13.865) — parser `an:debate` |
| **Totale** | ~1.183.000 file XML, ~14 GB su disco |

## Finding principale

Nel corpus `Leg19/ddlpres`, poche famiglie di testi concentrano una quota
sproporzionata della massa documentale:

| Famiglia | % atti | % testo | Rapporto |
|---|---|---|---|
| **Decreto-like** (decreti-legge, conversioni) | 6.99% | 29.94% | 4.28× |
| **Bilancio** | 0.57% | 7.58% | 13.37× |
| **Delega** | 6.33% | 8.96% | 1.42× |
| **Istituzione** | 14.08% | 7.55% | 0.54× |
| **Ratifica** | 5.01% | 1.09% | 0.22× |

**I bilanci, quasi invisibili nel conteggio (0.57%), pesano 13× più del loro numero.**
In alcuni mesi, i decreti superano il 60% del testo totale pur essendo meno del 15% degli atti.

## Esempi di domande

- **Quanto pesa davvero la decretazione d'urgenza rispetto alle leggi ordinarie?**
- **Quali tipologie di atti producono più volume testuale per singolo documento?**
- **Come varia il lavoro legislativo mese per mese?**
- **Cosa c'è nei 43.185 emendamenti di Commissione non ancora parsati?**
- **Quali proposte di legge diventano effettivamente legge?**

## Tre modi per accedere ai dati

### 1. Via GitHub Artifact

I parquet derivati sono disponibili come GitHub Artifact del workflow `pipeline`
(mode `full` → Actions → download). Non sono in git.

### 2. Via SQL su parquet

```python
import duckdb
duckdb.sql("""
    SELECT famiglia, COUNT(*) AS n_atti, SUM(text_len) AS volume
    FROM read_parquet('data/derived/leg19_ddlpres_v0.parquet')
    GROUP BY famiglia
    ORDER BY volume DESC
""").show()
```

### 3. Via estrazione locale

La sorgente è un clone git dell'upstream (`git_source`): il primo run clona
e materializza la legislatura (download via pack, ~2 min), i successivi
fanno `git fetch` (delta) e parsano da disco (~1 ms/file).

```bash
pip install -e ".[dev]"
python3 scripts/extract.py              # Leg19/ddlpres (clone git + parse)
python3 scripts/extract.py --tipologie ddlpres,emend,emendc,ddlmess,ddlcomm  # full parsabile
python3 scripts/extract.py --incremental   # delta: solo i file cambiati (manifest + snapshot)
```

## Partecipa

- **Hai una domanda sul lavoro del Senato?** Apri una [Discussion](https://github.com/orgs/dataciviclab/discussions/new?category=Domanda)
- **Vuoi contribuire?** Issues per bug, PR per script e parsing

## Stato

- **Ingest via git** (`git_source`): clone `blob:none` + sparse della
  legislatura. La GitHub tree API tronca oltre ~100k entry — l'estrazione
  HTTP scopriva solo ~46% dei file; con git il corpus è completo.
- **Multi-legislatura**: Leg14–Leg19 estratte e unificate. Clone condiviso
  con `sparse-checkout add` per aggiungere legislature senza perdere le
  precedenti. Leg14–Leg15 hanno solo emendamenti; Leg16 ha 14 ddlpres;
  Leg17–Leg19 hanno il corpus completo.
- **Estrazione**: clone ~5-6 min (una tantum per tutte le legislature),
  fetch delta ~11 s, parsing ~1 ms/file. Delta incrementale via
  `--incremental` (manifest path→sha + merge del parquet).
- **Layer toolkit**: 3 dataset (`senato-corpus`, `senato-dibattito`,
  `senato-emendamenti`) — raw→clean→mart. Bridge verso `senato_ddl` (atto_num)
  e `senato_anagrafica` (persona_id). Pubblicati su GCS (clean + mart).
- **Dibattito**: parser `an:debate`, una riga per intervento con oratore
  (bridge `osr:Persona` → `senato_anagrafica`). ~360k interventi tra Aula e
  Commissione (Leg17–Leg19).
- **Namespace**: parser supporta CSD02 (Leg13–Leg16) e CSD03 (Leg17+).

## Prossimi passi

1. Bridge dibattito → interventi in open-politica (testo accanto ai metadati)
2. Incrocio con italia-corpus: proposto (Senato) vs legge (vigente) — [F5](https://github.com/dataciviclab/senato-akn/issues/15)

## Strategia di estrazione

- **Una tantum**: Leg14–Leg18 (storiche, non cambiano) — estratte e salvate
- **Mensile**: Leg19 (attiva, nuovi atti ogni mese) — estrazione incrementale
- **Pipeline**: solo Leg19 nel loop mensile; le legislature storiche restano fisse

## Architettura

```
scripts/          # extract.py, union_legislatures.py
senato_akn/       # core: extract, git_source, parser, classifier, summarize
data/raw/akn/     # clone git upstream (gitignored) — il "download" è via pack
data/derived/     # parquet + manifest generati (gitignored, GitHub Artifact)
.github/workflows/# test (CI), pipeline (extract→toolkit→GCS→registry)
```

## Licenza

MIT — salvo la fonte originale (Senato della Repubblica, CC BY 3.0).

Progetto del [DataCivicLab](https://github.com/dataciviclab) — corpus-based
autonomo, perché il formato XML Akoma Ntoso richiede un approccio diverso
dalle pipeline tabellari standard.
