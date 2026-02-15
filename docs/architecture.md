# Architecture

## System Overview

audit-agentは、内部監査の全ライフサイクルをAIエージェントで自動化するエンタープライズプラットフォームです。

## Agent Design

### Auditor Agents（監査人側: 8エージェント）

| Agent | 役割 | LLM使用 |
|-------|------|---------|
| `AuditorOrchestrator` | フェーズ管理・ルーティング | No |
| `PlannerAgent` | リスク評価・監査計画策定 | Yes |
| `DataCollectorAgent` | 外部システムからのデータ収集 | Yes |
| `ControlsTesterAgent` | 統制テスト実行・評価 | Yes |
| `AnomalyDetectiveAgent` | ML+LLMによる異常検知 | Yes |
| `ReportWriterAgent` | 監査報告書生成 | Yes |
| `FollowUpAgent` | 改善措置追跡 | No |
| `PrepAgent` | 監査準備・質問生成 | Yes |

### Auditee Agents（被監査人側: 6エージェント）

| Agent | 役割 | LLM使用 |
|-------|------|---------|
| `AuditeeOrchestrator` | リクエスト分類・ルーティング | No |
| `ResponseAgent` | 質問回答ドラフト生成 | Yes |
| `EvidenceSearchAgent` | 証跡検索・収集 | Yes |
| `ControlsMonitorAgent` | 統制モニタリング | Yes |
| `RiskAlertAgent` | 5カテゴリリスクスキャン | Yes |
| `SelfAssessmentAgent` | 自己評価実施 | Yes |

### Agent State Machine

各エージェントはLangGraph状態マシンで実装されています。

```
AuditorState:
  init → planning → fieldwork → reporting → follow_up

AuditeeState:
  idle → responding / evidence_search / monitoring
```

### Human-in-the-Loop

重要な意思決定（監査計画承認、報告書承認、高リスクアクション）では、
`AgentDecisionRecord`を通じて人間の承認を待機します。

## Database Design

### Core Models

- `AuditProject` - 監査プロジェクト（フェーズ、ステータス管理）
- `RCM` - リスク・コントロール・マトリクス
- `Finding` - 検出事項（5C: Criteria/Condition/Cause/Consequence/Corrective）
- `EvidenceRegistry` - 証跡管理（ハッシュ検証、S3パス）
- `DialogueMessage` - 対話メッセージ（監査人⇔被監査人）
- `Tenant` / `User` - マルチテナント・RBAC

### Tenant Isolation

全テーブルに`tenant_id`カラムを持ち、`BaseRepository`で自動フィルタリング。
PostgreSQL Row Level Security (RLS) による追加保護。

## ML Pipeline

| モジュール | 用途 | アルゴリズム |
|-----------|------|-------------|
| `anomaly_detection.py` | 仕訳異常検知 | Isolation Forest + LLM確認 |
| `risk_scoring.py` | リスクスコアリング | 特徴量ベース + LightGBM |
| `time_series.py` | 時系列予測 | STL分解 + Prophet |

## Security

- **JWT認証** + リフレッシュトークン
- **RBAC** (admin, auditor, auditee, viewer)
- **AES-256-GCM暗号化** (証跡ファイル)
- **SHA-256ハッシュ** (改竄検知)
- **監査証跡** (全エージェント操作記録)
- **OWASP対策** (SQLi/XSS防御、セキュリティヘッダー)
- **IP Throttling** + レート制限

## Infrastructure

```
┌────────────┐   ┌────────────┐   ┌────────────┐
│  FastAPI    │   │  Temporal  │   │  Redis     │
│  (API)     │   │  (Workflow)│   │  (Cache/   │
│            │   │            │   │   Pub/Sub) │
└─────┬──────┘   └─────┬──────┘   └─────┬──────┘
      │                │                │
      └────────┬───────┘────────────────┘
               │
      ┌────────┴────────┐
      │   PostgreSQL    │
      │   + pgvector    │
      └────────┬────────┘
               │
      ┌────────┴────────┐
      │   S3 Storage    │
      │   (Evidence)    │
      └─────────────────┘
```

## LLM Gateway

マルチプロバイダー対応のLLMゲートウェイ:

- **Primary**: Anthropic Claude (Sonnet 4.5 / Haiku 4.5)
- **Fallback**: Azure OpenAI (GPT-4o)
- **Cost Tracking**: モデル別のトークン使用量・コスト追跡
- **Retry / Fallback**: プロバイダー障害時の自動フォールバック
