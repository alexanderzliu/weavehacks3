.PHONY: all validate lint format typecheck test clean

# Default target
all: validate

# Fix issues (Format + Lint Fix)
fix:
	@echo "🔧 Fixing code style issues..."
	uv run ruff format src/ tests/
	uv run ruff check --fix --unsafe-fixes src/ tests/
	@echo "✅ Fix complete."

# Full validation gate (CI equivalent) - fail fast (CI equivalent) - fail fast
validate:
	@echo "📝 1. Formatting..."
	@make --no-print-directory format-check || { echo "❌ Formatting failed. Run 'make format' to fix."; exit 1; }
	@echo "🧹 2. Linting..."
	@make --no-print-directory lint || { echo "❌ Linting failed."; exit 1; }
	@echo "🔍 3. Type Checking..."
	@make --no-print-directory typecheck || { echo "❌ Type check failed."; exit 1; }
	@echo "🏗️ 4. Architecture Tests..."
	@make --no-print-directory arch-test || { echo "❌ Arch tests failed."; exit 1; }
	@echo "🧪 5. Unit Tests..."
	@make --no-print-directory test || { echo "❌ Unit tests failed."; exit 1; }
	@echo "✅ All checks passed!"

# Formatting
format:
	uv run ruff format src/ tests/
	uv run ruff check --fix --unsafe-fixes src/ tests/

format-check:
	uv run ruff format --check src/ tests/

# Linting (Check only)
lint:
	uv run ruff check src/ tests/

# Type Checking
typecheck:
	uv run ty check

# Testing
test:
	uv run pytest tests/ -v

clean:
	rm -rf .ruff_cache .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
