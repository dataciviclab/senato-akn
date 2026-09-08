-- mart_dib_per_atto.sql — dibattito raggruppato per atto
--
-- Usa atto_num dal clean (derivato da path).
-- PK: (atto_num)

SELECT
    atto_num,
    COUNT(*) AS n_interventi,
    COUNT(DISTINCT senatore_id) AS n_oratori,
    SUM(text_len) AS testo_totale
FROM clean_input
WHERE atto_num IS NOT NULL
GROUP BY atto_num
ORDER BY n_interventi DESC
