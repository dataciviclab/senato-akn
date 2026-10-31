-- mart_per_atto.sql — un foglio per atto (tabella-bridge verso senato_ddl)
--
-- Aggrega i documenti del corpus per Atto: tipologie presenti, volume
-- testuale e numero di articoli.
--
-- Chiavi verso `senato_ddl`:
--   * `atto_num` ↔ `ddl_url` (http://dati.senato.it/ddl/<atto_num>)
--   * `fase` (S.NNN) ↔ `senato_ddl.fase`
--
-- `fase` è quella del documento `ddlpres` quando c'è (l'atto stesso); per gli
-- atti senza ddlpres si usa la fase dei documenti presenti. Serve alla
-- dashboard per collegare l'atto ai suoi emendamenti (keyed by fase).

SELECT
    atto_num,
    coalesce(
        max(fase) FILTER (WHERE tipologia = 'ddlpres'),
        max(fase)
    )                                                AS fase,
    any_value(legislatura)                           AS legislatura,
    string_agg(DISTINCT tipologia, ',')              AS tipologie,
    count(*)                                         AS n_documenti,
    sum(text_len)                                    AS testo_totale,
    sum(articles_count)                              AS articoli_totali,
    min(work_date)                                   AS data_primo_documento
FROM clean_input
GROUP BY atto_num
