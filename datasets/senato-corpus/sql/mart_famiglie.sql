-- mart_famiglie.sql — aggregazione per famiglia legislativa
--
-- Una riga per famiglia. Conta documenti e somma testo.

SELECT
    famiglia,
    COUNT(*) AS n_documenti,
    SUM(text_len) AS testo_totale,
    ROUND(100.0 * SUM(text_len) / (SELECT SUM(text_len) FROM clean_input), 1) AS pct_testo
FROM clean_input
WHERE famiglia IS NOT NULL AND famiglia != ''
GROUP BY famiglia
ORDER BY n_documenti DESC
