-- mart_interventi_per_persona.sql — chi parla e quanto
--
-- Per ogni oratore (senatore_id, bridge → senato_anagrafica/senato_interventi
-- in open-politica): numero di interventi, testo totale, e come si distribuisce
-- tra Aula (resaula) e Commissione (sommcomm). La domanda: "chi occupa lo
-- spazio del dibattito?".

SELECT
    senatore_id,
    arg_max(nome_oratore, text_len)                           AS nome_oratore,
    count(*)                                                  AS n_interventi,
    sum(text_len)                                             AS testo_totale,
    count(DISTINCT data_seduta)                               AS n_sedute,
    count(*) FILTER (WHERE tipologia = 'resaula')             AS n_aula,
    count(*) FILTER (WHERE tipologia = 'sommcomm')            AS n_commissione
FROM clean_input
GROUP BY senatore_id
