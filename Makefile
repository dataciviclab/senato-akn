PYTHON ?= python3
VENV := .venv

# --- Setup ambiente ---

.PHONY: install
install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -e ".[dev]"

# --- Estrazione ---

.PHONY: extract
extract:
	$(PYTHON) scripts/extract_leg19_ddlpres.py --out data/derived/leg19_ddlpres_v0.csv
	$(PYTHON) scripts/extract_leg19_ddlpres.py --out data/derived/leg19_ddlpres_v0_nonzero.csv --drop-zero-text

.PHONY: summarize
summarize:
	$(PYTHON) scripts/build_summaries.py

.PHONY: all
all: extract summarize

# --- Test ---

.PHONY: test
test:
	$(PYTHON) -m pytest tests/ -v --tb=short

.PHONY: ci
ci:
	$(PYTHON) -m pytest tests/ -v --tb=short
	$(PYTHON) scripts/extract_leg19_ddlpres.py --limit 2 --out /tmp/senato-ci-test.csv
	$(PYTHON) scripts/build_summaries.py --input /tmp/senato-ci-test.csv --out-families /tmp/senato-ci-families.csv --out-monthly /tmp/senato-ci-monthly.csv

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
