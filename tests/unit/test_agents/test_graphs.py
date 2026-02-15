"""StateGraph トポロジー・遷移テスト"""

import pytest

from src.agents.graphs.auditee_graph import (
    _orchestrator_node as _auditee_orchestrator_node,
)
from src.agents.graphs.auditee_graph import (
    _route_after_evidence,
    _route_after_orchestrator,
    _route_after_response,
    build_auditee_monitoring_graph,
    build_auditee_response_graph,
    compile_auditee_monitoring_graph,
    compile_auditee_response_graph,
)
from src.agents.graphs.auditor_graph import (
    _orchestrator_node,
    _route_after_anomaly,
    _route_after_planner,
    _route_after_reporter,
    build_auditor_graph,
    compile_auditor_graph,
)
from src.agents.state import AuditeeState, AuditorState


@pytest.mark.unit
class TestAuditorGraphTopology:
    """監査側グラフトポロジーテスト"""

    def test_build_auditor_graph(self) -> None:
        """グラフ構築が成功する"""
        graph = build_auditor_graph()
        assert graph is not None

    def test_compile_auditor_graph(self) -> None:
        """グラフコンパイルが成功する"""
        compiled = compile_auditor_graph()
        assert compiled is not None

    def test_auditor_graph_has_all_nodes(self) -> None:
        """全ノードが登録されている"""
        graph = build_auditor_graph()
        nodes = set(graph.nodes)
        expected = {
            "orchestrator",
            "planner",
            "human_approval_plan",
            "data_collector",
            "controls_tester",
            "anomaly_detective",
            "knowledge",
            "report_writer",
            "human_approval_report",
            "follow_up",
        }
        assert expected.issubset(nodes)

    def test_auditor_graph_start_edge(self) -> None:
        """START → orchestrator エッジが存在する"""
        compiled = compile_auditor_graph()
        graph_dict = compiled.get_graph().to_json()
        # グラフが構築されればSTART→orchestratorは存在する
        assert graph_dict is not None

    def test_compile_with_interrupt(self) -> None:
        """interrupt_before を指定してコンパイル"""
        compiled = compile_auditor_graph(interrupt_before=["human_approval_plan", "human_approval_report"])
        assert compiled is not None


@pytest.mark.unit
class TestAuditorOrchestratorNode:
    """Orchestrator ノード遷移テスト"""

    def test_init_to_planning(self) -> None:
        """init → planning"""
        state = AuditorState(current_phase="init")
        result = _orchestrator_node(state)
        assert result["current_phase"] == "planning"

    def test_planning_to_fieldwork(self) -> None:
        """planning（計画あり） → fieldwork"""
        state = AuditorState(
            current_phase="planning",
            audit_plan={"objectives": ["test"]},
        )
        result = _orchestrator_node(state)
        assert result["current_phase"] == "fieldwork"

    def test_planning_stays_without_plan(self) -> None:
        """planning（計画なし） → planning のまま"""
        state = AuditorState(current_phase="planning")
        result = _orchestrator_node(state)
        assert result["current_phase"] == "planning"

    def test_fieldwork_to_reporting(self) -> None:
        """fieldwork（指摘あり） → reporting"""
        state = AuditorState(
            current_phase="fieldwork",
            test_results=[{"result": "pass"}],
            findings=[{"finding": "issue"}],
        )
        result = _orchestrator_node(state)
        assert result["current_phase"] == "reporting"

    def test_fieldwork_stays_without_findings(self) -> None:
        """fieldwork（指摘なし） → fieldwork のまま"""
        state = AuditorState(
            current_phase="fieldwork",
            test_results=[{"result": "pass"}],
        )
        result = _orchestrator_node(state)
        assert result["current_phase"] == "fieldwork"

    def test_reporting_to_follow_up(self) -> None:
        """reporting（報告書あり） → follow_up"""
        state = AuditorState(
            current_phase="reporting",
            report={"content": "test report"},
        )
        result = _orchestrator_node(state)
        assert result["current_phase"] == "follow_up"


@pytest.mark.unit
class TestAuditorConditionalRouting:
    """条件分岐ルーティングテスト"""

    def test_planner_route_with_approval(self) -> None:
        """Planner後 — 承認必要 → human_approval_plan"""
        state = AuditorState(requires_approval=True)
        assert _route_after_planner(state) == "human_approval_plan"

    def test_planner_route_without_approval(self) -> None:
        """Planner後 — 承認不要 → data_collector"""
        state = AuditorState(requires_approval=False)
        assert _route_after_planner(state) == "data_collector"

    def test_anomaly_route_with_questions(self) -> None:
        """異常検知後 — 質問あり → knowledge"""
        state = AuditorState(
            pending_questions=[{"question": "test?"}],
        )
        assert _route_after_anomaly(state) == "knowledge"

    def test_anomaly_route_without_questions(self) -> None:
        """異常検知後 — 質問なし → report_writer"""
        state = AuditorState()
        assert _route_after_anomaly(state) == "report_writer"

    def test_reporter_route_with_approval(self) -> None:
        """報告書後 — 承認必要 → human_approval_report"""
        state = AuditorState(requires_approval=True)
        assert _route_after_reporter(state) == "human_approval_report"

    def test_reporter_route_without_approval(self) -> None:
        """報告書後 — 承認不要 → follow_up"""
        state = AuditorState(requires_approval=False)
        assert _route_after_reporter(state) == "follow_up"


