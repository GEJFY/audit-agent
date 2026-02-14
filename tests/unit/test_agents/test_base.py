"""BaseAuditAgent テスト"""

import pytest
from unittest.mock import MagicMock

from src.agents.base import BaseAuditAgent, AgentResult
from src.agents.state import AuditorState
from src.config.constants import CONFIDENCE_THRESHOLD


class DummyAgent(BaseAuditAgent[AuditorState]):
    """テスト用ダミーAgent"""

    @property
    def agent_name(self) -> str:
        return "test_dummy"

    @property
    def agent_description(self) -> str:
        return "テスト用ダミーAgent"

    async def execute(self, state: AuditorState) -> AuditorState:
        state.current_agent = self.agent_name
        return state


@pytest.fixture
def dummy_agent(mock_llm_gateway: MagicMock) -> DummyAgent:
    return DummyAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestBaseAuditAgent:
    """BaseAuditAgentのユニットテスト"""

    async def test_run_success(self, dummy_agent: DummyAgent) -> None:
        """正常実行テスト"""
        state = AuditorState(project_id="test-project", tenant_id="test-tenant")
        result = await dummy_agent.run(state)

        assert result.current_agent == "test_dummy"

    async def test_agent_name(self, dummy_agent: DummyAgent) -> None:
        """Agent名テスト"""
        assert dummy_agent.agent_name == "test_dummy"
        assert dummy_agent.agent_description == "テスト用ダミーAgent"

    def test_should_escalate_low_confidence(self, dummy_agent: DummyAgent) -> None:
        """信頼度低下時のエスカレーション判定"""
        assert dummy_agent.should_escalate(0.5) is True
        assert dummy_agent.should_escalate(0.3) is True

    def test_should_not_escalate_high_confidence(self, dummy_agent: DummyAgent) -> None:
        """信頼度十分時のエスカレーション不要判定"""
        assert dummy_agent.should_escalate(0.9) is False
        assert dummy_agent.should_escalate(CONFIDENCE_THRESHOLD) is False

    async def test_call_llm(self, dummy_agent: DummyAgent) -> None:
        """LLM呼び出しテスト"""
        result = await dummy_agent.call_llm("テストプロンプト")
        assert result == '{"result": "test"}'

    def test_record_decision(
        self, dummy_agent: DummyAgent, auditor_tenant_id: str
    ) -> None:
        """判断記録テスト"""
        dummy_agent.record_decision(
            tenant_id=str(auditor_tenant_id),
            decision="test_decision",
            reasoning="テスト理由",
            confidence=0.9,
            resource_type="test",
            resource_id="test-id",
        )
        # エラーなく実行できることを確認
