"""対話メッセージモデル — Auditor ⇔ Auditee間対話記録"""

from typing import Any

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import BaseModel, TimestampMixin


class DialogueMessage(BaseModel, TimestampMixin):
    """Agent間対話メッセージ — 両テナントから参照可能

    Dialogue Busの全メッセージをAppend-Onlyで記録。
    tenant_idではなくfrom/toで方向を管理。
    """

    __tablename__ = "dialogue_messages"

    # 送信元・送信先
    from_tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    to_tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    from_agent: Mapped[str] = mapped_column(String(100), nullable=False)  # Agent種別
    to_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # メッセージ内容
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # DialogueMessageType
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)

    # 関連情報
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    parent_message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)  # スレッド化
    thread_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    # 添付・証跡
    attachments: Mapped[list[Any] | None] = mapped_column(JSONB, default=list)  # [{file_name, s3_path, file_hash}]
    evidence_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # 品質・信頼度
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # Agent信頼度(0-1)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 回答品質評価

    # 承認
    human_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # メタデータ
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, default=dict)
