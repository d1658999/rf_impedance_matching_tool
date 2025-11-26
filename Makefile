.PHONY: install install-dev test lint format coverage clean run help

PYTHON := python3
PIP := $(PYTHON) -m pip

help:
	@echo "SNP Tool - RF Impedance Matching Optimization"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install package in production mode"
	@echo "  install-dev  Install package with development dependencies"
	@echo "  test         Run pytest tests"
	@echo "  lint         Run flake8 and black check"
	@echo "  format       Format code with black"
	@echo "  coverage     Run tests with coverage report"
	@echo "  clean        Remove build artifacts and cache"
	@echo "  run          Run CLI tool (use ARGS='...' for arguments)"
	@echo ""

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[all]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m flake8 src/ tests/ --max-line-length=100 --ignore=E501,W503
	$(PYTHON) -m black --check src/ tests/

format:
	$(PYTHON) -m black src/ tests/

coverage:
	$(PYTHON) -m pytest tests/ --cov=src/snp_tool --cov-report=term-missing --cov-report=html

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

run:
	$(PYTHON) -m snp_tool.main $(ARGS)

# Development shortcuts
.PHONY: t l f c
t: test
l: lint
f: format
c: clean