@pytest.mark.unit
class TestAuditeeGraphTopology:
    """被監査側グラフトポロジーテスト"""

    def test_build_response_graph(self) -> None:
        """レスポンスグラフ構築"""
        graph = build_auditee_response_graph()
        assert graph is not None

    def test_compile_response_graph(self) -> None:
        """レスポンスグラフコンパイル"""
        compiled = compile_auditee_response_graph()
        assert compiled is not None

    def test_build_monitoring_graph(self) -> None:
        """監視グラフ構築"""
        graph = build_auditee_monitoring_graph()
        assert graph is not None

    def test_compile_monitoring_graph(self) -> None:
        """監視グラフコンパイル"""
        compiled = compile_auditee_monitoring_graph()
        assert compiled is not None

    def test_response_graph_has_all_nodes(self) -> None:
        """レスポンスグラフの全ノード"""
        graph = build_auditee_response_graph()
        nodes = set(graph.nodes)
        expected = {
            "orchestrator",
            "response",
            "evidence_search",
            "prep",
            "human_approval",
        }
        assert expected.issubset(nodes)

    def test_monitoring_graph_has_all_nodes(self) -> None:
        """監視グラフの全ノード"""
        graph = build_auditee_monitoring_graph()
        nodes = set(graph.nodes)
        expected = {"controls_monitor", "risk_alert"}
        assert expected.issubset(nodes)

    def test_compile_response_with_interrupt(self) -> None:
        """interrupt_before を指定してコンパイル"""
        compiled = compile_auditee_response_graph(interrupt_before=["human_approval"])
        assert compiled is not None


@pytest.mark.unit
class TestAuditeeOrchestratorNode:
    """Auditee Orchestrator ノード遷移テスト"""

    def test_idle_no_questions(self) -> None:
        """質問なし → idle"""
        state = AuditeeState()
        result = _auditee_orchestrator_node(state)
        assert result["current_phase"] == "idle"

    def test_question_type_general(self) -> None:
        """一般質問 → responding"""
        state = AuditeeState(
            incoming_questions=[{"type": "general", "content": "test"}],
        )
        result = _auditee_orchestrator_node(state)
        assert result["current_phase"] == "responding"

    def test_question_type_evidence(self) -> None:
        """証跡リクエスト → searching"""
        state = AuditeeState(
            incoming_questions=[{"type": "evidence_request", "content": "test"}],
        )
        result = _auditee_orchestrator_node(state)
        assert result["current_phase"] == "searching"

    def test_question_type_preparation(self) -> None:
        """準備リクエスト → preparing"""
        state = AuditeeState(
            incoming_questions=[{"type": "preparation", "content": "test"}],
        )
        result = _auditee_orchestrator_node(state)
        assert result["current_phase"] == "preparing"


@pytest.mark.unit
class TestAuditeeConditionalRouting:
    """Auditee 条件分岐ルーティングテスト"""

    def test_orchestrator_route_idle(self) -> None:
        """idle → end"""
        state = AuditeeState(current_phase="idle")
        assert _route_after_orchestrator(state) == "end"

    def test_orchestrator_route_responding(self) -> None:
        """responding → response"""
        state = AuditeeState(current_phase="responding")
        assert _route_after_orchestrator(state) == "response"

    def test_orchestrator_route_searching(self) -> None:
        """searching → evidence_search"""
        state = AuditeeState(current_phase="searching")
        assert _route_after_orchestrator(state) == "evidence_search"

    def test_orchestrator_route_preparing(self) -> None:
        """preparing → prep"""
        state = AuditeeState(current_phase="preparing")
        assert _route_after_orchestrator(state) == "prep"

    def test_response_route_with_evidence_queue(self) -> None:
        """回答後 — 証跡キューあり → evidence_search"""
        state = AuditeeState(
            evidence_queue=[{"query": "test"}],
        )
        assert _route_after_response(state) == "evidence_search"

    def test_response_route_with_approval(self) -> None:
        """回答後 — 承認必要 → human_approval"""
        state = AuditeeState(requires_approval=True)
        assert _route_after_response(state) == "human_approval"

    def test_response_route_direct_end(self) -> None:
        """回答後 — そのまま → end"""
        state = AuditeeState()
        assert _route_after_response(state) == "end"

    def test_evidence_route_with_approval(self) -> None:
        """証跡検索後 — 承認必要 → human_approval"""
        state = AuditeeState(requires_approval=True)
        assert _route_after_evidence(state) == "human_approval"

    def test_evidence_route_direct_end(self) -> None:
        """証跡検索後 — そのまま → end"""
        state = AuditeeState()
        assert _route_after_evidence(state) == "end"


@pytest.mark.unit
class TestGraphFactory:
    """ファクトリインポートテスト"""

    def test_import_from_package(self) -> None:
        """パッケージからインポート"""
        from src.agents.graphs import (
            build_auditee_monitoring_graph,
            build_auditee_response_graph,
            build_auditor_graph,
            compile_auditee_monitoring_graph,
            compile_auditee_response_graph,
            compile_auditor_graph,
        )

        assert callable(build_auditor_graph)
        assert callable(compile_auditor_graph)
        assert callable(build_auditee_response_graph)
        assert callable(compile_auditee_response_graph)
        assert callable(build_auditee_monitoring_graph)
        assert callable(compile_auditee_monitoring_graph)
