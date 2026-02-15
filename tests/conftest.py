"""共通テストフィクスチャ"""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# テスト用に環境変数を設定
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-bytes-ok!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


# ── テナント・ユーザーフィクスチャ ────────────────────
@pytest.fixture
def auditor_tenant_id() -> UUID:
    return UUID("10000000-0000-0000-0000-000000000001")


@pytest.fixture
def auditee_tenant_id() -> UUID:
    return UUID("20000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_user_id() -> UUID:
    return UUID("30000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_project_id() -> UUID:
    return UUID("40000000-0000-0000-0000-000000000001")


# ── LLMモックフィクスチャ ─────────────────────────────
@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """LLMゲートウェイのモック"""
    from src.llm_gateway.providers.base import LLMResponse

    gateway = MagicMock()

    default_response = LLMResponse(
        content='{"result": "test"}',
        model="claude-sonnet-4-5-20250929",
        provider="anthropic",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_usd=0.001,
        latency_ms=500.0,
    )

    gateway.generate = AsyncMock(return_value=default_response)
    gateway.generate_structured = AsyncMock(return_value=default_response)
    gateway.health_check = AsyncMock(return_value={"anthropic": True})

    return gateway


# ── 監査証跡フィクスチャ ──────────────────────────────
@pytest.fixture
def audit_trail() -> Any:
    """監査証跡サービス"""
    from src.security.audit_trail import AuditTrailService

    return AuditTrailService()


# ── RBAC フィクスチャ ─────────────────────────────────
@pytest.fixture
def rbac_service() -> Any:
    """RBACサービス"""
    from src.security.rbac import RBACService

    return RBACService()


# ── サンプルデータフィクスチャ ─────────────────────────
@pytest.fixture
def sample_journal_entries() -> list[dict[str, Any]]:
    """サンプル仕訳データ"""
    return [
        {"id": "JE-001", "date": "2026-01-15", "account_code": "1100", "amount": 500000, "description": "売上計上"},
        {"id": "JE-002", "date": "2026-01-15", "account_code": "5100", "amount": -500000, "description": "売上原価"},
        {"id": "JE-003", "date": "2026-01-31", "account_code": "1100", "amount": 50000000, "description": "期末調整"},
        {"id": "JE-004", "date": "2026-02-01", "account_code": "9999", "amount": 100, "description": "テスト仕訳"},
        {"id": "JE-005", "date": "2026-01-20", "account_code": "1100", "amount": 300000, "description": "通常売上"},
    ]


@pytest.fixture
def sample_dialogue_question() -> dict[str, Any]:
    """サンプル対話質問"""
    return {
        "id": str(uuid4()),
        "type": "question",
        "content": "購買承認フローの詳細と、Q3の承認記録一式を提出してください。",
        "from_agent": "auditor_controls_tester",
        "project_id": str(uuid4()),
    }


@pytest.fixture
def sample_risk_features() -> dict[str, Any]:
    """サンプルリスク特徴量"""
    return {
        "amount": 50_000_000,
        "amount_z_score": 3.5,
        "is_anomaly": True,
        "anomaly_score": 0.85,
        "approval_deviation": True,
        "days_since_last_audit": 180,
        "control_deviation_rate": 12.0,
        "transaction_frequency": 5,
        "is_manual_entry": True,
        "is_period_end": True,
        "department_risk_history": 3,
    }


@pytest.fixture
def sample_time_series_data() -> list[float]:
    """サンプル時系列データ（20ポイント）"""
    import numpy as np

    rng = np.random.default_rng(42)
    base = np.linspace(100, 120, 20)
    noise = rng.normal(0, 3, 20)
    return (base + noise).tolist()


# ── Agent レジストリ リセット ─────────────────────────
@pytest.fixture(autouse=True)
def reset_agent_registry() -> Any:
    """テスト間でAgentRegistryをリセット"""
    from src.agents.registry import AgentRegistry

    AgentRegistry._instance = None
    AgentRegistry._agents = {}
    yield
    AgentRegistry._instance = None
    AgentRegistry._agents = {}


# ── Dialogue メッセージ生成ヘルパー ──────────────────
@pytest.fixture
def make_dialogue_message() -> Any:
    """DialogueMessageSchemaを簡単に生成するヘルパー"""
    from src.config.constants import DialogueMessageType
    from src.dialogue.protocol import DialogueMessageSchema

    def _make(
        content: str = "テストメッセージ",
        msg_type: str = "question",
        confidence: float | None = None,
        **kwargs: Any,
    ) -> DialogueMessageSchema:
        return DialogueMessageSchema(
            from_tenant_id=kwargs.get("from_tenant_id", uuid4()),
            to_tenant_id=kwargs.get("to_tenant_id", uuid4()),
            from_agent=kwargs.get("from_agent", "test_agent"),
            message_type=DialogueMessageType(msg_type),
            content=content,
            confidence=confidence,
            **{k: v for k, v in kwargs.items() if k not in ("from_tenant_id", "to_tenant_id", "from_agent")},
        )

    return _make
