# Contribuire a senato-akn

Questo repo estrae il corpus legislativo del Senato (Akoma Ntoso, XML) e lo
pubblica come dataset raw → clean → mart su GCS.

## Struttura

```
senato_akn/            # core: extract, git_source, parser, classifier
scripts/               # extract.py, union_legislatures.py, findings.py
datasets/<slug>/       # dataset.yml + sql/ (clean.sql, mart*.sql)
dashboard/             # Streamlit: app.py, sources.py, pages/
data/raw/akn/          # clone git upstream (gitignored)
data/derived/          # parquet + manifest (gitignored, effimeri)
```

## Setup

Un solo ambiente per repo (il workspace usa una venv condivisa):

```bash
pip install -e ".[dev]"       # test + lint + type check
pip install -e ".[dev,pipeline]"  # + toolkit, per `make check`/`make run`
```

## Comandi

| Comando | Cosa fa |
|---|---|
| `make extract` | estrae Leg19/ddlpres dal clone git |
| `make extract-all` | estrae tutte le legislature e tipologie |
| `make union` | unisce i parquet per-legislatura |
| `make check` | preflight dei 3 `dataset.yml` |
| `make run` | esegue i 3 dataset (raw→clean→mart) |
| `make test` | pytest (core + dashboard) |
| `make findings` | ricalcola il finding per famiglia |

## Aggiungere o modificare un dataset

1. Crea `datasets/<slug>/` con `dataset.yml` e `sql/`
2. `clean.sql` legge solo da `raw_input`; i `mart*.sql` solo da `clean_input`
3. Valida: `make check` (preflight) e `make run`
4. Apri PR

## Test

- `tests/` — parser, extract, git_source, union, findings
- `dashboard/tests/` — smoke delle pagine + regressione sui path GCS

Ogni test deve proteggere un contratto pubblico, una regressione già vista o
un comportamento non ovvio (vedi `infra/lab-ops/operations/test-policy.md`).

## Contratti da non rompere

- Path GCS: `gs://dataciviclab-{clean,mart}/senato-akn/<slug>/<anno>/…`
- Colonne dei dataset pubblicati e chiavi dei `mart` (documentate nel registry)
- Nomi degli slug: `senato_corpus`, `senato_dibattito`, `senato_emendamenti`
- `make check` / `make run` / `make pipeline` sono l'interfaccia usata da CI

## CI

`test.yml` esegue ruff + mypy + pytest (composite `python-ci`) e uno smoke di
estrazione da un mini repo git. `pipeline.yml` (post-merge + schedule mensile)
esegue `make pipeline`, sincronizza su GCS e apre la PR del registry.

## Regole

- Non committare output pipeline (`out/`, `data/derived/`, `*.parquet`)
- Niente logica nei workflow YAML: la logica vive nel Makefile o in `scripts/`
- Branch `feat/<descrizione>` o `fix/<descrizione>`; PR con il template del repo
- Cambi a colonne, slug o path sono cambi di contratto: dichiarali nella PR
