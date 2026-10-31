-- mart_emendamenti_per_atto.sql — intensità emendativa per directory Atto
--
-- ATTENZIONE: `atto_num` è la directory `AttoNNNNN` del file, NON l'id
-- dell'atto. L'upstream replica gli stessi emendamenti in più directory, e
-- per alcune fasi la directory non coincide con l'atto. Per le classifiche
-- usare `mart_emendamenti_per_fase` (chiave: fase S.NNN = atto).
-- Questa tabella resta per compatibilità con i consumer esistenti.

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
