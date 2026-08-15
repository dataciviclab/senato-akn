-- mart_famiglie.sql — distribuzione per famiglia legislativa
--
-- Ogni documento può stare in più famiglie: si fa explode della colonna
-- ';'-separata (unnest). Il finding chiave del progetto è la concentrazione
-- di testo in poche famiglie (es. decreti: 6.99% atti, ~30% del testo).

SELECT
    famiglia,
    count(*)                                                       AS n_documenti,
    sum(text_len)                                                  AS testo_totale,
    round(100.0 * sum(text_len) / NULLIF((SELECT sum(text_len)
                                          FROM clean_input), 0), 2) AS pct_testo
FROM (
    SELECT text_len, unnest(string_split(famiglia, ';')) AS famiglia
    FROM clean_input
    WHERE famiglia != ''
)
GROUP BY famiglia
ORDER BY testo_totale DESC
