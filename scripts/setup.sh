#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# audit-agent Linux/Mac セットアップスクリプト
# ═══════════════════════════════════════════════════════
set -euo pipefail

echo "=== audit-agent Setup ==="

# Python バージョン確認
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "Python version: $PYTHON_VERSION"

# 仮想環境作成
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/5] Virtual environment already exists"
fi

# 仮想環境の有効化
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate

# 依存関係インストール
echo "[3/5] Installing dependencies..."
python -m pip install --upgrade pip
pip install -e ".[dev]"

# pre-commit設定
echo "[4/5] Setting up pre-commit hooks..."
pre-commit install

# .env作成
if [ ! -f ".env" ]; then
    echo "[5/5] Creating .env from template..."
    cp .env.example .env
    echo "[NOTE] Please update .env with your actual values"
else
    echo "[5/5] .env already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Update .env with your API keys"
echo "  2. Start local services: docker compose -f docker/docker-compose.yml up -d"
echo "  3. Run migrations: make migrate"
echo "  4. Run tests: make test"
echo "  5. Start dev server: make run"
