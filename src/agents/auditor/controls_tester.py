"""Controls Tester Agent — 統制テスト実行"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState


class ControlsTesterAgent(BaseAuditAgent[AuditorState]):
    """統制テスト実行Agent — RCMに基づくテストの自動実行"""

    @property
    def agent_name(self) -> str:
        return "auditor_controls_tester"

    @property
    def agent_description(self) -> str:
        return "統制テスト実行 — サンプリング・テスト実施・例外検出・結果評価"

    async def execute(self, state: AuditorState) -> AuditorState:
        """統制テストを実行"""
        logger.info("Controls Tester: テスト実行開始")

        plan = state.audit_plan
        test_procedures = plan.get("test_procedures", [])

        results: list[dict[str, Any]] = []
        for procedure in test_procedures:
            result = await self._execute_test(procedure, state)
            results.append(result)

        state.test_results = results

        # テスト結果の要約をLLMで生成
        summary = await self._summarize_results(results)
        state.metadata["test_summary"] = summary

        state.current_agent = self.agent_name
        logger.info(f"Controls Tester: {len(results)}件のテスト完了")
        return state

    async def _execute_test(
        self, procedure: dict[str, Any] | str, state: AuditorState
    ) -> dict[str, Any]:
        """個別テスト実行"""
        prompt = f"""
以下の統制テスト手続を実行し、結果を評価してください。

テスト手続: {json.dumps(procedure, ensure_ascii=False, default=str)}

JSON形式で結果を返してください:
{{
    "procedure": "テスト手続名",
    "result": "effective|ineffective|partially_effective|not_tested",
    "sample_tested": 25,
    "exceptions_found": 0,
    "details": "テスト詳細",
    "confidence": 0.0-1.0
}}
"""
        response = await self.call_llm(prompt)
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "procedure": str(procedure),
                "result": "not_tested",
                "confidence": 0.3,
                "details": response,
            }

        confidence = result.get("confidence", 0.5)
        self.record_decision(
            tenant_id=state.tenant_id,
            decision=f"test_result_{result.get('result', 'unknown')}",
            reasoning=result.get("details", ""),
            confidence=confidence,
            resource_type="test_result",
            resource_id=state.project_id,
        )

        return result

    async def _summarize_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """テスト結果サマリー"""
        total = len(results)
        effective = sum(1 for r in results if r.get("result") == "effective")
        return {
            "total_tests": total,
            "effective": effective,
            "ineffective": total - effective,
            "overall_assessment": "satisfactory" if effective / max(total, 1) > 0.8 else "needs_improvement",
        }
