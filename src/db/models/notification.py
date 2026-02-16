"""通知モデル — 通知履歴・通知設定"""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import TenantBaseModel


class Notification(TenantBaseModel):
    """通知履歴

    Slack/Teams等のプロバイダ経由で送信された通知の履歴を管理。
    """

    __tablename__ = "notifications"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, critical
    source: Mapped[str] = mapped_column(String(100), default="")  # escalation, approval_request, risk_alert
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # slack, teams, email
    channel: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent, failed, pending
    action_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


class NotificationSetting(TenantBaseModel):
    """テナント通知設定

    テナント単位の通知チャンネル設定・有効/無効を管理。
    """

    __tablename__ = "notification_settings"

    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # slack, teams, email
    channel: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    min_priority: Mapped[str] = mapped_column(String(20), default="low")  # 最低通知優先度
    webhook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, default=dict)
