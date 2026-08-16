-- mart_per_atto.sql — un foglio per atto (tabella-bridge verso senato_ddl)
--
-- Aggrega i documenti del corpus per Atto: tipologie presenti, famiglie,
-- volume testuale e numero di articoli. atto_num si collega a senato_ddl
-- via ddl_url (http://dati.senato.it/ddl/<atto_num>).

SELECT
    atto_num,
    string_agg(DISTINCT tipologia, ',')              AS tipologie,
    string_agg(DISTINCT split_part(famiglia, ';', 1), ',') AS famiglie,
    count(*)                                         AS n_documenti,
    sum(text_len)                                    AS testo_totale,
    sum(articles_count)                              AS articoli_totali,
    min(work_date)                                   AS data_primo_documento
FROM clean_input
GROUP BY atto_num
