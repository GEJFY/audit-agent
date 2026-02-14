"""テストデータファクトリ"""

from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd


def create_journal_entries(n: int = 100, anomaly_rate: float = 0.05) -> pd.DataFrame:
    """テスト用仕訳データを生成"""
    rng = np.random.default_rng(42)

    normal_count = int(n * (1 - anomaly_rate))
    anomaly_count = n - normal_count

    # 正常仕訳
    normal_amounts = rng.lognormal(mean=12, sigma=1.5, size=normal_count)
    normal_accounts = rng.choice(["1100", "1200", "2100", "3100", "5100"], size=normal_count)

    # 異常仕訳
    anomaly_amounts = rng.lognormal(mean=18, sigma=2, size=anomaly_count)  # 異常に大きい金額
    anomaly_accounts = rng.choice(["9999", "8888", "7777"], size=anomaly_count)  # レア科目

    amounts = np.concatenate([normal_amounts, anomaly_amounts])
    accounts = np.concatenate([normal_accounts, anomaly_accounts])

    dates = pd.date_range("2026-01-01", periods=n, freq="h")

    df = pd.DataFrame(
        {
            "id": [f"JE-{i:04d}" for i in range(n)],
            "date": dates[:n],
            "account_code": accounts,
            "amount": amounts.round(0).astype(int),
            "description": [f"仕訳 {i}" for i in range(n)],
            "timestamp": dates[:n],
        }
    )

    # シャッフル
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def create_audit_project(tenant_id: str | None = None) -> dict[str, Any]:
    """テスト用監査プロジェクト"""
    return {
        "id": str(uuid4()),
        "tenant_id": tenant_id or str(uuid4()),
        "name": "J-SOX監査 2026年度",
        "status": "planning",
        "fiscal_year": 2026,
        "audit_type": "j-sox",
        "agent_mode": "audit",
    }


def create_dialogue_thread(n_messages: int = 5) -> list[dict[str, Any]]:
    """テスト用対話スレッド"""
    thread_id = str(uuid4())
    auditor_tenant = str(uuid4())
    auditee_tenant = str(uuid4())

    messages = []
    for i in range(n_messages):
        is_auditor = i % 2 == 0
        messages.append(
            {
                "id": str(uuid4()),
                "thread_id": thread_id,
                "from_tenant_id": auditor_tenant if is_auditor else auditee_tenant,
                "to_tenant_id": auditee_tenant if is_auditor else auditor_tenant,
                "from_agent": "auditor_controls_tester" if is_auditor else "auditee_response",
                "message_type": "question" if is_auditor else "answer",
                "content": f"メッセージ {i + 1}",
                "confidence": 0.8 + (i * 0.02),
            }
        )

    return messages


def create_risk_features(
    amount: float = 1_000_000,
    is_anomaly: bool = False,
    anomaly_score: float = 0.3,
) -> dict[str, Any]:
    """テスト用リスク特徴量"""
    return {
        "amount": amount,
        "amount_z_score": 1.5,
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "approval_deviation": False,
        "days_since_last_audit": 90,
        "control_deviation_rate": 3.0,
        "transaction_frequency": 10,
        "is_manual_entry": False,
        "is_period_end": False,
        "department_risk_history": 1,
    }


def create_time_series(
    n: int = 50,
    trend: float = 0.5,
    noise_level: float = 3.0,
    base: float = 100.0,
    seed: int = 42,
) -> tuple[list[float], list[str]]:
    """テスト用時系列データを生成

    Returns:
        (values, timestamps) のタプル
    """
    rng = np.random.default_rng(seed)
    values = base + np.arange(n) * trend + rng.normal(0, noise_level, n)
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    timestamps = [d.isoformat() for d in dates]
    return values.tolist(), timestamps


def create_controls_status() -> list[dict[str, Any]]:
    """テスト用統制ステータス"""
    return [
        {
            "control_id": "CTL-001",
            "name": "購買承認フロー",
            "category": "purchasing",
            "status": "effective",
            "compliance_rate": 0.95,
            "last_tested": "2026-01-15",
        },
        {
            "control_id": "CTL-002",
            "name": "売上計上プロセス",
            "category": "revenue",
            "status": "deficient",
            "compliance_rate": 0.72,
            "last_tested": "2026-01-10",
        },
        {
            "control_id": "CTL-003",
            "name": "在庫管理",
            "category": "inventory",
            "status": "effective",
            "compliance_rate": 0.88,
            "last_tested": "2026-01-20",
        },
    ]
