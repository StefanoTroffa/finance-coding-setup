#!/bin/bash
# Bootstrap the finance-coding-setup environment.
# Run once after cloning: bash setup.sh
#
# What this does:
#   1. Installs uv (Python package manager) if not present
#   2. Installs Python + all financial/document libraries
#   3. Sets up quality hooks that catch common mistakes
#   4. Creates output directory and .env file
#
# Safe to run multiple times — it won't break anything.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "Setting up your finance coding environment..."
echo ""

# --- 1. Install uv ---
if ! command -v uv &> /dev/null; then
    echo "[1/5] Installing uv (Python package manager)..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        echo "  On Windows, run this in PowerShell instead:"
        echo "  powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\""
        echo ""
        echo "  Then close and reopen your terminal, and run this script again."
        exit 1
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the env file uv creates so it's available immediately
    if [ -f "$HOME/.local/bin/env" ]; then
        . "$HOME/.local/bin/env"
    fi
    export PATH="$HOME/.local/bin:$PATH"
    echo "  uv installed."
else
    echo "[1/5] uv already installed ($(uv --version))"
fi

# Verify uv is actually available
if ! command -v uv &> /dev/null; then
    echo ""
    echo "ERROR: uv was installed but isn't in your PATH yet."
    echo "Close this terminal, open a new one, and run: bash setup.sh"
    exit 1
fi

# --- 2. Install Python + packages ---
echo "[2/5] Installing Python and packages (this may take a minute)..."
cd "$REPO_DIR"
uv sync 2>&1 | tail -1
echo "  Done. Packages installed:"
echo "    Data:    pandas, numpy, openpyxl, xlsxwriter"
echo "    Finance: yfinance, fredapi"
echo "    Charts:  plotly"
echo "    Docs:    pdfplumber, python-docx, tabula-py"

# --- 3. Create output directory ---
echo "[3/5] Creating ~/finance-outputs/ for your generated files..."
mkdir -p ~/finance-outputs

# --- 4. Set up quality hooks ---
echo "[4/5] Setting up quality hooks..."
chmod +x "$REPO_DIR/hooks/"*.py 2>/dev/null || true
chmod +x "$REPO_DIR/hooks/pre-commit" 2>/dev/null || true

# Install git pre-commit hook if this is a git repo
if [ -d "$REPO_DIR/.git" ]; then
    mkdir -p "$REPO_DIR/.git/hooks"
    cp "$REPO_DIR/hooks/pre-commit" "$REPO_DIR/.git/hooks/pre-commit"
    chmod +x "$REPO_DIR/.git/hooks/pre-commit"
    echo "  Pre-commit hook installed (catches secrets before they're pushed)."
else
    echo "  Skipped git hook (not a git repo yet — run 'git init' first if you want it)."
fi

# --- 5. Create .env from template ---
echo "[5/5] Setting up API key storage..."
if [ ! -f "$REPO_DIR/.env" ]; then
    if [ -f "$REPO_DIR/.env.example" ]; then
        cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
        echo "  Created .env file. Add your API keys there when you have them."
    fi
else
    echo "  .env already exists (keeping your existing keys)."
fi

# --- Done ---
echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "  To start working:"
echo ""
echo "    cd $REPO_DIR"
echo "    claude"
echo ""
echo "  Then just describe what you need."
echo "  Example: 'Pull the last year of SPY prices and save to Excel'"
echo ""
echo "  Your output files will appear in: ~/finance-outputs/"
echo ""
