# Domande possibili - Senato Akoma Ntoso Leg19 ddlpres

Nota interna. Non pubblicare.

Base usata:

- `C:\\Users\\gabry\\dev\\dataciviclab-workspace\\_local\\data\\senato_akoma_ntoso_leg19_ddlpres_v0_nonzero.csv`

## Osservazioni minime dal corpus

- righe: `1058`
- anni coperti nel v0: `2022-2024`
- picco iniziale forte: `2022-10` ha `249` testi
- i testi piu' lunghi sono soprattutto:
  - bilanci
  - conversioni di decreto-legge
  - alcuni atti omnibus o di riforma ampia

Keyword abbastanza leggibili nei titoli:

- `istituzione`: `149`
- `decreto-legge`: `73`
- `delega`: `67`
- `conversione in legge`: `58`
- `ratifica`: `53`

## Domande che reggono

### 1. Quanto pesa la decretazione d'urgenza nel corpus dei testi presentati?

Perche' regge:

- i titoli permettono di riconoscere bene `decreto-legge` e `conversione in legge`;
- la misura e' semplice;
- non richiede ancora iter, gruppi politici o votazioni.

V0 plausibile:

- quota di testi che nascono come decreto-legge / conversione;
- lunghezza media di questi testi rispetto agli altri.

### 2. Quanto sono lunghi i testi legislativi presentati e quali famiglie concentrano gli outlier?

Perche' regge:

- `text_len` e' gia' disponibile;
- gli outlier si vedono subito;
- puo' produrre una prima lettura robusta senza NLP pesante.

V0 plausibile:

- distribuzione delle lunghezze;
- top atti piu' lunghi;
- confronto tra bilanci, decreti e altri testi.

### 3. Come si concentra il deposito dei testi all'inizio della legislatura?

Perche' regge:

- `work_date` e' pulita;
- si vede gia' un picco in `2022-10`;
- e' una domanda descrittiva ma non banale sul ritmo del corpus.

V0 plausibile:

- serie mensile dei testi presentati;
- confronto tra mesi di avvio legislatura e mesi successivi.

### 4. Quali categorie lessicali o istituzionali ricorrono di piu' nei titoli?

Perche' regge:

- titoli presenti e leggibili;
- si puo' fare con keyword semplici;
- resta una lettura esplorativa, non ancora semantica forte.

V0 plausibile:

- frequenze di parole o pattern tipo `istituzione`, `ratifica`, `delega`, `riordino`.

## Domande che non reggono ancora

- chi presenta cosa per gruppo politico;
- probabilita' di approvazione;
- tempi dell'iter;
- comportamento parlamentare;
- relazioni robuste tra testo, emendamenti e votazioni.

Per queste manca ancora modellazione aggiuntiva o join con altre superfici.

## Raccomandazione

La domanda piu' difendibile per un prossimo passo interno e':

`Quanto pesa la decretazione d'urgenza nel corpus dei testi presentati al Senato nella XIX legislatura?`

Seconda migliore:

`Quanto sono lunghi i testi legislativi presentati e quali famiglie concentrano gli atti piu' estesi?`
