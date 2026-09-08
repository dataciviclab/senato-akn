-- mart_per_legislatura.sql — aggregati per legislatura
--
-- PK: (legislatura)

SELECT
    legislatura,
    COUNT(*) AS n_documenti,
    SUM(text_len) AS testo_totale,
    COUNT(DISTINCT atto_num) AS n_atti
FROM clean_input
WHERE legislatura IS NOT NULL
GROUP BY legislatura
ORDER BY legislatura
