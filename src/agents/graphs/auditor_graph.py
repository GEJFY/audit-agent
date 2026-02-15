"""監査側 StateGraph — Auditor エージェント連携グラフ

フェーズ遷移:
  START → orchestrator → planner → [approval] → fieldwork → reporter → [approval] → follow_up → END

fieldwork は内部で data_collector → controls_tester → anomaly_detective を順次実行。
requires_approval=True の場合は human_approval ノードで中断。
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from loguru import logger

from src.agents.state import AuditorState


def _orchestrator_node(state: AuditorState) -> dict[str, Any]:
    """Orchestrator — フェーズ遷移判定"""
    current = state.current_phase

    if current == "init":
        next_phase = "planning"
    elif current == "planning" and state.audit_plan:
        next_phase = "fieldwork"
    elif current == "fieldwork" and state.findings:
        next_phase = "reporting"
    elif current == "reporting" and state.report:
        next_phase = "follow_up"
    else:
        next_phase = current

    if next_phase != current:
        logger.info(f"フェーズ遷移: {current} → {next_phase}")

    return {
        "current_phase": next_phase,
        "current_agent": "auditor_orchestrator",
    }


async def _planner_node(state: AuditorState) -> dict[str, Any]:
    """Planner — リスク評価・監査計画策定"""
    from src.agents.auditor.planner import PlannerAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = PlannerAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "risk_assessment": updated.risk_assessment,
        "audit_plan": updated.audit_plan,
        "requires_approval": updated.requires_approval,
        "approval_context": updated.approval_context,
        "current_agent": "auditor_planner",
        "current_phase": "planning",
    }


async def _data_collector_node(state: AuditorState) -> dict[str, Any]:
    """DataCollector — データ収集"""
    from src.agents.auditor.data_collector import DataCollectorAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = DataCollectorAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "metadata": updated.metadata,
        "current_agent": "auditor_data_collector",
    }


async def _controls_tester_node(state: AuditorState) -> dict[str, Any]:
    """ControlsTester — 統制テスト実行"""
    from src.agents.auditor.controls_tester import ControlsTesterAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = ControlsTesterAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "test_results": updated.test_results,
        "current_agent": "auditor_controls_tester",
    }


async def _anomaly_detective_node(state: AuditorState) -> dict[str, Any]:
    """AnomalyDetective — 異常検知"""
    from src.agents.auditor.anomaly_detective import AnomalyDetectiveAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = AnomalyDetectiveAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "anomalies": updated.anomalies,
        "findings": updated.findings,
        "current_agent": "auditor_anomaly_detective",
    }


async def _knowledge_node(state: AuditorState) -> dict[str, Any]:
    """Knowledge — RAGベース知識検索"""
    from src.agents.auditor.knowledge import KnowledgeAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = KnowledgeAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "dialogue_history": updated.dialogue_history,
        "pending_questions": updated.pending_questions,
        "current_agent": "auditor_knowledge",
    }


async def _report_writer_node(state: AuditorState) -> dict[str, Any]:
    """ReportWriter — 報告書生成"""
    from src.agents.auditor.report_writer import ReportWriterAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = ReportWriterAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "report": updated.report,
        "requires_approval": True,  # 報告書は常に承認必要
        "approval_context": updated.approval_context,
        "current_agent": "auditor_report_writer",
        "current_phase": "reporting",
    }


async def _follow_up_node(state: AuditorState) -> dict[str, Any]:
    """FollowUp — 改善措置追跡"""
    from src.agents.auditor.follow_up import FollowUpAgent
    from src.llm_gateway.gateway import LLMGateway

    agent = FollowUpAgent(llm_gateway=LLMGateway())
    updated = await agent.execute(state)
    return {
        "metadata": updated.metadata,
        "current_agent": "auditor_follow_up",
        "current_phase": "follow_up",
    }


def _human_approval_node(state: AuditorState) -> dict[str, Any]:
    """Human-in-the-Loop 承認ゲート（中断ポイント）

    LangGraph の interrupt_before で呼び出し側が中断を制御。
    承認済みの場合は requires_approval を False に戻して続行。
    """
    logger.info("Human-in-the-Loop: 承認待ち")
    return {"requires_approval": False}


# ── 条件分岐関数 ────────────────────────────────────


def _route_after_planner(state: AuditorState) -> str:
    """Planner 後の分岐 — 承認必要ならゲート、そうでなければ fieldwork"""
    if state.requires_approval:
        return "human_approval_plan"
    return "data_collector"


def _route_after_plan_approval(state: AuditorState) -> str:
    """計画承認後 → fieldwork へ"""
    return "data_collector"


def _route_after_anomaly(state: AuditorState) -> str:
    """異常検知後 — 質問があれば knowledge、なければ reporting"""
    if state.pending_questions:
        return "knowledge"
    return "report_writer"


def _route_after_reporter(state: AuditorState) -> str:
    """報告書生成後 — 常に承認ゲート"""
    if state.requires_approval:
        return "human_approval_report"
    return "follow_up"


def _route_after_report_approval(state: AuditorState) -> str:
    """報告書承認後 → follow_up へ"""
    return "follow_up"


def build_auditor_graph() -> StateGraph:
    """監査側 StateGraph を構築

    Returns:
        コンパイル済み StateGraph
    """
    graph = StateGraph(AuditorState)

    # ノード追加
    graph.add_node("orchestrator", _orchestrator_node)
    graph.add_node("planner", _planner_node)
    graph.add_node("human_approval_plan", _human_approval_node)
    graph.add_node("data_collector", _data_collector_node)
    graph.add_node("controls_tester", _controls_tester_node)
    graph.add_node("anomaly_detective", _anomaly_detective_node)
    graph.add_node("knowledge", _knowledge_node)
    graph.add_node("report_writer", _report_writer_node)
    graph.add_node("human_approval_report", _human_approval_node)
    graph.add_node("follow_up", _follow_up_node)

    # エッジ定義
    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "planner")

    # Planner → 条件分岐（承認ゲート or fieldwork）
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {
            "human_approval_plan": "human_approval_plan",
            "data_collector": "data_collector",
        },
    )

    # 計画承認後 → fieldwork
    graph.add_conditional_edges(
        "human_approval_plan",
        _route_after_plan_approval,
        {"data_collector": "data_collector"},
    )

    # Fieldwork: data_collector → controls_tester → anomaly_detective
    graph.add_edge("data_collector", "controls_tester")
    graph.add_edge("controls_tester", "anomaly_detective")

    # 異常検知後 → 条件分岐（knowledge or report_writer）
    graph.add_conditional_edges(
        "anomaly_detective",
        _route_after_anomaly,
        {
            "knowledge": "knowledge",
            "report_writer": "report_writer",
        },
    )

    # Knowledge → report_writer
    graph.add_edge("knowledge", "report_writer")

    # ReportWriter → 条件分岐（承認ゲート or follow_up）
    graph.add_conditional_edges(
        "report_writer",
        _route_after_reporter,
        {
            "human_approval_report": "human_approval_report",
            "follow_up": "follow_up",
        },
    )

    # 報告書承認後 → follow_up
    graph.add_conditional_edges(
        "human_approval_report",
        _route_after_report_approval,
        {"follow_up": "follow_up"},
    )

    # follow_up → END
    graph.add_edge("follow_up", END)

    return graph


def compile_auditor_graph(**kwargs: Any) -> Any:
    """コンパイル済みグラフを返す

    Args:
        **kwargs: compile() に渡すオプション（interrupt_before等）
    """
    graph = build_auditor_graph()
    return graph.compile(**kwargs)
