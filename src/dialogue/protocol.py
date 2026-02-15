"""Dialogue Bus メッセージプロトコル — 構造化された対話スキーマ"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.config.constants import DialogueMessageType, EscalationReason


class Attachment(BaseModel):
    """メッセージ添付ファイル"""

    file_name: str
    file_type: str
    s3_path: str
    file_hash: str  # SHA-256
    file_size_bytes: int = 0


class DialogueMessageSchema(BaseModel):
    """Agent間対話メッセージの構造化スキーマ

    Auditor Agent ⇔ Auditee Agent間の全通信はこのスキーマに準拠。
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # 送受信
    from_tenant_id: UUID
    to_tenant_id: UUID
    from_agent: str
    to_agent: str | None = None

    # メッセージ内容
    message_type: DialogueMessageType
    subject: str | None = None
    content: str
    structured_content: dict[str, Any] = Field(default_factory=dict)

    # コンテキスト
    project_id: UUID | None = None
    parent_message_id: UUID | None = None  # 返信元
    thread_id: UUID | None = None  # スレッドID

    # 添付
    attachments: list[Attachment] = Field(default_factory=list)

    # 品質・信頼度
    confidence: float | None = None
    quality_score: float | None = None

    # 承認
    human_approved: bool | None = None  # None=未承認
    approved_by: UUID | None = None
    approved_at: datetime | None = None

    # エスカレーション
    is_escalated: bool = False
    escalation_reason: EscalationReason | None = None

    # メタ
    processing_time_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestionMessage(DialogueMessageSchema):
    """質問メッセージ — Auditor → Auditee"""

    message_type: DialogueMessageType = DialogueMessageType.QUESTION
    deadline: datetime | None = None
    priority: str = "medium"  # critical, high, medium, low


class AnswerMessage(DialogueMessageSchema):
    """回答メッセージ — Auditee → Auditor"""

    message_type: DialogueMessageType = DialogueMessageType.ANSWER
    referenced_documents: list[str] = Field(default_factory=list)
    is_reused: bool = False
    source_response_id: UUID | None = None


class EvidenceRequestMessage(DialogueMessageSchema):
    """証跡依頼メッセージ — Auditor → Auditee"""

    message_type: DialogueMessageType = DialogueMessageType.EVIDENCE_REQUEST
    evidence_description: str = ""
    accepted_formats: list[str] = Field(default_factory=lambda: ["pdf", "xlsx", "csv"])
    deadline: datetime | None = None


class EvidenceSubmitMessage(DialogueMessageSchema):
    """証跡提出メッセージ — Auditee → Auditor"""

    message_type: DialogueMessageType = DialogueMessageType.EVIDENCE_SUBMIT
    evidence_ids: list[UUID] = Field(default_factory=list)
    verification_status: str = "pending"  # pending, verified, rejected


class EscalationMessage(DialogueMessageSchema):
    """エスカレーションメッセージ — Agent → Human"""

    message_type: DialogueMessageType = DialogueMessageType.ESCALATION
    escalation_reason: EscalationReason = EscalationReason.HUMAN_REVIEW_REQUIRED
    urgency: str = "high"
    is_escalated: bool = True
