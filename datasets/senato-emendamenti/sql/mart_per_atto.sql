-- mart_emendamenti_per_atto.sql — intensità emendativa per atto
--
-- Una riga per atto_num. Conta emendamenti e testo totale.

SELECT
    atto_num,
    COUNT(*) AS n_emend,
    SUM(text_len) AS testo_totale,
    ROUND(AVG(text_len)) AS testo_medio,
    COUNT(*) FILTER (WHERE tipologia = 'emend') AS n_aula,
    COUNT(*) FILTER (WHERE tipologia = 'emendc') AS n_commissione
FROM clean_input
WHERE atto_num IS NOT NULL
GROUP BY atto_num
