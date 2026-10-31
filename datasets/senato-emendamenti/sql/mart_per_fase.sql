-- mart_per_fase.sql — intensità emendativa per atto (fase S.NNN)
--
-- `fase` è la chiave canonica: è l'atto a cui l'emendamento si riferisce
-- (bridge verso `senato_ddl.fase`). Una riga per (legislatura, fase): il solo
-- `fase` non basta, lo stesso S.NNN si ripete in legislature diverse.
--
-- Usare QUESTA tabella per le classifiche "atti più emendati".
-- `mart_per_atto` resta per compatibilità, ma raggruppa per directory `Atto`
-- e non per atto: l'upstream replica gli stessi emendamenti in più directory.

SELECT
    legislatura,
    fase,
    count(*)                                                    AS n_emend,
    sum(text_len)                                               AS testo_totale,
    round(avg(text_len))                                        AS testo_medio,
    count(*) FILTER (WHERE tipologia = 'emend')                 AS n_aula,
    count(*) FILTER (WHERE tipologia = 'emendc')                AS n_commissione,
    count(DISTINCT active_ref)                                  AS n_target_distinti,
    min(work_date)                                              AS primo_emendamento,
    max(work_date)                                              AS ultimo_emendamento,
    max(n_atti_dir)                                             AS n_atti_dir
FROM clean_input
WHERE fase IS NOT NULL
GROUP BY legislatura, fase
