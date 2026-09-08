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

LEGISLATURA ?= Leg19
LEGISLATURE ?= Leg14 Leg15 Leg16 Leg17 Leg18 Leg19
TIPOLOGIE_ALL = ddlpres,emend,emendc,ddlmess,ddlcomm,resaula,sommcomm

.PHONY: extract
extract:
	$(PYTHON) scripts/extract.py --legislatura $(LEGISLATURA) --drop-zero-text

# Delta: processa solo i file cambiati (manifest + snapshot accanto a --out)
.PHONY: extract-incremental
extract-incremental:
	$(PYTHON) scripts/extract.py --legislatura $(LEGISLATURA) --drop-zero-text --incremental

# Full: tutte le tipologie con parser per una legislatura
.PHONY: extract-full
extract-full:
	$(PYTHON) scripts/extract.py --legislatura $(LEGISLATURA) --tipologie $(TIPOLOGIE_ALL) \
		--drop-zero-text

# Estrai tutte le legislature disponibili (sequenziale)
.PHONY: extract-all
extract-all:
	@for leg in $(LEGISLATURE); do \
		echo "=== Estrazione $$leg (atti: ddlpres,ddlmess,ddlcomm) ==="; \
		$(PYTHON) scripts/extract.py --legislatura $$leg --tipologie ddlpres --drop-zero-text; \
		$(PYTHON) scripts/extract.py --legislatura $$leg --tipologie ddlmess --drop-zero-text; \
		$(PYTHON) scripts/extract.py --legislatura $$leg --tipologie ddlcomm --drop-zero-text; \
		echo "=== Estrazione $$leg (emend+emendc) ==="; \
		$(PYTHON) scripts/extract.py --legislatura $$leg --tipologie emend,emendc --drop-zero-text; \
		echo "=== Estrazione $$leg (dibattito) ==="; \
		$(PYTHON) scripts/extract.py --legislatura $$leg --tipologie resaula,sommcomm --drop-zero-text; \
	done

# Unisci parquet per-legislatura in file unificati (tutte le legislature)
.PHONY: union
union:
	$(PYTHON) scripts/union_legislatures.py

# Full pipeline: estrai + unisci
.PHONY: extract-union
extract-union: extract-all union

.PHONY: summarize
summarize:
	@echo "build_summaries.py rimosso — le aggregazioni sono nei mart SQL"

# --- Layer toolkit (raw local_file -> clean -> mart) ---

.PHONY: run-senato-corpus
run-senato-corpus:
	$(PYTHON) -m toolkit.cli.app run --config datasets/senato-corpus/dataset.yml

.PHONY: run-senato-dibattito
run-senato-dibattito:
	$(PYTHON) -m toolkit.cli.app run --config datasets/senato-dibattito/dataset.yml

.PHONY: run-senato-emendamenti
run-senato-emendamenti:
	$(PYTHON) -m toolkit.cli.app run --config datasets/senato-emendamenti/dataset.yml

.PHONY: run-all
run-all: run-senato-corpus run-senato-dibattito run-senato-emendamenti

.PHONY: check-senato-corpus
check-senato-corpus:
	$(PYTHON) -m toolkit.cli.app run preflight --config datasets/senato-corpus/dataset.yml

.PHONY: check-senato-dibattito
check-senato-dibattito:
	$(PYTHON) -m toolkit.cli.app run preflight --config datasets/senato-dibattito/dataset.yml

.PHONY: check-senato-emendamenti
check-senato-emendamenti:
	$(PYTHON) -m toolkit.cli.app run preflight --config datasets/senato-emendamenti/dataset.yml

.PHONY: check-all
check-all: check-senato-corpus check-senato-dibattito check-senato-emendamenti

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

# --- Pipeline completa (CI chiama questo) ---

.PHONY: git-clone
git-clone:
	@for leg in $(LEGISLATURE); do \
		echo "=== Materializza $$leg ==="; \
		$(PYTHON) -c "from senato_akn.git_source import ensure_repo; ensure_repo('data/raw/akn', '$$leg')"; \
	done

.PHONY: pipeline
pipeline: git-clone extract-all union run-all

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
