# Micro-analisi interna - Decretazione d'urgenza nel corpus Senato Leg19

Nota interna. Non pubblicare.

Base:

- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`

Criterio usato:

- record classificato come `decreto_like` se nel titolo contiene:
  - `decreto-legge`
  - oppure `conversione in legge`

## Risultato rapido

Nel corpus `Leg19/ddlpres` filtrato:

- testi totali: `1058`
- testi `decreto_like`: `74`
- quota sul corpus: `6.99%`

Quindi la decretazione d'urgenza pesa poco in termini di conteggio puro dei testi presentati, ma non e' marginale.

## Lunghezza dei testi

`decreto_like`:

- lunghezza media: `54229.7`
- mediana: `13365.5`

altri testi:

- lunghezza media: `9535.7`
- mediana: `3829.5`

L'effetto e' netto:

- i testi di decretazione d'urgenza sono molti meno del resto;
- ma sono mediamente molto piu' lunghi;
- tra gli outlier piu' grandi del corpus compaiono spesso conversioni di decreto-legge.

## Esempi di outlier

Tra i piu' lunghi:

- `Atto00058173` - 574687 caratteri
- `Atto00057156` - 349960
- `Atto00057381` - 306539
- `Atto00057888` - 226559
- `Atto00056683` - 220995

## Serie mensile: primo sguardo

La quota mensile di testi `decreto_like` oscilla molto, ma alcuni mesi si alzano:

- `2023-06`: `11.9%`
- `2023-07`: `11.9%`
- `2023-11`: `18.52%`
- `2024-01`: `14.29%`

Il corpus quindi suggerisce che la decretazione d'urgenza non domina il volume dei testi presentati, ma incide in modo sproporzionato sul peso documentale.

## Lettura prudente

Questa e' una proxy semplice, non una misura completa dell'uso dei decreti.

Limiti:

- classificazione basata sul titolo;
- nessun join con iter, Governo, approvazione o conversione finale;
- nessuna distinzione tra testo originario e modificato oltre il corpus `ddlpres`.

## Utilita'

La domanda regge come:

- nota interna;
- eventuale discussione futura se si decide di uscire dal perimetro locale;
- base per un pilot su corpus legislativi e non ancora per un'analisi pubblica forte.
