"""FollowUpAgent テスト"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.agents.auditor.follow_up import FollowUpAgent
from src.agents.state import AuditorState


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> FollowUpAgent:
    return FollowUpAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestFollowUpAgent:
    def test_agent_name(self, agent: FollowUpAgent) -> None:
        assert agent.agent_name == "auditor_follow_up"

    def test_agent_description(self, agent: FollowUpAgent) -> None:
        assert agent.agent_description != ""

    async def test_execute_no_findings(self, agent: FollowUpAgent) -> None:
        """検出事項なし"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert result.current_agent == "auditor_follow_up"
        assert "overdue_findings" not in result.metadata

    async def test_execute_all_remediated(self, agent: FollowUpAgent) -> None:
        """全て改善済み"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            findings=[
                {"id": "f1", "status": "remediated"},
                {"id": "f2", "status": "closed"},
            ],
        )
        result = await agent.execute(state)
        assert "overdue_findings" not in result.metadata

    async def test_execute_with_overdue(self, agent: FollowUpAgent) -> None:
        """未対応の検出事項あり"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            findings=[
                {"id": "f1", "status": "draft"},
                {"id": "f2", "status": "remediated"},
                {"id": "f3", "status": "pending"},
            ],
        )
        result = await agent.execute(state)
        assert len(result.metadata["overdue_findings"]) == 2

    async def test_execute_all_overdue(self, agent: FollowUpAgent) -> None:
        """全て未対応"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            findings=[
                {"id": "f1", "status": "draft"},
                {"id": "f2", "status": "pending"},
            ],
        )
        result = await agent.execute(state)
        assert len(result.metadata["overdue_findings"]) == 2
