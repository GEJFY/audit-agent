"""audit-agent データベース初期化スクリプト.

pgvector拡張の有効化、RLSポリシーの設定、初期データの投入を行う。

使用方法:
    python -m infrastructure.scripts.init_db
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import get_settings


async def init_extensions(engine) -> None:  # type: ignore[no-untyped-def]
    """PostgreSQL拡張を有効化."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        print("[OK] PostgreSQL extensions enabled")


async def init_rls_policies(engine) -> None:  # type: ignore[no-untyped-def]
    """RLS (Row Level Security) ポリシーを設定.

    テナント分離のためのRLSポリシーを全テナント対応テーブルに適用する。
    """
    # tenant_idカラムを持つテーブル一覧
    tenant_tables = [
        "users",
        "audit_projects",
        "risk_universe",
        "audit_plans",
        "rcm",
        "test_results",
        "anomalies",
        "findings",
        "reports",
        "remediation_actions",
        "agent_decisions",
        "approval_queue",
        "auditee_responses",
        "evidence_registry",
        "risk_alerts",
        "controls_status",
        "self_assessments",
        "prep_checklists",
        "dialogue_messages",
    ]

    async with engine.begin() as conn:
        for table in tenant_tables:
            # テーブルが存在するか確認
            result = await conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT FROM information_schema.tables "
                    "  WHERE table_name = :table_name"
                    ")"
                ),
                {"table_name": table},
            )
            exists = result.scalar()

            if not exists:
                print(f"[SKIP] Table '{table}' does not exist yet")
                continue

            # RLSを有効化
            await conn.execute(
                text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            )

            # テナント分離ポリシー
            policy_name = f"{table}_tenant_isolation"
            await conn.execute(
                text(f"DROP POLICY IF EXISTS {policy_name} ON {table}")
            )
            await conn.execute(
                text(
                    f"CREATE POLICY {policy_name} ON {table} "
                    f"USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"
                )
            )

        print(f"[OK] RLS policies applied to {len(tenant_tables)} tables")


async def main() -> None:
    """メイン実行."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)

    try:
        print("=== audit-agent Database Initialization ===")
        await init_extensions(engine)
        await init_rls_policies(engine)
        print("=== Initialization Complete ===")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
