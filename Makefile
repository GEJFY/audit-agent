.PHONY: help install dev lint format typecheck test test-unit test-integration test-e2e coverage clean docker-up docker-down migrate seed

# ── デフォルトターゲット ──────────────────────────────
help: ## ヘルプ表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── セットアップ ──────────────────────────────────────
install: ## 本番依存関係インストール
	pip install -e .

dev: ## 開発依存関係インストール
	pip install -e ".[dev]"
	pre-commit install

# ── コード品質 ────────────────────────────────────────
lint: ## Lintチェック実行
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## コード自動フォーマット
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck: ## 型チェック実行
	mypy src/

# ── テスト ────────────────────────────────────────────
test: ## 全テスト実行
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit: ## ユニットテストのみ
	pytest tests/unit/ -v -m unit

test-integration: ## 統合テストのみ
	pytest tests/integration/ -v -m integration

test-e2e: ## E2Eテストのみ
	pytest tests/e2e/ -v -m e2e

coverage: ## カバレッジレポート生成
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "HTMLレポート: htmlcov/index.html"

# ── セキュリティ ──────────────────────────────────────
security: ## セキュリティスキャン
	pip-audit
	bandit -r src/ -c pyproject.toml

# ── データベース ──────────────────────────────────────
migrate: ## マイグレーション実行
	alembic upgrade head

migrate-create: ## 新規マイグレーション作成
	alembic revision --autogenerate -m "$(msg)"

migrate-down: ## マイグレーションロールバック
	alembic downgrade -1

seed: ## テストデータ投入
	python scripts/seed_data.py

# ── Docker ────────────────────────────────────────────
docker-up: ## Docker開発環境起動
	docker compose -f docker/docker-compose.yml up -d

docker-down: ## Docker開発環境停止
	docker compose -f docker/docker-compose.yml down

docker-build: ## Dockerイメージビルド
	docker build -f docker/Dockerfile -t audit-agent:latest .

docker-logs: ## Dockerログ表示
	docker compose -f docker/docker-compose.yml logs -f

# ── アプリケーション ──────────────────────────────────
run: ## 開発サーバー起動
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# ── クリーンアップ ────────────────────────────────────
clean: ## ビルド成果物削除
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage

# ── CI再現 ────────────────────────────────────────────
ci: lint typecheck test security ## CIパイプライン全体を再現
