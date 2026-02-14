"""Agent動的登録・取得レジストリ"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent


class AgentRegistry:
    """エージェントの登録・取得を管理するレジストリ"""

    _instance: "AgentRegistry | None" = None
    _agents: dict[str, BaseAuditAgent[Any]] = {}

    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """シングルトンインスタンスを返す"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, agent: BaseAuditAgent[Any]) -> None:
        """Agentを登録"""
        self._agents[agent.agent_name] = agent
        logger.info(f"Agent登録: {agent.agent_name}")

    def get(self, agent_name: str) -> BaseAuditAgent[Any]:
        """Agent名で取得"""
        agent = self._agents.get(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' が未登録")
        return agent

    def list_agents(self) -> list[dict[str, str]]:
        """登録済みAgent一覧"""
        return [
            {"name": a.agent_name, "description": a.agent_description}
            for a in self._agents.values()
        ]

    def has(self, agent_name: str) -> bool:
        """Agent登録確認"""
        return agent_name in self._agents
