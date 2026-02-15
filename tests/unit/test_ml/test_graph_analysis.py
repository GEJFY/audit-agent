"""リスクグラフ分析 テスト"""

from typing import Any

import pytest

from src.ml.graph_analysis import (
    CentralityResult,
    GraphAnalysisResult,
    GraphEdge,
    GraphNode,
    RiskGraphAnalyzer,
    RiskPropagationPath,
)


def _sample_risks() -> list[dict[str, Any]]:
    """テスト用リスクデータ"""
    return [
        {"id": "R001", "name": "売上計上リスク", "score": 80, "category": "financial"},
        {"id": "R002", "name": "在庫リスク", "score": 60, "category": "operational"},
        {"id": "R003", "name": "アクセスリスク", "score": 70, "category": "it"},
    ]


def _sample_controls() -> list[dict[str, Any]]:
    """テスト用統制データ"""
    return [
        {"id": "C001", "name": "売上照合", "risk_id": "R001", "type": "detective"},
        {"id": "C002", "name": "在庫棚卸", "risk_id": "R002", "type": "detective"},
        {"id": "C003", "name": "アクセスレビュー", "risk_id": "R003", "type": "preventive"},
        {"id": "C004", "name": "承認フロー", "risk_id": "R001", "type": "preventive"},
    ]


@pytest.mark.unit
class TestGraphNodeEdge:
    """GraphNode/GraphEdge データクラステスト"""

    def test_graph_node_creation(self) -> None:
        """GraphNodeの作成"""
        node = GraphNode(
            node_id="R001",
            node_type="risk",
            label="売上計上リスク",
            score=80.0,
        )
        assert node.node_id == "R001"
        assert node.node_type == "risk"
        assert node.score == 80.0
        assert node.metadata == {}

    def test_graph_node_with_metadata(self) -> None:
        """メタデータ付きGraphNode"""
        node = GraphNode(
            node_id="C001",
            node_type="control",
            label="売上照合",
            metadata={"type": "detective"},
        )
        assert node.metadata["type"] == "detective"

    def test_graph_edge_creation(self) -> None:
        """GraphEdgeの作成"""
        edge = GraphEdge(
            source="C001",
            target="R001",
            edge_type="mitigates",
            weight=1.0,
        )
        assert edge.source == "C001"
        assert edge.target == "R001"
        assert edge.edge_type == "mitigates"

    def test_graph_edge_default_weight(self) -> None:
        """デフォルトweight=1.0"""
        edge = GraphEdge(source="A", target="B", edge_type="depends_on")
        assert edge.weight == 1.0


@pytest.mark.unit
class TestRiskGraphAnalyzerBasic:
    """RiskGraphAnalyzer 基本テスト"""

    def test_empty_graph(self) -> None:
        """空グラフの分析"""
        analyzer = RiskGraphAnalyzer()
        result = analyzer.analyze()

        assert result.total_nodes == 0
        assert result.total_edges == 0
        assert result.centrality_ranking == []

    def test_add_node(self) -> None:
        """ノード追加"""
        analyzer = RiskGraphAnalyzer()
        node = GraphNode(node_id="R001", node_type="risk", label="テスト")
        analyzer.add_node(node)

        assert analyzer.get_node("R001") is not None
        assert analyzer.get_node("R001").label == "テスト"

    def test_add_edge(self) -> None:
        """エッジ追加"""
        analyzer = RiskGraphAnalyzer()
        analyzer.add_node(GraphNode("A", "risk", "Risk A"))
        analyzer.add_node(GraphNode("B", "control", "Control B"))
        analyzer.add_edge(GraphEdge("B", "A", "mitigates"))

        result = analyzer.analyze()
        assert result.total_edges >= 1

    def test_get_node_not_found(self) -> None:
        """存在しないノードはNone"""
        analyzer = RiskGraphAnalyzer()
        assert analyzer.get_node("nonexistent") is None

    def test_get_nodes_by_type(self) -> None:
        """タイプ別ノード取得"""
        analyzer = RiskGraphAnalyzer()
        analyzer.add_node(GraphNode("R001", "risk", "Risk 1"))
        analyzer.add_node(GraphNode("R002", "risk", "Risk 2"))
        analyzer.add_node(GraphNode("C001", "control", "Control 1"))

        risks = analyzer.get_nodes_by_type("risk")
        controls = analyzer.get_nodes_by_type("control")

        assert len(risks) == 2
        assert len(controls) == 1

    def test_clear(self) -> None:
        """グラフクリア"""
        analyzer = RiskGraphAnalyzer()
        analyzer.add_node(GraphNode("R001", "risk", "Risk 1"))
        analyzer.add_edge(GraphEdge("R001", "R002", "depends_on"))
        analyzer.clear()

        assert analyzer.get_node("R001") is None
        result = analyzer.analyze()
        assert result.total_nodes == 0


