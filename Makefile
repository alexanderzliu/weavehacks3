.PHONY: all validate lint format typecheck test clean install

# Backend directory
BACKEND_DIR := backend

# Default target
all: validate

# Install dev dependencies
install:
	@echo "📦 Installing backend dev dependencies..."
	cd $(BACKEND_DIR) && uv sync --group dev

# Fix issues (Format + Lint Fix)
fix:
	@echo "🔧 Fixing code style issues..."
	cd $(BACKEND_DIR) && uv run ruff format .
	cd $(BACKEND_DIR) && uv run ruff check --fix --unsafe-fixes .
	@echo "✅ Fix complete."

# Full validation gate (CI equivalent) - fail fast
validate:
	@echo "📝 1. Formatting..."
	@make --no-print-directory format-check || { echo "❌ Formatting failed. Run 'make fix' to fix."; exit 1; }
	@echo "🧹 2. Linting..."
	@make --no-print-directory lint || { echo "❌ Linting failed."; exit 1; }
	@echo "🔍 3. Type Checking (warnings only)..."
	@make --no-print-directory typecheck || echo "⚠️  Type check has warnings (non-blocking)"
	@echo "✅ All checks passed!"

# Formatting
format:
	cd $(BACKEND_DIR) && uv run ruff format .
	cd $(BACKEND_DIR) && uv run ruff check --fix --unsafe-fixes .

format-check:
	cd $(BACKEND_DIR) && uv run ruff format --check .

# Linting (Check only)
lint:
	cd $(BACKEND_DIR) && uv run ruff check .

# Type Checking
typecheck:
	cd $(BACKEND_DIR) && uv run ty check

# Testing (optional - only runs if tests exist)
test:
	@if [ -d "$(BACKEND_DIR)/tests" ] && [ "$$(ls -A $(BACKEND_DIR)/tests 2>/dev/null)" ]; then \
		cd $(BACKEND_DIR) && uv run pytest tests/ -v; \
	else \
		echo "⚠️  No tests found, skipping..."; \
	fi

clean:
	rm -rf $(BACKEND_DIR)/.ruff_cache $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.mypy_cache
	find $(BACKEND_DIR) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
