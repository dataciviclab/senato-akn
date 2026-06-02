# Esplorazione interna - Senato Akoma Ntoso Leg19 ddlpres

Nota interna. Non pubblicare.

Data: 2026-04-03
Origine: `TASK_senato_akoma_ntoso_exploration.md`
Fonte: `AkomaNtosoBulkData` del Senato della Repubblica

## Scopo

Capire se il bulk Akoma Ntoso del Senato regge come progetto DataCivicLab e quale v0 abbia senso, prima di qualunque passo pubblico.

## Perimetro verificato

- sola legislatura `Leg19`
- sola tipologia `ddlpres`
- campione reale di file `.akn.xml`

## Risultati tecnici

Conteggi su `Leg19`:

- cartelle atto: `1059`
- atti con `ddlpres`: `1058`
- file XML `ddlpres`: `1094`
- massimo file `ddlpres` nello stesso atto: `9`

Quindi:

- quasi tutti gli atti hanno almeno un testo presentato;
- alcuni atti hanno piu' file `ddlpres`, quindi il record naturale non e' "un atto", ma almeno "un documento/testo".

## Shape minima confermata

Campi leggibili senza troppo sforzo:

- `atto_dir`
- `file_name`
- `FRBRuri` / URI logico del DdL
- `date_work`
- `date_expression`
- testo integrale del corpo
- lunghezza del testo

Campi non ancora affidabili nel campione:

- `doc_title`
- `short_title`
- alias leggibili e consistenti

Nel campione provato, il testo del corpo si estrae bene, mentre i titoli non sono sempre presenti in campi semplici.

## Artefatti locali creati

Creati:

- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_sample.csv`
- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0.csv`
- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`
- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\scripts\\senato_akoma_leg19_extract.py`

Il parser locale minimo produce un record per file `ddlpres` con:

- identificativi FRBR
- date principali
- titolo breve e titolo documento
- contatori base (`articles_count`, `paragraphs_count`)
- preview
- testo integrale

## Primo v0 locale

Il run completo su `Leg19/ddlpres` ha prodotto:

- `1094` righe
- `1058` atti distinti
- `1094` record con almeno un campo titolo valorizzato (`doc_title` o `short_title`)
- lunghezza media testo: `12245.1`
- mediana lunghezza testo: `3824.5`
- lunghezza massima osservata: `672654`
- righe con `text_len = 0`: `36`
- atti con piu' di un file `ddlpres`: `27`
- atti multi-file che includono almeno una riga a testo zero: `26`

Quindi:

- il v0 document-level regge davvero;
- il corpus ha gia' forma abbastanza leggibile per analisi esplorative;
- esistono outlier molto grandi, quindi il trattamento del testo va fatto con un minimo di cautela.
- c'e' un pattern concreto di duplicazione/placeholder: nei multi-file compaiono spesso seconde righe con stesso titolo e testo vuoto.

## Regola pratica che emerge

Per un v0 serio, la shape pubblica piu' sensata non e' "tutti i file cosi' come sono", ma:

- tenere il record a livello documento;
- escludere o trattare separatamente i record con `text_len = 0`;
- analizzare con cautela gli atti multi-file, per capire se le righe extra sono:
  - placeholder;
  - versioni alternative;
  - manifestazioni tecniche dello stesso testo.

## Corpus v0 consigliato

Creato anche il corpus filtrato:

- `senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`

Numeri:

- `1058` righe
- `1057` atti distinti
- `0` righe con testo vuoto

Questa e' oggi la base locale migliore per eventuali analisi esplorative o quality-check successivi.

## Lettura metodologica

Questo non si comporta come un candidate DI normale:

- non e' tabellare di partenza;
- richiede parsing XML e scelte semantiche;
- il record v0 piu' difendibile e' il documento, non l'atto aggregato;
- ha piu' la forma di corpus documentale che di dataset amministrativo classico.

## Raccomandazione

Verdetto interno: **pilot tecnico separato**

Non aprire per ora:

- candidate DI standard
- discussion pubblica

Prima conviene fare un mini parser locale che produca una tabella v0 con:

- `legislatura`
- `atto_dir`
- `file_name`
- `work_uri`
- `date_work`
- `date_expression`
- `text_len`
- `text_integrale`

Solo dopo si puo' decidere se il filone regge davvero per il pubblico.

## Prossimo passo consigliato

1. ispezione di quality-control sui record piu' lunghi e sui casi con piu' file per atto
2. scelta del vero v0 pubblico:
   - indice documenti
   - corpus testi
   - metadati + testo
3. verifica su:
   - stabilita' dei campi
   - costo del parsing
   - prime domande civiche plausibili

## File consultati

- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\scouting\\notes\\source-checks-approved\\senato_akoma_ntoso_bulk_data_source_check_2026-04-03.md`
- `https://github.com/SenatoDellaRepubblica/AkomaNtosoBulkData`
- `https://raw.githubusercontent.com/SenatoDellaRepubblica/AkomaNtosoBulkData/master/Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml`
- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_sample.csv`
- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0.csv`
- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`
