"""監査側Orchestrator — 監査ワークフロー全体を統括指揮"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState


class AuditorOrchestrator(BaseAuditAgent[AuditorState]):
    """監査側Orchestrator Agent

    監査プロジェクトのライフサイクル全体を管理。
    各フェーズに応じて適切なAgentへタスクをルーティング。
    """

    @property
    def agent_name(self) -> str:
        return "auditor_orchestrator"

    @property
    def agent_description(self) -> str:
        return "監査ワークフロー統括 — フェーズ遷移・タスクルーティング・状態管理"

    async def execute(self, state: AuditorState) -> AuditorState:
        """フェーズに応じた次のアクションを決定"""
        current_phase = state.current_phase
        logger.info(f"Orchestrator: 現在フェーズ = {current_phase}")

        # フェーズ遷移ロジック
        next_phase = await self._determine_next_phase(state)

        if next_phase != current_phase:
            logger.info(f"フェーズ遷移: {current_phase} → {next_phase}")
            state.current_phase = next_phase

        state.current_agent = self.agent_name
        return state

    async def _determine_next_phase(self, state: AuditorState) -> str:
        """次フェーズを決定"""
        phase = state.current_phase

        if phase == "init":
            return "planning"
        elif phase == "planning" and state.audit_plan:
            return "fieldwork"
        elif phase == "fieldwork" and state.test_results:
            # テスト結果と異常検知が完了していれば報告フェーズへ
            if state.findings:
                return "reporting"
        elif phase == "reporting" and state.report:
            return "follow_up"

        return phase

    def route_to_agent(self, state: AuditorState) -> str:
        """現在のフェーズに応じてルーティング先Agentを返す"""
        routing: dict[str, str] = {
            "init": "auditor_orchestrator",
            "planning": "auditor_planner",
            "fieldwork": "auditor_controls_tester",
            "reporting": "auditor_report_writer",
            "follow_up": "auditor_follow_up",
        }
        return routing.get(state.current_phase, "auditor_orchestrator")
