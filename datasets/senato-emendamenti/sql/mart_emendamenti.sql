-- mart_emendamenti.sql — una riga per emendamento, non per documento
--
-- Il clean è a grano (legislatura, fase, document_id): lo stesso emendamento
-- può avere più documenti (l'upstream replica i file, e un emendamento può
-- essere ripresentato). I consumer che collegano emendamento → atto hanno
-- bisogno del grano (legislatura, fase, emend_id) e di una scelta
-- deterministica di quale documento rappresenta l'emendamento.
--
-- Qui la regola è esplicita e vive nel produttore: vince il `document_id`
-- minore (a parità, `path`). È la stessa scelta che legal-graph faceva nel
-- proprio compose (ROW_NUMBER ... ORDER BY document_id): spostarla qui evita
-- che ogni consumer la riscriva, e permette di leggere una volta sola.
--
-- Perché non basta `mart_emendamenti_per_fase`: quella è un aggregato
-- (n_emend, testo_totale) e non ha le chiavi per costruire un edge
-- emendamento → atto. Questa tabella è il grano riga che serve al grafo.

SELECT
    legislatura,
    fase,
    emend_id,
    atto_num,
    n_atti_fase,
    tipologia,
    work_date,
    text_preview,
    document_id,
    text_len
FROM (
    SELECT
        legislatura,
        fase,
        emend_id,
        atto_num,
        n_atti_fase,
        tipologia,
        work_date,
        text_preview,
        document_id,
        text_len,
        ROW_NUMBER() OVER (
            PARTITION BY legislatura, fase, emend_id
            ORDER BY document_id, path
        ) AS _rn
    FROM clean_input
    WHERE emend_id IS NOT NULL
      AND fase IS NOT NULL
      AND legislatura IS NOT NULL
) q
WHERE _rn = 1
