"""Agent Registry テスト"""

from unittest.mock import MagicMock

import pytest

from src.agents.base import BaseAuditAgent
from src.agents.registry import AgentRegistry
from src.agents.state import AuditorState


class DummyAgentA(BaseAuditAgent[AuditorState]):
    @property
    def agent_name(self) -> str:
        return "dummy_a"

    @property
    def agent_description(self) -> str:
        return "テスト用A"

    async def execute(self, state: AuditorState) -> AuditorState:
        state.current_agent = self.agent_name
        return state


class DummyAgentB(BaseAuditAgent[AuditorState]):
    @property
    def agent_name(self) -> str:
        return "dummy_b"

    @property
    def agent_description(self) -> str:
        return "テスト用B"

    async def execute(self, state: AuditorState) -> AuditorState:
        state.current_agent = self.agent_name
        return state


@pytest.mark.unit
class TestAgentRegistry:
    """AgentRegistryのユニットテスト"""

    def test_singleton(self) -> None:
        """シングルトンパターンの確認"""
        r1 = AgentRegistry.get_instance()
        r2 = AgentRegistry.get_instance()
        assert r1 is r2

    def test_register_and_get(self, mock_llm_gateway: MagicMock) -> None:
        """登録・取得テスト"""
        registry = AgentRegistry.get_instance()
        agent = DummyAgentA(llm_gateway=mock_llm_gateway)

        registry.register(agent)

        assert registry.has("dummy_a")
        assert registry.get("dummy_a") is agent

    def test_get_unknown_raises(self) -> None:
        """未登録Agent取得でKeyError"""
        registry = AgentRegistry.get_instance()

        with pytest.raises(KeyError, match="unknown_agent"):
            registry.get("unknown_agent")

    def test_list_agents(self, mock_llm_gateway: MagicMock) -> None:
        """一覧取得テスト"""
        registry = AgentRegistry.get_instance()
        registry.register(DummyAgentA(llm_gateway=mock_llm_gateway))
        registry.register(DummyAgentB(llm_gateway=mock_llm_gateway))

        agents = registry.list_agents()

        assert len(agents) == 2
        names = [a["name"] for a in agents]
        assert "dummy_a" in names
        assert "dummy_b" in names

    def test_has_agent(self, mock_llm_gateway: MagicMock) -> None:
        """存在確認テスト"""
        registry = AgentRegistry.get_instance()
        registry.register(DummyAgentA(llm_gateway=mock_llm_gateway))

        assert registry.has("dummy_a") is True
        assert registry.has("nonexistent") is False
