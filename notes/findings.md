# Findings

## Finding principale

Nel corpus `Leg19/ddlpres`, poche famiglie di testi concentrano una quota sproporzionata della massa documentale.

### Decreto-like

- quota atti: `6.99%`
- quota testo: `29.96%`

Lettura:

- i decreti e le conversioni non dominano per numero di testi;
- ma pesano moltissimo come volume documentale.

### Bilancio

- quota atti: `0.57%`
- quota testo: `7.58%`

Lettura:

- famiglia quasi invisibile nel conteggio puro;
- ma fortissima come peso testuale.

## Finding secondario

Nel corpus grezzo esiste un piccolo insieme di record con testo vuoto, quasi sempre associati ad atti multi-file.

Per il v0 operativo e' quindi meglio usare:

- `data/derived/leg19_ddlpres_v0_nonzero.csv`

e trattare il dump completo solo come base grezza di riferimento.

## Stato del finding

- interessante
- difendibile internamente
- non ancora pronto per uscire in pubblico senza un framing piu' robusto
