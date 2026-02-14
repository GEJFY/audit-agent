"""テナント・ユーザーモデル"""

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import BaseModel, TenantBaseModel


class Tenant(BaseModel):
    """テナント — 監査部門 or 被監査部門"""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_type: Mapped[str] = mapped_column(String(20), nullable=False)  # auditor / auditee
    parent_tenant_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tenants.id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # リレーション
    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(TenantBaseModel):
    """ユーザー"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # UserRole enum
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # リレーション
    tenant: Mapped["Tenant"] = relationship(
        back_populates="users",
        foreign_keys=[TenantBaseModel.tenant_id],
        primaryjoin="User.tenant_id == Tenant.id",
    )
