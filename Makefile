.PHONY: install test

install:
	pip install -e ".[dev]"

test:
	pytest -v --cov=src/amt_auth --cov-report=term-missing
