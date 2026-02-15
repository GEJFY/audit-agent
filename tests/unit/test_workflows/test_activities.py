"""Temporal Activities テスト"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("temporalio")

from src.workflows.activities import (
    AgentActivityInput,
    AgentActivityOutput,
    _get_or_create_agent,
)


@pytest.mark.unit
class TestAgentActivityInput:
    """Activity入力のテスト"""

    def test_create(self) -> None:
        inp = AgentActivityInput(
            agent_name="auditor_planner",
            state_dict={"project_id": "p-001", "tenant_id": "t-001"},
            tenant_id="t-001",
        )
        assert inp.agent_name == "auditor_planner"
        assert inp.tenant_id == "t-001"


@pytest.mark.unit
class TestAgentActivityOutput:
    """Activity出力のテスト"""

    def test_success(self) -> None:
        out = AgentActivityOutput(
            updated_state={"project_id": "p-001"},
            success=True,
        )
        assert out.success is True
        assert out.error is None

    def test_failure(self) -> None:
        out = AgentActivityOutput(
            updated_state={},
            success=False,
            error="Agent実行エラー",
        )
        assert out.success is False
        assert out.error == "Agent実行エラー"


@pytest.mark.unit
class TestGetOrCreateAgent:
    """Agent動的取得のテスト"""

    def test_unknown_agent_raises(self) -> None:
        """未知のAgent名でValueError"""
        with pytest.raises(ValueError, match="Unknown agent"):
            _get_or_create_agent("nonexistent_agent")

    def test_get_from_registry(self, mock_llm_gateway: MagicMock) -> None:
        """レジストリにあればそこから取得"""
        from src.agents.base import BaseAuditAgent
        from src.agents.registry import AgentRegistry
        from src.agents.state import AuditorState

        class FakeAgent(BaseAuditAgent[AuditorState]):
            @property
            def agent_name(self) -> str:
                return "auditor_planner"

            @property
            def agent_description(self) -> str:
                return "fake"

            async def execute(self, state: AuditorState) -> AuditorState:
                return state

        registry = AgentRegistry.get_instance()
        fake = FakeAgent(llm_gateway=mock_llm_gateway)
        registry.register(fake)

        result = _get_or_create_agent("auditor_planner")
        assert result is fake
