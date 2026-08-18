-- clean.sql — senato_dibattito
--
-- Dibattito parlamentare (XIX leg.), dal corpus Akoma Ntoso (resaula Aula +
-- sommcomm Commissione), parser an:debate. Una riga = UN INTERVENTO (speech),
-- con l'oratore.
--
-- Il raw ha un documento per riga con `speakers` (STRUCT array): si
-- unnesta → un intervento per riga. L'ordine dello speech (WITH ORDINALITY)
-- è la chiave di riga (insieme a path + senatore_id).
--
-- Bridge osr:Persona: senatore_id è il numero dell'URI osr:Persona/N
-- (risolto dal parser dal blocco references) — la STESSA chiave di
-- senato_anagrafica e senato_interventi (open-politica). DI GIROLAMO =
-- osr:Persona/32619 = senatore 32619. Il nome completo (showAs) arriva
-- dalle references anche in sommcomm dove an:from è vuoto.
--
-- Drop di colonne raw (tecniche/FRBR non necessarie a livello intervento):
-- atto_dir, file_name, raw_url, work_uri, expression_uri, manifestation_uri,
-- work_date (→ data_seduta), expression_date, manifestation_date, doc_title,
-- short_title, articles_count, paragraphs_count, text_preview, doc_type,
-- speakers (unnestato), legislatura (perimetro XIX), famiglie per doc.
--
-- Esclusi gli speech segnaposto dell'upstream (by="#p" as="", senza oratore):
-- 5.883 in resaula, interventi non attribuibili → fuori dal perimetro.

SELECT
    normalize_string(tipologia)               AS tipologia,
    TRY_CAST(work_date AS DATE)               AS data_seduta,
    normalize_string(document_id)             AS document_id,
    normalize_string(path)                    AS path,
    TRY_CAST(s.unnest.senatore_id AS BIGINT)  AS senatore_id,
    normalize_string(s.unnest.persona_id)     AS persona_id,
    normalize_string(s.unnest.nome)           AS nome_oratore,
    s.ordinality                              AS ordine_intervento,
    TRY_CAST(length(s.unnest."text") AS BIGINT) AS text_len,
    s.unnest."text"                           AS text_intervento
FROM raw_input
CROSS JOIN UNNEST(speakers) WITH ORDINALITY AS s
WHERE length(s.unnest."text") > 0
  AND s.unnest.senatore_id IS NOT NULL
  AND s.unnest.senatore_id NOT IN ('', '0')
