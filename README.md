# audit-agent

**Enterprise AI Audit Agent Platform** - 双方向AI監査エージェントプラットフォーム

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

監査人側（Auditor）8エージェントと被監査人側（Auditee）6エージェントが自律的に協調動作し、内部監査の計画策定から指摘事項フォローアップまでを包括的に支援する、エンタープライズグレードのAI監査プラットフォームです。

## Features

- **14 AI Agents** - LangGraph状態マシンによる8監査人+6被監査人エージェント
- **Dialogue Bus** - Redis Streams + Kafkaによる双方向対話バス
- **LLM Gateway** - Anthropic Claude / Azure OpenAI マルチプロバイダー対応
- **ML Pipeline** - 異常検知（Isolation Forest）、リスクスコアリング、時系列予測
- **FastAPI** - JWT認証、RBAC、テナント分離、OWASP準拠セキュリティ
- **PostgreSQL + pgvector** - ベクトル検索によるセマンティックRAG
- **Temporal** - ワークフローオーケストレーション
- **APAC Multi-Region** - JP/SG/HK/AU/TW/KR/TH対応、SOC2/ISO27001/GDPR/PDPA/PIPL準拠
- **SLA Monitoring** - Tier別SLA目標管理・違反検出

## Quick Start

```bash
# リポジトリクローン
git clone https://github.com/GEJFY/audit-agent.git
cd audit-agent

# Python仮想環境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -e ".[dev]"

# 環境変数設定
cp .env.example .env
# .envファイルを編集してAPI keysを設定

# テスト実行
make test-unit

# 開発サーバー起動
make run
```

## Project Structure

```
audit-agent/
├── src/
│   ├── agents/          # 14 AI Agents (auditor + auditee)
│   ├── analytics/       # クロス企業分析・ポートフォリオリスク
│   ├── api/             # FastAPI routes, middleware, schemas
│   ├── config/          # 設定、定数、リージョン、Tier管理
│   ├── connectors/      # 外部システム連携 (SAP, SharePoint, Box, Email)
│   ├── db/              # SQLAlchemy models, repositories
│   ├── dialogue/        # 対話プロトコル、Kafka Bus
│   ├── llm_gateway/     # LLMプロバイダー、コスト追跡、プロンプト
│   ├── ml/              # 異常検知、リスクスコアリング、時系列予測
│   ├── monitoring/      # ヘルスチェック、SLA監視、メトリクス、ログ
│   ├── notifications/   # Slack / Teams 通知
│   ├── reports/         # 報告書テンプレート、エグゼクティブサマリー
│   ├── risk_templates/  # リスク評価テンプレート
│   ├── security/        # 認証、RBAC、暗号化、監査証跡、コンプライアンス
│   ├── storage/         # S3ストレージ、ベクトルDB
│   └── workflows/       # Temporal ワークフロー定義
├── tests/
│   ├── unit/            # ユニットテスト (~400+ tests)
│   └── integration/     # 統合テスト
├── frontend/            # Next.js フロントエンド
├── docs/                # ドキュメント
└── pyproject.toml       # プロジェクト設定
```

## Architecture

詳細は [docs/architecture.md](docs/architecture.md) を参照。

```
┌──────────────────────────────────────────────┐
│                 Frontend (Next.js)            │
├──────────────────────────────────────────────┤
│              FastAPI + WebSocket              │
│  ┌─────────┐ ┌──────────┐ ┌───────────────┐ │
│  │  Auth    │ │ Projects │ │  Compliance   │ │
│  │  RBAC    │ │ Agents   │ │  Analytics    │ │
│  └─────────┘ └──────────┘ └───────────────┘ │
├──────────────────────────────────────────────┤
│            Dialogue Bus (Kafka/Redis)        │
│  ┌──────────────┐     ┌──────────────────┐  │
│  │ 8 Auditor    │◄───►│ 6 Auditee        │  │
│  │   Agents     │     │   Agents         │  │
│  └──────────────┘     └──────────────────┘  │
├──────────────────────────────────────────────┤
│  LLM Gateway  │  ML Pipeline  │  Temporal   │
│  (Claude/GPT) │  (Anomaly/    │  (Workflow  │
│               │   Risk/TS)    │   Orch.)    │
├──────────────────────────────────────────────┤
│  PostgreSQL + pgvector  │  S3  │  Redis     │
└──────────────────────────────────────────────┘
```

## Development

```bash
# テスト（ユニットのみ）
make test-unit

# テスト（カバレッジ付き）
python -m pytest tests/unit/ --cov=src --cov-report=term-missing

# Lint
make lint

# フォーマット
make format

# 型チェック
python -m mypy src/

# フロントエンド
cd frontend && npm install && npm run dev
```

## Documentation

| ドキュメント | 説明 |
|------------|------|
| [Architecture](docs/architecture.md) | システムアーキテクチャ・エージェント設計 |
| [API Reference](docs/api-reference.md) | 全APIエンドポイント仕様 |
| [Deployment](docs/deployment.md) | デプロイ・環境構築ガイド |
| [Development](docs/development.md) | 開発者ガイド・テスト方法 |
| [Compliance](docs/compliance.md) | コンプライアンスフレームワーク |

## License

MIT License
