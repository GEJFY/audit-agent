@echo off
REM ═══════════════════════════════════════════════════════
REM audit-agent Windows セットアップスクリプト
REM ═══════════════════════════════════════════════════════

echo === audit-agent Setup ===

REM Python バージョン確認
python --version 2>NUL
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)

REM 仮想環境作成
if not exist ".venv" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/5] Virtual environment already exists
)

REM 仮想環境の有効化
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat

REM 依存関係インストール
echo [3/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -e ".[dev]"

REM pre-commit設定
echo [4/5] Setting up pre-commit hooks...
pre-commit install

REM .env作成
if not exist ".env" (
    echo [5/5] Creating .env from template...
    copy .env.example .env
    echo [NOTE] Please update .env with your actual values
) else (
    echo [5/5] .env already exists
)

echo.
echo === Setup Complete ===
echo.
echo Next steps:
echo   1. Update .env with your API keys
echo   2. Start local services: docker compose -f docker/docker-compose.yml up -d
echo   3. Run migrations: make migrate
echo   4. Run tests: make test
echo   5. Start dev server: make run
