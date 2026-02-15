"""audit-agent テストデータ投入スクリプト.

開発環境用のサンプルデータを投入する。

使用方法:
    python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import get_settings


async def seed_tenants(session: AsyncSession) -> dict[str, uuid.UUID]:
    """テナントデータを投入."""
    auditor_id = uuid.uuid4()
    auditee_id = uuid.uuid4()

    await session.execute(
        text(
            "INSERT INTO tenants (id, name, tenant_type, is_active) "
            "VALUES (:id, :name, :type, true) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(auditor_id), "name": "Sample Auditor Firm", "type": "auditor"},
    )
    await session.execute(
        text(
            "INSERT INTO tenants (id, name, tenant_type, is_active, parent_tenant_id) "
            "VALUES (:id, :name, :type, true, :parent) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(auditee_id),
            "name": "Sample Auditee Corp",
            "type": "auditee",
            "parent": str(auditor_id),
        },
    )

    print(f"[OK] Tenants: auditor={auditor_id}, auditee={auditee_id}")
    return {"auditor": auditor_id, "auditee": auditee_id}


async def seed_users(
    session: AsyncSession, tenants: dict[str, uuid.UUID]
) -> dict[str, uuid.UUID]:
    """ユーザーデータを投入."""
    # bcrypt hash of 'password123'
    password_hash = "$2b$12$LJ3m4ys3FnYqST/9KDZq7OQEVVGm9M7Q3Ks5h.G/2GvW3hPNGGJ2O"

    users = {
        "admin": {
            "tenant_id": str(tenants["auditor"]),
            "email": "admin@audit-firm.example.com",
            "full_name": "Admin User",
            "role": "admin",
            "department": "IT",
        },
        "auditor": {
            "tenant_id": str(tenants["auditor"]),
            "email": "auditor@audit-firm.example.com",
            "full_name": "Lead Auditor",
            "role": "auditor",
            "department": "Audit Division",
        },
        "auditee_mgr": {
            "tenant_id": str(tenants["auditee"]),
            "email": "manager@auditee-corp.example.com",
            "full_name": "Auditee Manager",
            "role": "auditee_manager",
            "department": "Finance",
        },
    }

    user_ids = {}
    for key, data in users.items():
        user_id = uuid.uuid4()
        user_ids[key] = user_id
        await session.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, hashed_password, role, department, is_active) "
                "VALUES (:id, :tenant_id, :email, :full_name, :password, :role, :department, true) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {
                "id": str(user_id),
                "password": password_hash,
                **data,
            },
        )

    print(f"[OK] Users: {len(users)} created")
    return user_ids


async def seed_project(
    session: AsyncSession,
    tenants: dict[str, uuid.UUID],
) -> uuid.UUID:
    """サンプル監査プロジェクトを投入."""
    project_id = uuid.uuid4()
    now = datetime.now(timezone.utc).isoformat()

    await session.execute(
        text(
            "INSERT INTO audit_projects "
            "(id, tenant_id, name, description, fiscal_year, status, "
            " auditor_tenant_id, auditee_tenant_id, start_date, end_date) "
            "VALUES (:id, :tenant_id, :name, :desc, :fy, :status, "
            " :auditor_id, :auditee_id, :start, :end) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(project_id),
            "tenant_id": str(tenants["auditor"]),
            "name": "FY2025 Financial Statement Audit",
            "desc": "年次財務諸表監査 - Sample Auditee Corp",
            "fy": 2025,
            "status": "planning",
            "auditor_id": str(tenants["auditor"]),
            "auditee_id": str(tenants["auditee"]),
            "start": "2025-04-01",
            "end": "2026-03-31",
        },
    )

    print(f"[OK] Audit project: {project_id}")
    return project_id


async def main() -> None:
    """メイン実行."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            print("=== Seeding Development Data ===")
            tenants = await seed_tenants(session)
            await seed_users(session, tenants)
            await seed_project(session, tenants)
            await session.commit()
            print("=== Seed Complete ===")
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Seed failed: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
