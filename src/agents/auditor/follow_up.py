"""Follow-up Agent — 改善措置追跡"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState


class FollowUpAgent(BaseAuditAgent[AuditorState]):
    """改善追跡Agent — 是正措置の期限管理・進捗確認"""

    @property
    def agent_name(self) -> str:
        return "auditor_follow_up"

    @property
    def agent_description(self) -> str:
        return "改善追跡 — 是正措置の期限管理・進捗確認・リマインダー"

    async def execute(self, state: AuditorState) -> AuditorState:
        """改善措置の追跡状況を確認"""
        logger.info("Follow-up: 改善追跡開始")

        findings = state.findings
        overdue: list[dict[str, Any]] = []

        for finding in findings:
            status = finding.get("status", "draft")
            if status not in ("remediated", "closed"):
                overdue.append(finding)

        if overdue:
            logger.warning(f"未対応の検出事項: {len(overdue)}件")
            state.metadata["overdue_findings"] = overdue

        state.current_agent = self.agent_name
        return state
