"""LangGraph共通State定義 — 全エージェントのステートマシン基盤"""

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """Agent間メッセージ"""

    role: str  # system, human, ai, tool
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditorState(BaseModel):
    """監査側Agent共通State"""

    # プロジェクト情報
    project_id: str = ""
    tenant_id: str = ""
    agent_mode: str = "audit"  # audit, assist, autonomous

    # メッセージ履歴
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)

    # 現在のフェーズ
    current_phase: str = "init"  # init, planning, fieldwork, reporting, follow_up
    current_agent: str = ""

    # データコンテキスト
    risk_assessment: dict[str, Any] = Field(default_factory=dict)
    audit_plan: dict[str, Any] = Field(default_factory=dict)
    test_results: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] = Field(default_factory=dict)

    # 対話コンテキスト
    pending_questions: list[dict[str, Any]] = Field(default_factory=list)
    dialogue_history: list[dict[str, Any]] = Field(default_factory=list)

    # Human-in-the-Loop
    requires_approval: bool = False
    approval_context: dict[str, Any] = Field(default_factory=dict)

    # エラー・メタ
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditeeState(BaseModel):
    """被監査側Agent共通State"""

    # テナント情報
    tenant_id: str = ""
    department: str = ""

    # メッセージ履歴
    messages: Annotated[list[Any], add_messages] = Field(default_factory=list)

    # 現在のフェーズ
    current_phase: str = "idle"  # idle, responding, searching, preparing, monitoring
    current_agent: str = ""

    # 対話コンテキスト
    incoming_questions: list[dict[str, Any]] = Field(default_factory=list)
    drafted_responses: list[dict[str, Any]] = Field(default_factory=list)

    # 証跡管理
    evidence_search_results: list[dict[str, Any]] = Field(default_factory=list)
    evidence_queue: list[dict[str, Any]] = Field(default_factory=list)

    # リスク監視
    risk_alerts: list[dict[str, Any]] = Field(default_factory=list)
    controls_status: list[dict[str, Any]] = Field(default_factory=list)

    # 監査準備
    prep_checklist: dict[str, Any] = Field(default_factory=dict)
    predicted_questions: list[str] = Field(default_factory=list)

    # Human-in-the-Loop
    requires_approval: bool = False
    approval_context: dict[str, Any] = Field(default_factory=dict)

    # エラー・メタ
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
