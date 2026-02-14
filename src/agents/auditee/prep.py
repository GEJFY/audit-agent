"""Prep Agent — 監査準備自動化"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditeeState


class PrepAgent(BaseAuditAgent[AuditeeState]):
    """監査準備自動化Agent — 想定質問生成・事前証跡収集・セルフアセスメント"""

    @property
    def agent_name(self) -> str:
        return "auditee_prep"

    @property
    def agent_description(self) -> str:
        return "監査準備自動化 — 想定質問AI生成・事前証跡収集・セルフアセスメント"

    async def execute(self, state: AuditeeState) -> AuditeeState:
        """監査準備を実行"""
        logger.info("Prep Agent: 監査準備開始")

        # 想定質問を生成
        predicted = await self._predict_questions(state)
        state.predicted_questions = predicted

        # 準備チェックリスト生成
        checklist = await self._generate_checklist(state, predicted)
        state.prep_checklist = checklist

        state.current_phase = "preparing"
        state.current_agent = self.agent_name

        logger.info(f"Prep Agent: {len(predicted)}件の想定質問生成完了")
        return state

    async def _predict_questions(self, state: AuditeeState) -> list[str]:
        """過去の監査パターンから想定質問を生成"""
        prompt = f"""
部門: {state.department}
過去の監査対話: {json.dumps(state.metadata.get("past_audits", []), ensure_ascii=False, default=str)[:2000]}

この部門に対して内部監査で想定される質問を10件生成してください。
JSON配列形式で返してください。
"""
        response = await self.call_llm(prompt, use_fast_model=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return [response]

    async def _generate_checklist(
        self, state: AuditeeState, predicted_questions: list[str]
    ) -> dict[str, Any]:
        """準備チェックリスト生成"""
        return {
            "items": [
                {"task": f"質問「{q[:50]}...」への回答準備", "status": "pending"}
                for q in predicted_questions[:10]
            ],
            "completion_rate": 0.0,
        }
