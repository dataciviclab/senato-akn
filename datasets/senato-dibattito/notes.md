# senato-dibattito — il chi parla e cosa dice

## Cosa è
Il terzo dataset del triangolo senato-akn. I resoconti del dibattito
parlamentare: **Aula** (resaula) e **Commissione** (sommcomm). Una riga =
**un intervento** (speech) con oratore e testo.

## Parser `an:debate`
La struttura è diversa dagli atti: `an:body/an:p` non esiste (prima: `text_len=0`).
Il parser ora estrae:
- `debateBody → debateSection → speech (by=#pNNNN) → from` (oratore)
- testo dagli `<an:p>` dentro lo speech
- **nome risolto dal blocco `references`** (`an:TLCPerson showAs`) — indispensabile
  per sommcomm, dove `an:from` è vuoto e il nome sta solo nelle references
  (es. `<an:TLCPerson id="p4192" showAs="Claudio Fazzone">`)

## Bridge `osr:Persona`
`senatore_id` = numero dell'URI `osr:Persona/N` (risolto da `href` delle
references). È la **stessa chiave** di `senato_anagrafica` e `senato_interventi`
(open-politica) → il dibattito si aggancia a persone, anagrafica, interventi.

Verificato su open-politica: 251 oratori distinti, 204 match con anagrafica
(81%). I non-match sono ministri non senatori e ruoli istituzionali
(Nordio, Valditara, Giorgetti, PRESIDENTE…).

## Numeri (Leg19)
- 195.387 interventi attribuibili (resaula 78.710 + sommcomm 116.677)
- 8.334 resoconti (990 Aula + 7.344 Commissione)
- 5.883 speech segnaposto dell'upstream (by="#p" as="") esclusi nel clean
  — non attribuibili, niente oratore

## Note / limiti
- 132 interventi sommcomm (0.07%) senza nome: reference senza showAs o role
- il nome arriva da due fonti (showAs full-name vs from in maiuscolo) →
  possibile normalizzazione futura (es. solo showAs)
