"""エージェントスキーマ"""

from typing import Any

from pydantic import BaseModel


class AgentInfo(BaseModel):
    name: str
    description: str


class AgentListResponse(BaseModel):
    agents: list[dict[str, str]]


class AgentExecuteRequest(BaseModel):
    agent_name: str
    project_id: str | None = None
    parameters: dict[str, Any] | None = None


class AgentExecuteResponse(BaseModel):
    agent_name: str
    status: str
    message: str
    execution_id: str | None = None
    result: dict[str, Any] | None = None


class AgentDecisionResponse(BaseModel):
    id: str
    agent_type: str
    decision_type: str
    reasoning: str | None = None
    confidence: float
    model_used: str
    human_approved: bool | None = None
    project_id: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class AgentDecisionListResponse(BaseModel):
    decisions: list[AgentDecisionResponse]
    total: int


class ApprovalQueueItem(BaseModel):
    id: str
    decision_id: str
    approval_type: str
    priority: str
    status: str
    requested_by_agent: str
    context: dict[str, Any] | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class ApprovalActionRequest(BaseModel):
    action: str  # approved, rejected, deferred
    comment: str | None = None
