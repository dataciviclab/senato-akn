-- mart_dibattito_per_seduta.sql — quanto si discute per seduta
--
-- Per ogni seduta: interventi, oratori distinti, volume di testo. Utile per
-- vedere l'intensità del dibattito nel tempo (vs intensità emendativa F3).

SELECT
    data_seduta,
    count(*)                                      AS n_interventi,
    count(DISTINCT persona_id)                    AS n_oratori,
    sum(text_len)                                 AS testo_totale,
    count(DISTINCT tipologia)                     AS n_canali
FROM clean_input
GROUP BY data_seduta