@pytest.mark.unit
class TestBuildFromRCM:
    """RCMデータからのグラフ構築テスト"""

    def test_build_nodes(self) -> None:
        """RCMからノードが正しく作成される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())

        # 3リスク + 4統制 = 7ノード
        result = analyzer.analyze()
        assert result.total_nodes == 7

    def test_build_risk_nodes(self) -> None:
        """リスクノードが正しく作成される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())

        risks = analyzer.get_nodes_by_type("risk")
        assert len(risks) == 3
        assert any(r.node_id == "R001" for r in risks)

    def test_build_control_nodes(self) -> None:
        """統制ノードが正しく作成される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())

        controls = analyzer.get_nodes_by_type("control")
        assert len(controls) == 4

    def test_build_edges(self) -> None:
        """統制→リスクのエッジが作成される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())

        result = analyzer.analyze()
        # C001→R001, C002→R002, C003→R003, C004→R001 = 4エッジ
        assert result.total_edges == 4

    def test_build_risk_score(self) -> None:
        """リスクスコアがノードに設定される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), [])

        node = analyzer.get_node("R001")
        assert node is not None
        assert node.score == 80

    def test_build_control_without_risk_id(self) -> None:
        """risk_id未指定の統制はエッジなし"""
        analyzer = RiskGraphAnalyzer()
        controls = [{"id": "C999", "name": "独立統制"}]
        analyzer.build_from_rcm([], controls)

        result = analyzer.analyze()
        assert result.total_nodes == 1
        assert result.total_edges == 0


@pytest.mark.unit
class TestGraphAnalysis:
    """グラフ分析テスト"""

    def test_analyze_returns_result(self) -> None:
        """分析結果の型"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())
        result = analyzer.analyze()

        assert isinstance(result, GraphAnalysisResult)

    def test_centrality_ranking(self) -> None:
        """中心性ランキングが生成される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())
        result = analyzer.analyze()

        assert len(result.centrality_ranking) == 7
        for cr in result.centrality_ranking:
            assert isinstance(cr, CentralityResult)
            assert 0.0 <= cr.degree_centrality <= 1.0

    def test_centrality_sorted_by_pagerank(self) -> None:
        """中心性がPageRank降順ソート"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())
        result = analyzer.analyze()

        pageranks = [cr.pagerank for cr in result.centrality_ranking]
        assert pageranks == sorted(pageranks, reverse=True)

    def test_clusters(self) -> None:
        """クラスタが検出される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())
        result = analyzer.analyze()

        # 接続されたコンポーネント
        assert isinstance(result.clusters, list)

    def test_density(self) -> None:
        """密度が計算される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())
        result = analyzer.analyze()

        assert 0.0 <= result.density <= 1.0

    def test_is_connected(self) -> None:
        """接続性が判定される"""
        analyzer = RiskGraphAnalyzer()
        analyzer.build_from_rcm(_sample_risks(), _sample_controls())
        result = analyzer.analyze()

        assert isinstance(result.is_connected, bool)


@pytest.mark.unit
class TestResultDataclasses:
    """結果データクラス テスト"""

    def test_centrality_result(self) -> None:
        """CentralityResultデータクラス"""
        cr = CentralityResult(
            node_id="R001",
            label="売上リスク",
            degree_centrality=0.5,
            betweenness_centrality=0.3,
            pagerank=0.15,
        )
        assert cr.node_id == "R001"
        assert cr.pagerank == 0.15

    def test_risk_propagation_path(self) -> None:
        """RiskPropagationPathデータクラス"""
        rpp = RiskPropagationPath(
            source_risk="R001",
            target_risk="R002",
            path=["R001", "C001", "R002"],
            total_weight=2.0,
        )
        assert rpp.source_risk == "R001"
        assert len(rpp.path) == 3

    def test_graph_analysis_result_defaults(self) -> None:
        """GraphAnalysisResult デフォルト値"""
        result = GraphAnalysisResult(
            total_nodes=5,
            total_edges=3,
            centrality_ranking=[],
            propagation_paths=[],
            clusters=[],
        )
        assert result.density == 0.0
        assert result.is_connected is True
