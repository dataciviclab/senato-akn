-- clean.sql — senato_emendamenti
--
-- Emendamenti del Senato (Leg14–Leg19).
--
-- Identità di un emendamento: (legislatura, fase, document_id).
--   * `fase` = S.NNN dal work_uri `Emend/S/<N>`: è l'atto, ed è la chiave del
--     bridge verso `senato_ddl`.
--   * `atto_num` = directory `AttoNNNNN` dove vive il file: NON è l'id
--     dell'atto. L'upstream replica lo stesso documento sotto più directory
--     (fino a 57 copie identiche): senza dedup i conteggi sono gonfiati
--     (~+24% righe, fino a 57x su singoli atti).
--
-- Il dedup tiene una riga per documento; `n_copie` e `n_atti_dir` espongono la
-- replica invece di nasconderla. `n_atti_fase` è il numero di directory Atto
-- della fase (1 = l'atto è attribuibile senza ambiguità).

WITH raw AS (
    SELECT
        'S.' || regexp_extract(work_uri, 'Emend/S/(\d+)', 1)    AS fase,
        TRY_CAST(regexp_extract(atto_dir, 'Atto(\d+)', 1) AS BIGINT) AS atto_num,
        normalize_string(FRBRnumber)                            AS emend_id,
        normalize_string(tipologia)                             AS tipologia,
        normalize_string(document_id)                           AS document_id,
        normalize_string(path)                                  AS path,
        normalize_string(legislatura)                           AS legislatura,
        TRY_CAST(work_date AS DATE)                             AS work_date,
        TRY_CAST(text_len AS BIGINT)                            AS text_len,
        -- campi FRBR
        normalize_string(FRBRsubtype)                           AS FRBRsubtype,
        normalize_string(FRBRnumber)                            AS FRBRnumber,
        normalize_string(FRBRname)                              AS FRBRname,
        -- riferimento all'atto
        normalize_string(active_ref)                            AS active_ref,
        normalize_string(active_ref_href)                       AS active_ref_href,
        -- URI canonici
        normalize_string(work_uri)                              AS work_uri,
        normalize_string(doc_title)                             AS doc_title,
        text_integrale
    FROM raw_input
    WHERE work_uri LIKE '%/Emend/S/%'
      AND FRBRnumber IS NOT NULL
      AND FRBRnumber != ''
      AND regexp_extract(work_uri, 'Emend/S/(\d+)', 1) IS NOT NULL
      AND regexp_extract(work_uri, 'Emend/S/(\d+)', 1) != ''
),

dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY legislatura, fase, document_id
            ORDER BY atto_num, path
        ) AS rn
    FROM raw
),

copie AS (
    SELECT
        legislatura,
        fase,
        document_id,
        COUNT(*)                                AS n_copie,
        COUNT(DISTINCT atto_num)                AS n_atti_dir
    FROM raw
    GROUP BY 1, 2, 3
),

-- Numero di directory Atto in cui l'upstream archivia la fase: serve ai
-- consumer per decidere il fallback su `atto_num` (1 = non ambiguo).
fasi AS (
    SELECT
        legislatura,
        fase,
        COUNT(DISTINCT atto_num)                AS n_atti_fase
    FROM raw
    GROUP BY 1, 2
)

SELECT
    d.fase,
    d.atto_num,
    d.emend_id,
    d.tipologia,
    d.document_id,
    d.path,
    d.legislatura,
    d.work_date,
    d.text_len,
    d.FRBRsubtype,
    d.FRBRnumber,
    d.FRBRname,
    d.active_ref,
    d.active_ref_href,
    d.work_uri,
    d.doc_title,
    d.text_integrale,
    c.n_copie,
    c.n_atti_dir,
    f.n_atti_fase
FROM dedup d
JOIN copie c USING (legislatura, fase, document_id)
JOIN fasi f USING (legislatura, fase)
WHERE d.rn = 1
