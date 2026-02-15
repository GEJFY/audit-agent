"""Planner Agent — リスク評価・監査計画策定"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState


class PlannerAgent(BaseAuditAgent[AuditorState]):
    """リスク評価と監査計画を策定するAgent"""

    @property
    def agent_name(self) -> str:
        return "auditor_planner"

    @property
    def agent_description(self) -> str:
        return "リスク評価・監査計画策定 — リスクユニバースの評価とテスト計画の生成"

    async def execute(self, state: AuditorState) -> AuditorState:
        """リスク評価 → 監査計画生成"""
        logger.info("Planner: 監査計画策定開始")

        # リスク評価
        risk_assessment = await self._assess_risks(state)
        state.risk_assessment = risk_assessment

        # 監査計画生成
        audit_plan = await self._generate_plan(state, risk_assessment)
        state.audit_plan = audit_plan

        # 信頼度チェック
        confidence = audit_plan.get("confidence", 0.0)
        if self.should_escalate(confidence):
            state.requires_approval = True
            state.approval_context = {
                "type": "audit_plan",
                "plan": audit_plan,
                "reason": "計画の信頼度が閾値を下回っています",
            }

        self.record_decision(
            tenant_id=state.tenant_id,
            decision="audit_plan_generated",
            reasoning=audit_plan.get("methodology", ""),
            confidence=confidence,
            resource_type="audit_plan",
            resource_id=state.project_id,
        )

        state.current_agent = self.agent_name
        return state

    async def _assess_risks(self, state: AuditorState) -> dict[str, Any]:
        """リスク評価を実行"""
        prompt = f"""
以下の監査プロジェクト情報に基づいてリスク評価を実施してください。

プロジェクトID: {state.project_id}
既存リスク情報: {json.dumps(state.risk_assessment, ensure_ascii=False, default=str)}

JSON形式で以下を含むリスク評価結果を返してください:
- high_risk_areas: 高リスク領域のリスト
- risk_scores: 各リスクのスコア
- recommended_focus: 推奨される監査重点領域
"""
        response = await self.call_llm(prompt, system_prompt="あなたは内部監査のリスク評価専門AIです。")

        try:
            return json.loads(response)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {"raw_assessment": response, "confidence": 0.5}

    async def _generate_plan(self, state: AuditorState, risk_assessment: dict[str, Any]) -> dict[str, Any]:
        """監査計画を生成"""
        prompt = f"""
以下のリスク評価結果に基づいて監査計画を策定してください。

リスク評価: {json.dumps(risk_assessment, ensure_ascii=False, default=str)}

JSON形式で以下を含む監査計画を返してください:
- scope: 監査範囲
- objectives: 監査目的リスト
- methodology: 監査手法
- test_procedures: テスト手続リスト
- resource_allocation: リソース配分
- timeline: スケジュール
- confidence: 計画の信頼度(0-1)
"""
        response = await self.call_llm(
            prompt, system_prompt="あなたは内部監査計画の専門AIです。J-SOX要件を考慮してください。"
        )

        try:
            return json.loads(response)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {"raw_plan": response, "confidence": 0.5}
