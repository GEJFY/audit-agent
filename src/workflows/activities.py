"""Temporal Activities — Agent実行をActivity関数として定義"""

from dataclasses import dataclass
from typing import Any

from loguru import logger
from temporalio import activity

from src.agents.registry import AgentRegistry
from src.agents.state import AuditeeState, AuditorState
from src.llm_gateway.gateway import LLMGateway


@dataclass
class AgentActivityInput:
    """Activity共通入力"""

    agent_name: str
    state_dict: dict[str, Any]
    tenant_id: str


@dataclass
class AgentActivityOutput:
    """Activity共通出力"""

    updated_state: dict[str, Any]
    success: bool
    error: str | None = None


def _get_or_create_agent(agent_name: str) -> Any:
    """Agentをレジストリから取得。未登録なら動的にインスタンス化"""
    registry = AgentRegistry.get_instance()
    if registry.has(agent_name):
        return registry.get(agent_name)

    # 動的インポート・登録
    gateway = LLMGateway()
    agent_class_map: dict[str, tuple[str, str]] = {
        "auditor_orchestrator": ("src.agents.auditor.orchestrator", "AuditorOrchestrator"),
        "auditor_planner": ("src.agents.auditor.planner", "PlannerAgent"),
        "auditor_data_collector": ("src.agents.auditor.data_collector", "DataCollectorAgent"),
        "auditor_controls_tester": ("src.agents.auditor.controls_tester", "ControlsTesterAgent"),
        "auditor_anomaly_detective": ("src.agents.auditor.anomaly_detective", "AnomalyDetectiveAgent"),
        "auditor_report_writer": ("src.agents.auditor.report_writer", "ReportWriterAgent"),
        "auditor_follow_up": ("src.agents.auditor.follow_up", "FollowUpAgent"),
        "auditor_knowledge": ("src.agents.auditor.knowledge", "KnowledgeAgent"),
        "auditee_orchestrator": ("src.agents.auditee.orchestrator", "AuditeeOrchestrator"),
        "auditee_response": ("src.agents.auditee.response", "ResponseAgent"),
        "auditee_evidence_search": ("src.agents.auditee.evidence_search", "EvidenceSearchAgent"),
        "auditee_prep": ("src.agents.auditee.prep", "PrepAgent"),
        "auditee_risk_alert": ("src.agents.auditee.risk_alert", "RiskAlertAgent"),
        "auditee_controls_monitor": ("src.agents.auditee.controls_monitor", "ControlsMonitorAgent"),
    }

    mapping = agent_class_map.get(agent_name)
    if not mapping:
        raise ValueError(f"Unknown agent: {agent_name}")

    import importlib

    module = importlib.import_module(mapping[0])
    cls = getattr(module, mapping[1])
    agent = cls(llm_gateway=gateway)
    registry.register(agent)
    return agent


# ── Auditor側 Activities ──────────────────────────────


@activity.defn(name="run_auditor_agent")
async def run_auditor_agent(activity_input: AgentActivityInput) -> AgentActivityOutput:
    """監査側Agent実行Activity"""
    logger.info("Activity実行: agent={}, tenant={}", activity_input.agent_name, activity_input.tenant_id)
    try:
        agent = _get_or_create_agent(activity_input.agent_name)
        state = AuditorState(**activity_input.state_dict)

        updated_state = await agent.run(state)

        return AgentActivityOutput(
            updated_state=updated_state.model_dump(),
            success=True,
        )
    except Exception as e:
        logger.error("Activity失敗: agent={}, error={}", activity_input.agent_name, str(e))
        return AgentActivityOutput(
            updated_state=activity_input.state_dict,
            success=False,
            error=str(e),
        )


@activity.defn(name="run_auditee_agent")
async def run_auditee_agent(activity_input: AgentActivityInput) -> AgentActivityOutput:
    """被監査側Agent実行Activity"""
    logger.info("Activity実行: agent={}, tenant={}", activity_input.agent_name, activity_input.tenant_id)
    try:
        agent = _get_or_create_agent(activity_input.agent_name)
        state = AuditeeState(**activity_input.state_dict)

        updated_state = await agent.run(state)

        return AgentActivityOutput(
            updated_state=updated_state.model_dump(),
            success=True,
        )
    except Exception as e:
        logger.error("Activity失敗: agent={}, error={}", activity_input.agent_name, str(e))
        return AgentActivityOutput(
            updated_state=activity_input.state_dict,
            success=False,
            error=str(e),
        )


@activity.defn(name="send_notification")
async def send_notification(tenant_id: str, message: str, channel: str = "slack") -> bool:
    """通知送信Activity（Slack, Email等）"""
    logger.info("通知送信: tenant={}, channel={}", tenant_id, channel)
    # Phase 1+で実装: Slack API, SendGrid等
    return True


@activity.defn(name="check_approval_status")
async def check_approval_status(tenant_id: str, decision_id: str) -> dict[str, Any]:
    """承認ステータス確認Activity"""
    from sqlalchemy import select

    from src.db.models.auditor import ApprovalQueue
    from src.db.session import get_session

    try:
        async for session in get_session():
            result = await session.execute(
                select(ApprovalQueue).where(  # type: ignore[call-arg]
                    ApprovalQueue.tenant_id == tenant_id,
                    ApprovalQueue.decision_id == decision_id,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                return {
                    "status": row.status,
                    "resolved_at": row.resolved_at,
                    "comment": row.resolution_comment,
                }
    except Exception as e:
        logger.error("承認ステータス確認エラー: {}", str(e))

    return {"status": "pending", "resolved_at": None, "comment": None}
