#!/bin/bash

# Code Quality Check Script
# Runs formatting and linting tools on the codebase

echo "🔍 Running code quality checks..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Run black (auto-format)
echo "📝 Formatting code with black..."
if uv run black backend/ --check; then
    echo -e "${GREEN}✓ Black formatting check passed${NC}"
else
    echo -e "${YELLOW}⚠ Black formatting issues found. Run 'uv run black backend/' to fix${NC}"
    FAILED=1
fi
echo ""

# Run isort (import sorting)
echo "📦 Checking import sorting with isort..."
if uv run isort backend/ --check-only; then
    echo -e "${GREEN}✓ Import sorting check passed${NC}"
else
    echo -e "${YELLOW}⚠ Import sorting issues found. Run 'uv run isort backend/' to fix${NC}"
    FAILED=1
fi
echo ""

# Run flake8 (linting)
echo "🔎 Running flake8 linting..."
if uv run flake8 backend/ --max-line-length=88 --extend-ignore=E203,W503; then
    echo -e "${GREEN}✓ Flake8 linting passed${NC}"
else
    echo -e "${RED}✗ Flake8 linting found issues${NC}"
    FAILED=1
fi
echo ""

# Run mypy (type checking)
echo "🔬 Running mypy type checking..."
if uv run mypy backend/ --ignore-missing-imports --no-strict-optional; then
    echo -e "${GREEN}✓ Mypy type checking passed${NC}"
else
    echo -e "${RED}✗ Mypy type checking found issues${NC}"
    FAILED=1
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some quality checks failed. Please review the output above.${NC}"
    exit 1
fi
