"""SQLAlchemy Base model + テナント分離Mixin"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """全モデルの基底クラス"""

    pass


class TimestampMixin:
    """作成日時・更新日時の共通Mixin"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class TenantMixin:
    """テナント分離Mixin — RLS対応

    全テナントスコープのテーブルに付与。
    PostgreSQL RLSポリシーと連携してテナント間データ分離を保証。
    """

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
    )


class BaseModel(Base, TimestampMixin):
    """UUID主キー + タイムスタンプを持つ標準基底モデル"""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("gen_random_uuid()"),
    )


class TenantBaseModel(BaseModel, TenantMixin):
    """テナントスコープの標準基底モデル"""

    __abstract__ = True


# ── RLS設定用SQL ──────────────────────────────────────
RLS_SETUP_SQL = """
-- テナント分離RLSポリシー（テーブルごとに実行）
-- ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_isolation ON {table_name}
--   USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
-- GRANT SELECT, INSERT, UPDATE, DELETE ON {table_name} TO audit_app_user;
"""
