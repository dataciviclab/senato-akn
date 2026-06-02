# Micro-analisi interna - Famiglie di testi nel corpus Senato Leg19

Nota interna. Non pubblicare.

Base:

- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`

## Punto chiave

Nel corpus dei testi `ddlpres` della XIX legislatura, il numero di atti e la massa documentale non coincidono.

Alcune famiglie sono poco numerose ma concentrano una quota molto alta del testo totale.

## Famiglie principali

### Decreto-like

Definizione semplice:

- titolo contenente `decreto-legge` oppure `conversione in legge`

Risultato:

- `74` testi
- `6.99%` del corpus per numero di righe
- `29.96%` della massa testuale totale
- lunghezza media: `54229.7`
- mediana: `13365.5`

Lettura:

- pochi per numero
- enormi per peso documentale

### Bilancio

Definizione semplice:

- titolo contenente `bilancio di previsione` oppure `rendiconto`

Risultato:

- `6` testi
- `0.57%` del corpus
- `7.58%` della massa testuale totale
- lunghezza media: `169278.3`

Lettura:

- quasi invisibili nel conteggio puro
- ma giganteschi come volume di testo

### Delega

Risultato:

- `67` testi
- `6.33%` del corpus
- `8.96%` della massa testuale totale

Lettura:

- famiglia abbastanza frequente
- con peso testuale superiore alla sua quota numerica

### Istituzione

Risultato:

- `149` testi
- `14.08%` del corpus
- `7.55%` della massa testuale totale

Lettura:

- molto presenti nei titoli
- ma mediamente piu' leggeri dei decreti e dei bilanci

### Ratifica

Risultato:

- `53` testi
- `5.01%` del corpus
- `1.09%` della massa testuale totale

Lettura:

- famiglia riconoscibile
- ma mediamente breve

## Outlier forti

Gli atti piu' lunghi del corpus includono soprattutto:

- bilanci
- conversioni di decreto-legge
- grandi testi omnibus o di riforma

Esempi:

- `Atto00056372` bilancio 2023: `672654`
- `Atto00058173` conversione DL 2 marzo 2024 n. 19: `574687`
- `Atto00057654` bilancio 2024: `337326`
- `Atto00057156` conversione DL 22 aprile 2023 n. 44: `349960`

## Articolazione

Tra gli atti con piu' articoli compaiono ancora:

- bilanci
- decreti di conversione
- testi omnibus o riforme estese

Quindi non e' solo un effetto di lunghezza lineare del testo: alcune famiglie concentrano anche complessita' strutturale.

## Lettura utile per il Lab

La prima intuizione che regge davvero e':

`nel corpus dei testi presentati al Senato, la decretazione d'urgenza e i bilanci pesano molto piu' come massa documentale che come semplice numero di atti`

Questa e' una lettura piu' interessante del solo conteggio dei decreti.

## Passo successivo sensato

Se si continua il pilot interno:

1. confrontare in modo piu' netto:
   - quota atti
   - quota testo
   - quota articoli
2. decidere se il primo finding interno debba essere:
   - decretazione d'urgenza
   - oppure concentrazione del peso documentale in poche famiglie di testi
