-- mart_famiglie.sql — aggregazione per famiglia legislativa
--
-- `famiglia` nel clean è multi-valore (`;`-separata, es. `delega;norme_generali`).
-- Qui viene ESPLOSA: una riga per famiglia, così il finding per famiglia è
-- ricavabile dai mart pubblicati (prima le etichette composte finivano in
-- righe separate e i conteggi non tornavano).
--
-- ATTENZIONE: le percentuali NON sono esclusive — un documento può appartenere
-- a più famiglie, quindi la somma di `pct_documenti` / `pct_testo` può
-- superare il 100%.

WITH esploso AS (
    SELECT
        trim(f) AS famiglia,
        text_len
    FROM clean_input,
         UNNEST(string_split(famiglia, ';')) AS t(f)
    WHERE famiglia IS NOT NULL AND famiglia <> ''
)

SELECT
    famiglia,
    COUNT(*)                                     AS n_documenti,
    SUM(text_len)                                AS testo_totale,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM clean_input), 1)      AS pct_documenti,
    ROUND(100.0 * SUM(text_len) / (SELECT SUM(text_len) FROM clean_input), 1) AS pct_testo
FROM esploso
GROUP BY famiglia
ORDER BY testo_totale DESC
