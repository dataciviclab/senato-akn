-- clean.sql — senato_emendamenti
--
-- Emendamenti del Senato (Leg14–Leg19).
-- La fase (S.NNN) si deriva dal work_uri: Emend/S/<N> → S.<N>.
-- atto_num è estratto dal path (AttoNNNNNN) — lo stesso atto_num del corpus.

SELECT
    'S.' || regexp_extract(work_uri, 'Emend/S/(\d+)', 1)    AS fase,
    TRY_CAST(regexp_extract(atto_dir, 'Atto(\d+)', 1) AS BIGINT) AS atto_num,
    normalize_string(FRBRnumber)                            AS emend_id,
    normalize_string(tipologia)                             AS tipologia,
    normalize_string(document_id)                             AS document_id,
    normalize_string(path)                                    AS path,
    normalize_string(legislatura)                             AS legislatura,
    TRY_CAST(work_date AS DATE)                               AS work_date,
    TRY_CAST(text_len AS BIGINT)                              AS text_len,
    -- campi FRBR
    normalize_string(FRBRsubtype)                             AS FRBRsubtype,
    normalize_string(FRBRnumber)                              AS FRBRnumber,
    normalize_string(FRBRname)                                AS FRBRname,
    -- riferimento all'atto
    normalize_string(active_ref)                              AS active_ref,
    normalize_string(active_ref_href)                         AS active_ref_href,
    -- URI canonici
    normalize_string(work_uri)                                AS work_uri,
    normalize_string(doc_title)                               AS doc_title,
    text_integrale
FROM raw_input
WHERE work_uri LIKE '%/Emend/S/%'
  AND FRBRnumber IS NOT NULL
  AND FRBRnumber != ''
  AND regexp_extract(work_uri, 'Emend/S/(\d+)', 1) IS NOT NULL
