#!/bin/bash
set -e

echo "🔍 Running Verification Gates..."

echo "1. Type Checking (ty)..."
uv run ty check

echo "2. Linting (ruff)..."
uv run ruff check src/ tests/

echo "3. Formatting (ruff)..."
uv run ruff format --check src/ tests/

echo "4. Architecture & Standards Tests..."
uv run pytest tests/test_architecture.py -v

echo "✅ All clean code assertions passed!"
