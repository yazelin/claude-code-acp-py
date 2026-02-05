.PHONY: install test test-unit test-integration test-mcp test-all coverage lint clean

# Install dependencies
install:
	uv sync --extra dev

# Run all tests
test:
	uv run pytest tests/ -v

# Run only unit tests (fast, no external dependencies)
test-unit:
	uv run pytest tests/test_unit_*.py -v

# Run integration tests (require Claude CLI)
test-integration:
	uv run pytest tests/test_integration_*.py -v

# Run MCP tests (slow, require nanobanana)
test-mcp:
	uv run pytest tests/test_integration_mcp.py -v

# Run all tests with coverage
test-all:
	uv run pytest tests/test_unit_*.py tests/test_integration_*.py -v --cov=claude_code_acp --cov-report=term-missing

# Generate coverage report
coverage:
	uv run pytest tests/ --cov=claude_code_acp --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Run linter
lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

# Format code
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

# Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Build package
build: clean
	uv build

# Publish to PyPI
publish: build
	uv publish
