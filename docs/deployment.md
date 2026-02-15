# Deployment Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (with pgvector extension)
- Redis 7+
- Node.js 20+ (frontend)
- Temporal Server (optional, for workflow orchestration)

## Environment Variables

```bash
# Application
APP_ENV=production          # development / testing / production
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/audit_agent

# Authentication
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_PRIMARY=claude-sonnet-4-5-20250929
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001

# Azure OpenAI (fallback)
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Storage
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_EVIDENCE=audit-evidence
S3_BUCKET_REPORTS=audit-reports

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key

# Messaging
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Workflow
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=audit-agent

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=
DATADOG_API_KEY=
```

## Local Development

```bash
# 1. Python環境セットアップ
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. 環境変数
cp .env.example .env
# .envを編集

# 3. データベース
# PostgreSQL + pgvectorが必要
createdb audit_agent
psql -d audit_agent -c "CREATE EXTENSION IF NOT EXISTS vector"

# 4. マイグレーション
alembic upgrade head

# 5. バックエンド起動
make run
# or: uvicorn src.api.main:app --reload

# 6. フロントエンド起動
cd frontend
npm install
npm run dev
```

## Docker

```bash
# ビルド
docker compose build

# 起動
docker compose up -d

# ログ確認
docker compose logs -f api
```

## CI/CD

GitHub Actionsで自動テスト・品質チェック:

1. **Unit Tests** - pytest + coverage (threshold: 60%)
2. **Lint** - ruff check
3. **Format** - ruff format --check
4. **Type Check** - mypy
5. **Frontend** - npm lint + typecheck + build

## Production Considerations

- `APP_ENV=production` でSwagger UIを無効化
- JWT secret keyは十分な長さ (32+ bytes) を使用
- PostgreSQL接続プールサイズを適切に設定
- S3バケットにKMS暗号化を有効化
- Redis認証を有効化
- Temporal Serverの高可用性構成
- Prometheus + Grafanaによる監視
- Sentry / Datadogによるエラー追跡
