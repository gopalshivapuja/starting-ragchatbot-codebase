#!/bin/bash

# Code Formatting Script
# Automatically formats code with black and isort

echo "✨ Formatting code..."
echo ""

# Run black
echo "📝 Running black formatter..."
uv run black backend/
echo ""

# Run isort
echo "📦 Sorting imports with isort..."
uv run isort backend/
echo ""

echo "✅ Code formatting complete!"
