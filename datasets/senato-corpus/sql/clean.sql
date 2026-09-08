-- clean.sql — senato_corpus
--
-- Corpus legislativo del Senato (Leg14–Leg19).
-- Mantiene tutte le colonne utili dall'unified parquet.
-- Solo conversioni di tipo e normalizzazione, nessun drop.

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
    normalize_string(FRBRsubtype)                                 AS FRBRsubtype,
    normalize_string(FRBRnumber)                                  AS FRBRnumber,
    normalize_string(FRBRname)                                    AS FRBRname,
    normalize_string(work_uri)                                    AS work_uri,
    normalize_string(expression_uri)                              AS expression_uri,
    normalize_string(manifestation_uri)                           AS manifestation_uri,
    normalize_string(atto_dir)                                    AS atto_dir,
    normalize_string(doc_number) AS doc_number_raw,
    normalize_string(path)                                        AS path,
    proponenti,
    sezioni,
    speakers,
    text_integrale
FROM raw_input
WHERE atto_dir LIKE 'Atto%'
  AND TRY_CAST(work_date AS DATE) IS NOT NULL
  AND TRY_CAST(work_date AS DATE) <= CURRENT_DATE
  AND TRY_CAST(work_date AS DATE) >= '1990-01-01'
