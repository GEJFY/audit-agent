"""被監査側Orchestrator — 被監査側ワークフロー統括"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditeeState


class AuditeeOrchestrator(BaseAuditAgent[AuditeeState]):
    """被監査側Orchestrator — 監査チームからのリクエスト受付・調整"""

    @property
    def agent_name(self) -> str:
        return "auditee_orchestrator"

    @property
    def agent_description(self) -> str:
        return "被監査側統括 — リクエスト受付・部門調整・回答期限管理・品質チェック・承認フロー"

    async def execute(self, state: AuditeeState) -> AuditeeState:
        """受信した質問を解析してAgentにルーティング"""
        logger.info("Auditee Orchestrator: リクエスト処理開始")

        incoming = state.incoming_questions

        for question in incoming:
            # 質問タイプに応じてルーティング
            routing = self._determine_routing(question)
            logger.info(f"質問ルーティング: {routing}")

        state.current_phase = "responding" if incoming else "idle"
        state.current_agent = self.agent_name
        return state

    def _determine_routing(self, question: dict[str, Any]) -> str:
        """質問の種類に応じてルーティング先を決定"""
        q_type = question.get("type", "general")

        routing_map: dict[str, str] = {
            "evidence_request": "auditee_evidence_search",
            "question": "auditee_response",
            "preparation": "auditee_prep",
            "general": "auditee_response",
        }

        return routing_map.get(q_type, "auditee_response")
