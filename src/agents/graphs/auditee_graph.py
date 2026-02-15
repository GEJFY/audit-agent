"""被監査側 StateGraph — Auditee エージェント連携グラフ

ワークフロー:
  START → orchestrator → [response | evidence_search | prep] → [approval] → END

監視フロー:
  START → controls_monitor → risk_alert → END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from loguru import logger

from src.agents.state import AuditeeState


def _orchestrator_node(state: AuditeeState) -> dict[str, Any]:
    """Orchestrator — 質問ルーティング判定"""
    incoming = state.incoming_questions

    if not incoming:
        return {
            "current_phase": "idle",
            "current_agent": "auditee_orchestrator",
        }

    # 質問タイプ判定（最初の質問で判断）
    q_type = incoming[0].get("type", "general") if incoming else "general"

    phase_map = {
        "evidence_request": "searching",
        "question": "responding",
        "preparation": "preparing",
        "general": "responding",
    }

    return {
        "current_phase": phase_map.get(q_type, "responding"),
        "current_agent": "auditee_orchestrator",
    }


async def _response_node(state: AuditeeState) -> dict[str, Any]:
    """Response — 回答ドラフト生成"""
    from src.agents.auditee.response import ResponseAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = ResponseAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "drafted_responses": updated.drafted_responses,
        "evidence_queue": updated.evidence_queue,
        "requires_approval": updated.requires_approval,
        "approval_context": updated.approval_context,
        "current_agent": "auditee_response",
    }


async def _evidence_search_node(state: AuditeeState) -> dict[str, Any]:
    """EvidenceSearch — 証跡検索"""
    from src.agents.auditee.evidence_search import EvidenceSearchAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = EvidenceSearchAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "evidence_search_results": updated.evidence_search_results,
        "current_agent": "auditee_evidence_search",
    }


async def _prep_node(state: AuditeeState) -> dict[str, Any]:
    """Prep — 監査準備"""
    from src.agents.auditee.prep import PrepAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = PrepAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "prep_checklist": updated.prep_checklist,
        "predicted_questions": updated.predicted_questions,
        "current_agent": "auditee_prep",
    }


async def _controls_monitor_node(state: AuditeeState) -> dict[str, Any]:
    """ControlsMonitor — 統制監視"""
    from src.agents.auditee.controls_monitor import ControlsMonitorAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = ControlsMonitorAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "controls_status": updated.controls_status,
        "current_agent": "auditee_controls_monitor",
        "current_phase": "monitoring",
    }


async def _risk_alert_node(state: AuditeeState) -> dict[str, Any]:
    """RiskAlert — リスクアラート検知"""
    from src.agents.auditee.risk_alert import RiskAlertAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = RiskAlertAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "risk_alerts": updated.risk_alerts,
        "current_agent": "auditee_risk_alert",
    }


def _human_approval_node(state: AuditeeState) -> dict[str, Any]:
    """Human-in-the-Loop 承認ゲート"""
    logger.info("Auditee: 回答承認待ち")
    return {"requires_approval": False}


# ── 条件分岐関数 ────────────────────────────────────


def _route_after_orchestrator(state: AuditeeState) -> str:
    """Orchestrator 後の分岐 — フェーズに応じてルーティング"""
    route_map = {
        "idle": "end",
        "searching": "evidence_search",
        "preparing": "prep",
    }
    return route_map.get(state.current_phase, "response")


def _route_after_response(state: AuditeeState) -> str:
    """回答生成後 — 証跡キューがあれば検索、承認必要なら承認ゲート"""
    if state.evidence_queue:
        return "evidence_search"
    if state.requires_approval:
        return "human_approval"
    return "end"


def _route_after_evidence(state: AuditeeState) -> str:
    """証跡検索後 — 承認必要なら承認ゲート"""
    if state.requires_approval:
        return "human_approval"
    return "end"


def _route_after_prep(state: AuditeeState) -> str:
    """準備完了後 → END"""
    return "end"


def build_auditee_response_graph() -> StateGraph:
    """被監査側レスポンス StateGraph を構築

    質問受付 → 回答生成/証跡検索/準備 → 承認 → 完了
    """
    graph = StateGraph(AuditeeState)

    # ノード追加
    graph.add_node("orchestrator", _orchestrator_node)
    graph.add_node("response", _response_node)
    graph.add_node("evidence_search", _evidence_search_node)
    graph.add_node("prep", _prep_node)
    graph.add_node("human_approval", _human_approval_node)

    # エッジ定義
    graph.add_edge(START, "orchestrator")

    # Orchestrator → 条件分岐
    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "response": "response",
            "evidence_search": "evidence_search",
            "prep": "prep",
            "end": END,
        },
    )

    # Response → 条件分岐（evidence_search or approval or end）
    graph.add_conditional_edges(
        "response",
        _route_after_response,
        {
            "evidence_search": "evidence_search",
            "human_approval": "human_approval",
            "end": END,
        },
    )

    # EvidenceSearch → 条件分岐（approval or end）
    graph.add_conditional_edges(
        "evidence_search",
        _route_after_evidence,
        {
            "human_approval": "human_approval",
            "end": END,
        },
    )

    # Prep → end
    graph.add_conditional_edges(
        "prep",
        _route_after_prep,
        {"end": END},
    )

    # Approval → END
    graph.add_edge("human_approval", END)

    return graph


def build_auditee_monitoring_graph() -> StateGraph:
    """被監査側監視 StateGraph を構築

    統制監視 → リスクアラート → 完了
    """
    graph = StateGraph(AuditeeState)

    graph.add_node("controls_monitor", _controls_monitor_node)
    graph.add_node("risk_alert", _risk_alert_node)

    graph.add_edge(START, "controls_monitor")
    graph.add_edge("controls_monitor", "risk_alert")
    graph.add_edge("risk_alert", END)

    return graph


def compile_auditee_response_graph(**kwargs: Any) -> Any:
    """コンパイル済みレスポンスグラフを返す"""
    graph = build_auditee_response_graph()
    return graph.compile(**kwargs)


def compile_auditee_monitoring_graph(**kwargs: Any) -> Any:
    """コンパイル済み監視グラフを返す"""
    graph = build_auditee_monitoring_graph()
    return graph.compile(**kwargs)
