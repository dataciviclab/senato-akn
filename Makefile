PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python3

# --- Setup ambiente (idempotente) ---

$(VENV):
	$(PYTHON) -m venv $(VENV)

.PHONY: install
install: $(VENV)
	$(VENV_PYTHON) -m pip install -e ".[dev]"

# --- Estrazione (sorgente: clone git upstream, git_source) ---

.PHONY: extract
extract:
	$(PYTHON) scripts/extract.py --drop-zero-text

# Delta: processa solo i file cambiati (manifest + snapshot accanto a --out)
.PHONY: extract-incremental
extract-incremental:
	$(PYTHON) scripts/extract.py --drop-zero-text --incremental

# Full: le tipologie con parser (incl. emendc; resaula/sommcomm fuori finché
# non c'è il parser an:debate)
.PHONY: extract-full
extract-full:
	$(PYTHON) scripts/extract.py --tipologie ddlpres,emend,emendc,ddlmess,ddlcomm \
		--drop-zero-text

.PHONY: summarize
summarize:
	$(PYTHON) scripts/build_summaries.py

# --- Layer toolkit (raw local_file -> clean -> mart) ---

.PHONY: run-senato-corpus
run-senato-corpus:
	$(PYTHON) -m toolkit.cli.app run --config datasets/senato-corpus/dataset.yml

.PHONY: check-senato-corpus
check-senato-corpus:
	$(PYTHON) -m toolkit.cli.app run preflight --config datasets/senato-corpus/dataset.yml

.PHONY: all
all: extract summarize

# --- Test (richiede make install prima) ---

.PHONY: test
test: install
	$(VENV_PYTHON) -m pytest tests/ -v --tb=short

# --- CI (auto-sufficiente da checkout pulito) ---

.PHONY: ci
ci: install
	$(VENV_PYTHON) -m pytest tests/ -v --tb=short
	# smoke: mini repo git + extract + summarize (nessuna rete)
	rm -rf /tmp/senato-smoke
	mkdir -p /tmp/senato-smoke/Leg19/Atto00055177/ddlpres
	cp tests/fixtures/sample.akn.xml \
	   /tmp/senato-smoke/Leg19/Atto00055177/ddlpres/01360967-ft.akn.xml
	git -C /tmp/senato-smoke init -q
	git -C /tmp/senato-smoke add -A
	git -C /tmp/senato-smoke -c user.email=t -c user.name=t commit -qm smoke
	$(VENV_PYTHON) scripts/extract.py --repo-dir /tmp/senato-smoke \
	  --limit 1 --out /tmp/senato-ci-test.parquet
	$(VENV_PYTHON) scripts/build_summaries.py --input /tmp/senato-ci-test.parquet \
	  --out-families /tmp/senato-ci-families.csv --out-monthly /tmp/senato-ci-monthly.csv

# --- Pulizia ---

.PHONY: clean
clean:
	rm -rf $(VENV) .pytest_cache __pycache__
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-data
clean-data:
	rm -f data/derived/*.csv

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:' Makefile | sort
