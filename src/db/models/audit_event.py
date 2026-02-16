"""監査イベントモデル — 操作ログ・監査証跡"""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import TenantBaseModel


class AuditEvent(TenantBaseModel):
    """監査イベント（操作ログ）

    システム内の全操作を記録する監査証跡テーブル。
    誰が・いつ・何を・どのリソースに対して行ったかを追跡。
    """

    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # create, update, delete, login, export, approve, reject
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)  # project, finding, report, evidence, user
    resource_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)  # 操作者
    actor_type: Mapped[str] = mapped_column(String(50), default="user")  # user, agent, system
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
