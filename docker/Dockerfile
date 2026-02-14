# ═══════════════════════════════════════════════════════
# audit-agent マルチステージDockerビルド
# ═══════════════════════════════════════════════════════

# ── Stage 1: 依存関係インストール ─────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルのみコピー（キャッシュ効率化）
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ── Stage 2: テスト実行（CIで使用） ──────────────────
FROM builder AS test

COPY . .
RUN pip install --no-cache-dir ".[dev]"
CMD ["pytest", "tests/", "-v", "--cov=src"]

# ── Stage 3: 本番イメージ ─────────────────────────────
FROM python:3.11-slim AS production

# セキュリティ: 非rootユーザー
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# システム依存関係（ランタイムのみ）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージをビルダーからコピー
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションコード
COPY src/ ./src/
COPY alembic.ini ./
COPY pyproject.toml ./

# ログディレクトリ
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# 非rootユーザーに切替
USER appuser

# 環境変数
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    APP_PORT=8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
