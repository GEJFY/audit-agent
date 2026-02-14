"""Report Writer Agent — 監査報告書自動生成"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState
from src.llm_gateway.prompts.report import REPORT_GENERATION_PROMPT, SYSTEM_PROMPT


class ReportWriterAgent(BaseAuditAgent[AuditorState]):
    """報告書自動生成Agent — IIA基準準拠の監査報告書を生成"""

    @property
    def agent_name(self) -> str:
        return "auditor_report_writer"

    @property
    def agent_description(self) -> str:
        return "報告書自動生成 — 検出事項をIIA基準準拠の監査報告書に構造化"

    async def execute(self, state: AuditorState) -> AuditorState:
        """監査報告書を生成"""
        logger.info("Report Writer: 報告書生成開始")

        prompt = REPORT_GENERATION_PROMPT.format(
            project_info=json.dumps(
                {"project_id": state.project_id, "phase": state.current_phase},
                ensure_ascii=False,
            ),
            findings=json.dumps(state.findings, ensure_ascii=False, default=str),
            test_results=json.dumps(state.test_results, ensure_ascii=False, default=str),
        )

        response = await self.call_llm(prompt, system_prompt=SYSTEM_PROMPT)

        try:
            report = json.loads(response)
        except json.JSONDecodeError:
            report = {"raw_content": response, "confidence": 0.5}

        state.report = report
        state.requires_approval = True  # 報告書は常に人間承認必要
        state.approval_context = {
            "type": "report",
            "report": report,
            "reason": "監査報告書の最終承認",
        }

        confidence = report.get("confidence", 0.7)
        self.record_decision(
            tenant_id=state.tenant_id,
            decision="report_generated",
            reasoning=report.get("executive_summary", ""),
            confidence=confidence,
            resource_type="report",
            resource_id=state.project_id,
        )

        state.current_agent = self.agent_name
        logger.info("Report Writer: 報告書生成完了")
        return state
