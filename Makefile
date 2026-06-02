PYTHON ?= python3

.PHONY: extract summarize all

extract:
	$(PYTHON) scripts/extract_leg19_ddlpres.py --out data/derived/leg19_ddlpres_v0.csv
	$(PYTHON) scripts/extract_leg19_ddlpres.py --out data/derived/leg19_ddlpres_v0_nonzero.csv --drop-zero-text

summarize:
	$(PYTHON) scripts/build_summaries.py

all: extract summarize

.PHONY: clean
clean:
	rm -f data/derived/*.csv
