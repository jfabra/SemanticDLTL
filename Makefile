# Development helpers for SemanticDLTL. Requires Python >= 3.10.
#
#   make venv     create .venv and install the package in editable mode with the dev tools
#   make test     run the test-suite
#   make lint     run ruff
#   make check    lint + test
#   make sample   run the checker on the sample model (batch mode)
#   make clean    remove caches, build artefacts and result files of the examples

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin

.PHONY: venv test lint check sample clean

venv: $(BIN)/pytest

$(BIN)/pytest: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

test: venv
	$(BIN)/pytest

lint: venv
	$(BIN)/ruff check src tests scripts

check: lint test

sample: venv
	$(BIN)/dltl-mc --log-file examples/sample --init-file examples/sample.init \
	    --formula-file examples/formulas.txt --no-interactive

clean:
	rm -rf .pytest_cache .ruff_cache build dist src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f examples/*.res examples/*.norm examples/*.forms examples/*_trace_lengths.txt
