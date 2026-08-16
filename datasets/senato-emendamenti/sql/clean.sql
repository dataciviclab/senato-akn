-- clean.sql — senato_emendamenti
--
-- Emendamenti del Senato (XIX leg.), dal corpus Akoma Ntoso (emend Aula +
-- emendc Commissione). Una riga = un documento emendamento, con la fase
-- dell'atto a cui si riferisce.
--
-- La fase (S.NNN) si deriva dal work_uri FRBR: gli emendamenti hanno URI
-- http://dati.senato.it/19/Emend/S/<N>/<A|C>/<id> → fase = S.<N>. È la
-- chiave di bridge verso senato_ddl.fase (open-politica).
-- Tipologia: emend = Aula, emendc = Commissione.
--
-- Drop voluto di colonne raw (17 rimosse, 1 aggiunta, net -16), documentato:
-- - concetti dei disegni di legge non applicabili agli emendamenti:
--   articles_count, paragraphs_count, doc_title, short_title, famiglia,
--   doc_type, atto_dir
-- - tecniche/URI: raw_url, work_uri, expression_uri, manifestation_uri,
--   file_name, text_preview (prefix di text_integrale)
-- - ridondanti con l'estrazione: legislatura (già nel grafo 19), FRBRname
--   (0 valorizzato sugli emendamenti), FRBRsubtype/FRBRnumber (rinominati)
-- - decisione: expression_date/manifestation_date DROPPATE qui (in
--   senato_corpus erano mantenute come informative) — per gli emendamenti
--   la data utile è work_date (presentazione), le altre sono boilerplate FRBR

SELECT
    'S.' || regexp_extract(work_uri, 'Emend/S/(\d+)', 1)    AS fase,
    normalize_string(FRBRnumber)                            AS emend_id,
    normalize_string(FRBRsubtype)                           AS frbr_subtype,
    normalize_string(active_ref)                            AS active_ref,
    normalize_string(tipologia)                             AS tipologia,
    normalize_string(document_id)                           AS document_id,
    normalize_string(path)                                  AS path,
    TRY_CAST(work_date AS DATE)                             AS work_date,
    TRY_CAST(text_len AS BIGINT)                            AS text_len,
    text_integrale
FROM raw_input
WHERE work_uri LIKE '%/Emend/S/%'
  AND FRBRnumber IS NOT NULL
  AND FRBRnumber != ''
