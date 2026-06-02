# senato-akn — Corpus legislativo del Senato in formato Akoma Ntoso

**Quanto pesa davvero la decretazione d'urgenza se la misuriamo per volume e struttura dei testi, e non solo per numero di atti?**

Questo progetto estrae ed esplora il corpus legislativo del Senato della Repubblica pubblicato nel formato standard Akoma Ntoso (XML). L'obiettivo è capire cosa contiene davvero il lavoro legislativo — misurandolo non per numero di atti, ma per **peso documentale**, struttura e contenuto dei testi.

## Stato

| Perimetro | Copertura |
|---|---|
| **Fonte** | [SenatoDellaRepubblica/AkomaNtosoBulkData](https://github.com/SenatoDellaRepubblica/AkomaNtosoBulkData) |
| **Legislatura** | Leg19 (2022-oggi) |
| **Tipologia** | `ddlpres` — disegni di legge presentati |
| **Unità di analisi** | Documento (testo legislativo con metadati strutturali) |
| **Stato progetto** | Pubblico — esplorativo. Perimetro stretto, espansione futura da valutare |

## Finding principale

Nel corpus `Leg19/ddlpres`, poche famiglie di testi concentrano una quota sproporzionata della massa documentale:

| Famiglia | % atti | % testo | Rapporto testo/atti |
|---|---|---|---|
| **Decreto-like** (decreti-legge, conversioni) | 6.99% | 29.96% | 4.28× |
| **Bilancio** (previsione, rendiconto) | 0.57% | 7.58% | 13.37× |
| **Delega** | 6.33% | 8.96% | 1.42× |
| **Istituzione** | 14.08% | 7.55% | 0.54× |
| **Ratifica** | 5.01% | 1.09% | 0.22× |

**La decretazione d'urgenza non domina per numero di atti, ma occupa quasi un terzo dell'intero volume testuale del corpus.** I bilanci, quasi invisibili nel conteggio (0.57%), pesano 13× più del loro numero.

In alcuni mesi, i decreti superano il 60% del testo totale pur essendo meno del 15% degli atti.

## Cosa contiene questo repo

- `scripts/extract_leg19_ddlpres.py` — estrazione del corpus da GitHub API + parsing XML Akoma Ntoso
- `scripts/build_summaries.py` — aggregazioni per famiglie e per mese
- `data/derived/` — CSV derivati (v0 del corpus e summary)
- `notes/` — finding, domande, stato del progetto
- `Makefile` — target `extract` e `summarize`

## Come eseguire

```bash
# 1. Clona
git clone https://github.com/dataciviclab/senato-akn
cd senato-akn

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Estrai il corpus (Leg19/ddlpres)
make extract

# 4. Genera summary
make summarize
```

L'estrazione scarica i file XML via GitHub API e li parserizza in una tabella CSV (~1058 documenti). Con `--drop-zero-text` si filtrano i record con testo vuoto (atti multi-file).

## Limiti attuali

- Copre solo **Leg19** e solo **ddlpres** — non emendamenti, resoconti, atti commissione
- I dati si basano sul [bulk GitHub del Senato](https://github.com/SenatoDellaRepubblica/AkomaNtosoBulkData), aggiornato dalla fonte
- Non include votazioni, iter parlamentare o comportamento individuale dei senatori
- Il parsing XML è limitato ai metadati FRBR + body text + conteggio articoli

## Domande da esplorare

1. **Quanto pesa la decretazione d'urgenza per volume testuale, non per numero di atti?** — finding già verificato
2. **Quali famiglie legislative occupano davvero il corpus del Senato?** — analisi per peso documentale
3. **Quanto incidono bilanci e decreti sul volume complessivo?** — confronto già disponibile nei summary

Domande che richiedono parsing aggiuntivo (emendamenti, legislature precedenti) sono rimandate.

## Partecipa

- **Discussion** per domande civiche, interpretazioni, proposte di espansione
- **Issues** per bug tecnici, errori nel parsing, miglioramenti script
- **PR** per contributi direttamente verificabili

## Cos'è questo progetto

senato-akn fa parte del [DataCivicLab](https://github.com/dataciviclab): un osservatorio civico sui dati pubblici italiani.

Questo repository è un **progetto corpus-based autonomo** — non segue il funnel standard `dataset-incubator`/`toolkit` perché il formato XML Akoma Ntoso richiede un approccio diverso dalle pipeline tabellari. Se emergeranno altri corpus XML nel Lab, potrebbe nascere un'estrazione riusabile.


## Licenza

MIT — salvo diversa indicazione nei file della fonte originale (Senato della Repubblica, CC BY 3.0).
