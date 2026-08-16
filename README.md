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
| **Legislatura** | Leg19 (2022-oggi) |
| **Documenti estratti** | ddlpres (1.095) · emend (18.563) · emendc (43.046) · ddlmess (214) · ddlcomm (162) |
| **In attesa di parsing** | resaula (510) · sommcomm (4.512) |
| **Totale Leg19** | 68.114 file XML, ~786 MB |

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

I parquet derivati sono disponibili come GitHub Artifact del workflow `build`
(→ Actions → download). Non sono in git.

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
python3 scripts/build_summaries.py      # aggregazioni per famiglia e mese
```

## Partecipa

- **Hai una domanda sul lavoro del Senato?** Apri una [Discussion](https://github.com/orgs/dataciviclab/discussions/new?category=Domanda)
- **Vuoi contribuire?** Issues per bug, PR per script e parsing

## Prossimi passi

1. Estendere il parser a `<an:debate>` (resoconti: resaula, sommcomm)
2. Incrocio con italia-corpus: proposto (Senato) vs legge (vigente)

## Architettura

```
scripts/          # extract.py, build_summaries.py
senato_akn/       # core: extract, git_source, parser, classifier, summarize
data/raw/akn/     # clone git upstream (gitignored) — il "download" è via pack
data/derived/     # parquet + manifest generati (gitignored, GitHub Artifact)
.github/workflows/# test, build, build-full
```

## Licenza

MIT — salvo la fonte originale (Senato della Repubblica, CC BY 3.0).

Progetto del [DataCivicLab](https://github.com/dataciviclab) — corpus-based
autonomo, perché il formato XML Akoma Ntoso richiede un approccio diverso
dalle pipeline tabellari standard.
