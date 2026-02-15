"""対話スキーマ"""

from typing import Any

from pydantic import BaseModel


class DialogueSendRequest(BaseModel):
    to_tenant_id: str
    to_agent: str | None = None
    message_type: str  # question, answer, evidence_request, evidence_submit, escalation
    content: str
    subject: str | None = None
    project_id: str | None = None
    parent_message_id: str | None = None
    attachments: list[dict[str, str]] | None = None


class DialogueMessageResponse(BaseModel):
    id: str
    status: str
    message: str


class DialogueMessageDetail(BaseModel):
    id: str
    from_tenant_id: str
    to_tenant_id: str
    from_agent: str
    to_agent: str | None = None
    message_type: str
    subject: str | None = None
    content: str
    project_id: str | None = None
    thread_id: str | None = None
    confidence: float | None = None
    quality_score: float | None = None
    human_approved: bool | None = None
    is_escalated: bool = False
    escalation_reason: str | None = None
    attachments: list[dict[str, Any]] | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class DialogueListResponse(BaseModel):
    messages: list[DialogueMessageDetail]
    total: int


class DialogueApproveRequest(BaseModel):
    approved: bool = True
    comment: str | None = None


class ThreadResponse(BaseModel):
    thread_id: str
    messages: list[DialogueMessageDetail]
    total: int
