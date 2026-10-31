# Findings

## Finding principale

Nel corpus `Leg19/ddlpres` poche famiglie di testi concentrano una quota
sproporzionata della massa documentale.

| Famiglia | % documenti | % testo | Rapporto |
|---|---|---|---|
| **Bilancio** | <1% | ≈8% | **≈11×** |
| **Decreto-like** | ≈9% | ≈1/3 | **≈3,7×** |
| Delega | ≈7% | ≈9% | ≈1,3× |
| Istituzione | ≈14% | ≈7% | ≈0,5× |
| Ratifica | ≈5% | ≈1% | ≈0,2× |

Lettura:

- i decreti e le conversioni non dominano per numero di testi, ma pesano
  molto come volume documentale;
- i bilanci sono quasi invisibili nel conteggio puro e fortissimi come peso
  testuale;
- in alcuni mesi i decreti superano il 60% del testo (aprile 2024 ≈67%,
  giugno 2023 ≈63%).

## Metodo e limiti

- Misura: `count(*)` e `sum(text_len)` per famiglia, sul sottoinsieme
  `Leg19`/`ddlpres`.
- `famiglia` è multi-valore (`;`-separata) ed è **esplosa**: un documento può
  stare in più famiglie, quindi le percentuali non sono esclusive (la somma
  può superare il 100%).
- Le cifre qui sono **arrotondate**: il corpus si aggiorna ogni mese.
  Il valore esatto dello snapshot corrente si rigenera con

```bash
make findings ARGS="--parquet https://storage.googleapis.com/dataciviclab-clean/senato-akn/senato_corpus/2026/senato_corpus_2026_clean.parquet"
```

- Fonte canonica pubblicata: `senato_corpus` (clean) e `senato_corpus__mart_famiglie`
  (mart, una riga per famiglia).
- Il finding vale per i **disegni di legge presentati**: non dice nulla su
  esiti, tempi o probabilità di approvazione (servono join con l'iter).

## Stato del finding

- difendibile: i numeri sono ricavabili da un mart pubblicato
- il testo del README resta volutamente qualitativo e non datato
