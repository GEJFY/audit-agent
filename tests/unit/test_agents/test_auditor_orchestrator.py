"""AuditorOrchestrator テスト"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.agents.auditor.orchestrator import AuditorOrchestrator
from src.agents.state import AuditorState


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> AuditorOrchestrator:
    return AuditorOrchestrator(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestAuditorOrchestrator:
    def test_agent_name(self, agent: AuditorOrchestrator) -> None:
        assert agent.agent_name == "auditor_orchestrator"

    async def test_phase_init_to_planning(self, agent: AuditorOrchestrator) -> None:
        """init → planning"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="init",
        )
        result = await agent.execute(state)
        assert result.current_phase == "planning"

    async def test_phase_planning_to_fieldwork(self, agent: AuditorOrchestrator) -> None:
        """planning → fieldwork（計画あり）"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="planning",
            audit_plan={"scope": "テスト", "test_procedures": []},
        )
        result = await agent.execute(state)
        assert result.current_phase == "fieldwork"

    async def test_phase_planning_stays_without_plan(self, agent: AuditorOrchestrator) -> None:
        """planning: 計画なしなら遷移しない"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="planning",
        )
        result = await agent.execute(state)
        assert result.current_phase == "planning"

    async def test_phase_fieldwork_to_reporting(self, agent: AuditorOrchestrator) -> None:
        """fieldwork → reporting（テスト結果＋検出事項あり）"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="fieldwork",
            test_results=[{"result": "effective"}],
            findings=[{"id": "f1"}],
        )
        result = await agent.execute(state)
        assert result.current_phase == "reporting"

    async def test_phase_fieldwork_stays_without_findings(self, agent: AuditorOrchestrator) -> None:
        """fieldwork: 検出事項なしなら遷移しない"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="fieldwork",
            test_results=[{"result": "effective"}],
        )
        result = await agent.execute(state)
        assert result.current_phase == "fieldwork"

    async def test_phase_reporting_to_follow_up(self, agent: AuditorOrchestrator) -> None:
        """reporting → follow_up（報告書あり）"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="reporting",
            report={"executive_summary": "テスト"},
        )
        result = await agent.execute(state)
        assert result.current_phase == "follow_up"

    async def test_phase_reporting_stays_without_report(self, agent: AuditorOrchestrator) -> None:
        """reporting: 報告書なしなら遷移しない"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="reporting",
        )
        result = await agent.execute(state)
        assert result.current_phase == "reporting"

    def test_route_to_planner(self, agent: AuditorOrchestrator) -> None:
        state = AuditorState(current_phase="planning")
        assert agent.route_to_agent(state) == "auditor_planner"

    def test_route_to_controls_tester(self, agent: AuditorOrchestrator) -> None:
        state = AuditorState(current_phase="fieldwork")
        assert agent.route_to_agent(state) == "auditor_controls_tester"

    def test_route_to_report_writer(self, agent: AuditorOrchestrator) -> None:
        state = AuditorState(current_phase="reporting")
        assert agent.route_to_agent(state) == "auditor_report_writer"

    def test_route_to_follow_up(self, agent: AuditorOrchestrator) -> None:
        state = AuditorState(current_phase="follow_up")
        assert agent.route_to_agent(state) == "auditor_follow_up"

    def test_route_unknown_phase(self, agent: AuditorOrchestrator) -> None:
        state = AuditorState(current_phase="unknown")
        assert agent.route_to_agent(state) == "auditor_orchestrator"

    async def test_current_agent_set(self, agent: AuditorOrchestrator) -> None:
        """current_agentが設定される"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            current_phase="init",
        )
        result = await agent.execute(state)
        assert result.current_agent == "auditor_orchestrator"
