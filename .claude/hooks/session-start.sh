#!/bin/bash
# Session Start Hook for Datagen
# Auto-runs quality checks when Claude Code sessions start

set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Datagen Development Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if we're in the datagen repo
if [ ! -f "pyproject.toml" ]; then
    echo "⚠️  Warning: Not in datagen repository root"
    exit 0
fi

# Show current phase and priority
if [ -f "GOAL.md" ]; then
    echo "📋 Current Phase:"
    grep "Current Phase:" GOAL.md 2>/dev/null | head -1 || echo "  Check GOAL.md for details"
    echo ""
fi

# Git status check
echo "📊 Git Status:"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "  Branch: $CURRENT_BRANCH"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "  ⚠️  Uncommitted changes present"
else
    echo "  ✅ Working tree clean"
fi
echo ""

# Test status check
echo "🧪 Test Status:"
if command -v pytest &> /dev/null; then
    # Run tests with minimal output
    if pytest tests/ -q --tb=no --no-header 2>&1 | tail -5; then
        echo "  ✅ All tests passing"
    else
        echo "  ❌ Tests failing - run 'pytest tests/ -v' for details"
    fi
else
    echo "  ⚠️  pytest not found - run: pip install -e .[dev]"
fi
echo ""

# Code quality check
echo "🔍 Code Quality:"
if command -v ruff &> /dev/null; then
    RUFF_ISSUES=$(ruff check src/ tests/ 2>&1 | grep -c "error\|warning" || echo "0")
    if [ "$RUFF_ISSUES" -eq 0 ]; then
        echo "  ✅ No linting issues"
    else
        echo "  ⚠️  $RUFF_ISSUES linting issues found"
        echo "     Run: ruff check src/ tests/"
    fi
else
    echo "  ⚠️  ruff not found - run: pip install ruff"
fi

# Check if black is happy with formatting
if command -v black &> /dev/null; then
    if black --check src/ tests/ &> /dev/null; then
        echo "  ✅ Code formatting clean"
    else
        FILES_TO_FORMAT=$(black --check src/ tests/ 2>&1 | grep -c "would reformat" || echo "0")
        echo "  ⚠️  $FILES_TO_FORMAT files need formatting"
        echo "     Run: black src/ tests/"
    fi
else
    echo "  ⚠️  black not found - run: pip install black"
fi
echo ""

# Coverage info (if .coverage exists)
if [ -f ".coverage" ]; then
    echo "📈 Test Coverage:"
    if command -v coverage &> /dev/null; then
        COVERAGE=$(coverage report --precision=1 2>/dev/null | grep "TOTAL" | awk '{print $NF}' || echo "unknown")
        echo "  Current: $COVERAGE (Target: 75%)"
    fi
    echo ""
fi

# Next priority reminder
echo "🎯 Next Priority:"
if [ -f "PRD.md" ]; then
    grep -A 3 "🚧 IN PROGRESS" PRD.md 2>/dev/null | head -4 || echo "  Check PRD.md for current work"
else
    echo "  Feature #1: Entity Vintage Effects (12-16h effort)"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 Quick Commands: pytest tests/ -v  |  ruff check src/  |  black src/ tests/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
