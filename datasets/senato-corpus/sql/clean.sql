-- clean.sql — senato_corpus
--
-- Corpus Akoma Ntoso del Senato (Leg19), un documento per riga.
-- Input: parquet derivato da senato_akn/extract (data/derived/leg19_ddlpres_v0.parquet).
--
-- Note:
-- - atto_dir è la directory AttoNNNNN nel repo AkomaNtosoBulkData: il numero
--   coincide con l'URI http://dati.senato.it/ddl/N (ddl_url in senato_ddl) —
--   è la chiave di bridge verso open-politica.
-- - famiglia è ';'-separata (un documento può stare in più famiglie).
--
-- Drop voluto di colonne raw (10), documentato:
-- - tecniche/morte: path, file_name, raw_url, work_uri, expression_uri,
--   manifestation_uri (URI e boilerplate dell'estrazione, non analizzabili)
-- - duplicati: text_preview (prefix di text_integrale), FRBRname
--   (0/1978 valorizzata su ddlpres)
-- - mantenute qui (informative, 100% valorizzate): expression_date e
--   manifestation_date (date FRBR del documento, oltre a work_date)

SELECT
    TRY_CAST(regexp_extract(atto_dir, 'Atto(\d+)', 1) AS BIGINT) AS atto_num,
    normalize_string(legislatura)                                 AS legislatura,
    normalize_string(tipologia)                                   AS tipologia,
    normalize_string(doc_type)                                    AS doc_type,
    normalize_string(document_id)                                 AS document_id,
    normalize_string(doc_title)                                   AS doc_title,
    normalize_string(short_title)                                 AS short_title,
    normalize_string(famiglia)                                    AS famiglia,
    TRY_CAST(work_date AS DATE)                                   AS work_date,
    TRY_CAST(expression_date AS DATE)                             AS expression_date,
    TRY_CAST(manifestation_date AS DATE)                          AS manifestation_date,
    TRY_CAST(articles_count AS BIGINT)                            AS articles_count,
    TRY_CAST(paragraphs_count AS BIGINT)                          AS paragraphs_count,
    TRY_CAST(text_len AS BIGINT)                                  AS text_len,
    normalize_string(FRBRsubtype)                                 AS frbr_subtype,
    normalize_string(FRBRnumber)                                  AS frbr_number,
    normalize_string(active_ref)                                  AS active_ref,
    text_integrale
FROM raw_input
WHERE atto_dir LIKE 'Atto%'
