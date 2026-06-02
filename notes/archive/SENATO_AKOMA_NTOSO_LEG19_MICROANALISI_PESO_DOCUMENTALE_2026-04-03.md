# Micro-analisi interna - Peso documentale per famiglie di testi

Nota interna. Non pubblicare.

Base:

- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`

## Tesi che emerge

Nel corpus `ddlpres` del Senato XIX legislatura, il numero di testi non descrive bene il peso reale delle famiglie legislative.

La misura piu' interessante non e' solo `quanti atti`, ma:

- quota di atti
- quota di testo totale
- quota di articoli

## Confronto famiglie principali

### Decreto-like

- quota atti: `6.99%`
- quota testo: `29.96%`
- quota articoli: `8.28%`
- rapporto `quota testo / quota atti`: `4.28`

Lettura:

- la decretazione d'urgenza e' molto meno dominante nel conteggio che nel peso documentale;
- occupa quasi un terzo della massa testuale del corpus.

### Bilancio

- quota atti: `0.57%`
- quota testo: `7.58%`
- quota articoli: `2.22%`
- rapporto `quota testo / quota atti`: `13.37`

Lettura:

- caso estremo;
- quasi invisibile come numero di atti, ma enorme come testo.

### Delega

- quota atti: `6.33%`
- quota testo: `8.96%`
- quota articoli: `8.23%`

Lettura:

- famiglia pesante ma meno squilibrata di decreti e bilanci.

### Istituzione

- quota atti: `14.08%`
- quota testo: `7.55%`
- quota articoli: `12.49%`

Lettura:

- molto presente nei titoli;
- ma mediamente piu' leggera come volume testuale.

### Ratifica

- quota atti: `5.01%`
- quota testo: `1.09%`
- quota articoli: `4.13%`

Lettura:

- famiglia riconoscibile ma documentariamente leggera.

## Profilo temporale dei decreti

In diversi mesi, la decretazione d'urgenza resta minoritaria per numero ma domina il testo totale del mese.

Esempi:

- `2023-02`: `8.11%` degli atti, `55.39%` del testo
- `2023-05`: `8.33%` degli atti, `50.43%` del testo
- `2023-06`: `11.90%` degli atti, `67.26%` del testo
- `2023-07`: `11.90%` degli atti, `58.60%` del testo
- `2024-01`: `14.29%` degli atti, `62.32%` del testo
- `2024-04`: `10.00%` degli atti, `86.27%` del testo

## Finding interno piu' forte

Il finding migliore, ad oggi, non e' semplicemente:

`ci sono molti decreti`

ma piuttosto:

`nel corpus dei testi presentati, poche famiglie — soprattutto decreti e bilanci — concentrano una quota sproporzionata della massa documentale`

## Implicazione

Se mai questo filone esce dal perimetro interno, la domanda pubblica piu' forte potrebbe essere:

`quanto pesa davvero la decretazione d'urgenza se la misuriamo per volume e struttura dei testi, e non solo per numero di atti?`

oppure, ancora meglio:

`quali famiglie legislative occupano davvero il corpus del Senato quando si guarda al peso documentale invece che al semplice conteggio?`
