.PHONY: install test test-fast test-file cov-html clean

# ── deps ──────────────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"

# ── testing ───────────────────────────────────────────────────────────────────

## Full run: verbose output + coverage table in the terminal
test:
	pytest -v --cov=src/amt_auth --cov-report=term-missing

## Quick run: no coverage, one-line-per-test, short tracebacks
test-fast:
	pytest -q --tb=short

## Run a single file:  make test-file FILE=tests/test_validator.py
test-file:
	pytest -v $(FILE)

## Run tests matching a keyword:  make test-k K=expired
test-k:
	pytest -v -k "$(K)"

## Generate HTML coverage report then open it in the browser
cov-html:
	pytest --cov=src/amt_auth --cov-report=html
	python -m webbrowser htmlcov/index.html

# ── housekeeping ──────────────────────────────────────────────────────────────

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache htmlcov .coverage
