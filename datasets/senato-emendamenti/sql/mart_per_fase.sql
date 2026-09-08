-- mart_emendamenti_per_atto.sql — intensità emendativa per atto
--
-- Per ogni atto (S.NNN) quanti emendamenti, quanto testo, e come si
-- distribuiscono tra Aula (emend) e Commissione (emendc). È la metrica
-- "quanto è stato contestato/modificato un DDL" — bridge verso senato_ddl.

SELECT
    fase,
    count(*)                                                          AS n_emend,
    sum(text_len)                                                     AS testo_totale,
    round(avg(text_len))                                              AS testo_medio,
    count(*) FILTER (WHERE tipologia = 'emend')                       AS n_aula,
    count(*) FILTER (WHERE tipologia = 'emendc')                      AS n_commissione,
    count(DISTINCT active_ref)                                        AS n_target_distinti
FROM clean_input
GROUP BY fase
