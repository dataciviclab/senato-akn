# senato-akn — Corpus legislativo del Senato in formato Akoma Ntoso

**Quanto pesa davvero la decretazione d'urgenza se la misuriamo per volume e struttura dei testi, e non solo per numero di atti?**

Questo progetto estrae ed esplora il corpus legislativo del Senato della Repubblica pubblicato nel formato standard Akoma Ntoso (XML). L'obiettivo è capire cosa contiene davvero il lavoro legislativo — misurandolo non per numero di atti, ma per **peso documentale**, struttura e contenuto dei testi.

## Stato

| Perimetro | Copertura |
|---|---|
| **Fonte** | [SenatoDellaRepubblica/AkomaNtosoBulkData](https://github.com/SenatoDellaRepubblica/AkomaNtosoBulkData) |
| **Legislatura** | Leg19 (2022-oggi) |
| **Documenti estratti** | `ddlpres` ✅ (1.095), `ddlmess` ✅ (214), `ddlcomm` ✅ (162) |
| **In attesa di parsing** | `emend` (18.563), `emendc` (43.229), `resaula` (501), `sommcomm` (4.353) |
| **Totale Leg19** | 68.117 file XML, ~786 MB |
| **Stato progetto** | Attivo — perimetro in espansione |

## Finding principale

Nel corpus `Leg19/ddlpres`, poche famiglie di testi concentrano una quota sproporzionata della massa documentale:

| Famiglia | % atti | % testo | Rapporto testo/atti |
|---|---|---|---|
| **Decreto-like** (decreti-legge, conversioni) | 6.99% | 29.94% | 4.28× |
| **Bilancio** (previsione, rendiconto) | 0.57% | 7.58% | 13.37× |
| **Delega** | 6.33% | 8.96% | 1.42× |
| **Istituzione** | 14.08% | 7.55% | 0.54× |
| **Ratifica** | 5.01% | 1.09% | 0.22× |

**La decretazione d'urgenza non domina per numero di atti, ma occupa quasi un terzo dell'intero volume testuale del corpus.** I bilanci, quasi invisibili nel conteggio (0.57%), pesano 13× più del loro numero.

In alcuni mesi, i decreti superano il 60% del testo totale pur essendo meno del 15% degli atti.

## Cosa contiene questo repo

```
scripts/
├── extract.py                   # Estrazione parametrizzata (tipologia, legislatura)
├── extract_leg19_ddlpres.py     # Alias backward compat (delega a extract.py)
├── build_summaries.py           # Aggregazioni per famiglie e mese
└── explore_leg19.py             # Analisi esplorativa del corpus

senato_akn/
├── extract.py   # Core: discover_files, fetch_and_parse, run_extract
├── parser.py    # Parsing XML Akoma Ntoso (funzioni pure)
├── classifier.py # Classificazione in famiglie tematiche
└── summarize.py  # Logica di aggregazione

data/derived/    # CSV generati dall'estrazione (non in git, vedi CI)
notes/           # Finding, domande, stato
.github/workflows/
├── test.yml           # Test + smoke su PR/push
├── build.yml          # Daily: estrazione ddlpres
└── build-weekly.yml   # Weekly: full Leg19 corpus
```

## Come eseguire

```bash
# 1. Installa
pip install -e ".[dev]"

# 2. Estrai Leg19/ddlpres (1.095 file, ~2 min)
python3 scripts/extract.py

# 3. Altre tipologie
python3 scripts/extract.py --tipologie ddlmess,ddlcomm

# 4. Tutto Leg19
python3 scripts/extract.py --tipologie all --drop-zero-text

# 5. Altre legislature
python3 scripts/extract.py --legislatura Leg18 --tipologie ddlpres

# 6. Genera summary
python3 scripts/build_summaries.py
```

L'estrazione scarica i file XML via GitHub API e li parserizza in CSV.
Con `--drop-zero-text` si filtrano i record con testo vuoto (atti multi-file).
Con `--limit N` si processano solo i primi N file (utile per test).

## CI / Schedule

| Trigger | Cosa fa | Quando |
|---|---|---|
| **Schedule daily** (02:00 UTC) | Estrae `ddlpres` | Ogni notte |
| **Schedule weekly** (dom 04:00 UTC) | Estrae full Leg19 | Domenica |
| **PR / push** | Test + smoke (2 file) | Su codice |
| **workflow_dispatch** | Estrazione manuale | Quando serve |

I CSV derivati sono disponibili come **GitHub Artifact** (build → download, non in git).

## Prossimi passi

1. **Estendere il parser** per `<an:amendment>` (emendamenti) e `<an:debate>` (resoconti)
2. **Estrarre emendamenti Aula** (18k file) — cuore politico dell'iter legislativo
3. **Incrociare con italia-corpus**: ciò che viene proposto (Senato) vs ciò che diventa legge

## Partecipa

- **Discussion** per domande civiche, interpretazioni, proposte di espansione
- **Issues** per bug tecnici, errori nel parsing, miglioramenti script
- **PR** per contributi direttamente verificabili

## Cos'è questo progetto

senato-akn fa parte del [DataCivicLab](https://github.com/dataciviclab): un osservatorio civico sui dati pubblici italiani.

Questo repository è un **progetto corpus-based autonomo** — non segue il funnel standard `dataset-incubator`/`toolkit` perché il formato XML Akoma Ntoso richiede un approccio diverso dalle pipeline tabellari. Se emergeranno altri corpus XML nel Lab, potrebbe nascere un'estrazione riusabile.

## Licenza

MIT — salvo diversa indicazione nei file della fonte originale (Senato della Repubblica, CC BY 3.0).
