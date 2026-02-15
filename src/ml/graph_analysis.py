"""リスクグラフ分析 — 統制依存グラフ・リスク伝播分析

リスクと統制の依存関係をグラフとして表現し、
中心性分析・伝播パス分析・クラスタリングを実施。
NetworkXベース。
"""

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


@dataclass
class GraphNode:
    """グラフノード"""

    node_id: str
    node_type: str  # risk, control, process, department
    label: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """グラフエッジ"""

    source: str
    target: str
    edge_type: str  # mitigates, depends_on, escalates_to, impacts
    weight: float = 1.0


@dataclass
class CentralityResult:
    """中心性分析結果"""

    node_id: str
    label: str
    degree_centrality: float = 0.0
    betweenness_centrality: float = 0.0
    pagerank: float = 0.0


@dataclass
class RiskPropagationPath:
    """リスク伝播パス"""

    source_risk: str
    target_risk: str
    path: list[str]
    total_weight: float = 0.0


@dataclass
class GraphAnalysisResult:
    """グラフ分析結果"""

    total_nodes: int
    total_edges: int
    centrality_ranking: list[CentralityResult]
    propagation_paths: list[RiskPropagationPath]
    clusters: list[list[str]]
    density: float = 0.0
    is_connected: bool = True


class RiskGraphAnalyzer:
    """リスクグラフ分析エンジン

    NetworkXが利用不可の場合は簡易分析にフォールバック。
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        """ノード追加"""
        self._nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """エッジ追加"""
        self._edges.append(edge)

    def build_from_rcm(
        self,
        risks: list[dict[str, Any]],
        controls: list[dict[str, Any]],
    ) -> None:
        """RCMデータからグラフを構築

        Args:
            risks: [{"id": ..., "name": ..., "score": ..., "category": ...}]
            controls: [{"id": ..., "name": ..., "risk_id": ..., "type": ...}]
        """
        for risk in risks:
            self.add_node(
                GraphNode(
                    node_id=risk["id"],
                    node_type="risk",
                    label=risk.get("name", risk["id"]),
                    score=risk.get("score", 0),
                    metadata={"category": risk.get("category", "")},
                )
            )

        for ctrl in controls:
            self.add_node(
                GraphNode(
                    node_id=ctrl["id"],
                    node_type="control",
                    label=ctrl.get("name", ctrl["id"]),
                    metadata={"type": ctrl.get("type", "detective")},
                )
            )
            # 統制→リスク（緩和関係）
            if ctrl.get("risk_id"):
                self.add_edge(
                    GraphEdge(
                        source=ctrl["id"],
                        target=ctrl["risk_id"],
                        edge_type="mitigates",
                        weight=1.0,
                    )
                )

    def analyze(self) -> GraphAnalysisResult:
        """グラフ分析を実行"""
        if HAS_NETWORKX and self._nodes:
            return self._analyze_networkx()
        return self._analyze_simple()

    def _analyze_networkx(self) -> GraphAnalysisResult:
        """NetworkXによる分析"""
        g = nx.DiGraph()

        for node_id, node in self._nodes.items():
            g.add_node(node_id, **{"label": node.label, "type": node.node_type})

        for edge in self._edges:
            if edge.source in g and edge.target in g:
                g.add_edge(edge.source, edge.target, weight=edge.weight)

        if g.number_of_nodes() == 0:
            return GraphAnalysisResult(
                total_nodes=0,
                total_edges=0,
                centrality_ranking=[],
                propagation_paths=[],
                clusters=[],
            )

        # 中心性分析
        degree = nx.degree_centrality(g)
        betweenness = nx.betweenness_centrality(g, weight="weight")
        pagerank = nx.pagerank(g, weight="weight")

        centrality: list[CentralityResult] = []
        for node_id in g.nodes():
            label = self._nodes.get(node_id, GraphNode(node_id, "", "")).label
            centrality.append(
                CentralityResult(
                    node_id=node_id,
                    label=label,
                    degree_centrality=round(degree.get(node_id, 0), 4),
                    betweenness_centrality=round(
                        betweenness.get(node_id, 0), 4
                    ),
                    pagerank=round(pagerank.get(node_id, 0), 4),
                )
            )

        # PageRank降順ソート
        centrality.sort(key=lambda c: c.pagerank, reverse=True)

        # リスク伝播パス
        risk_nodes = [
            n for n, d in g.nodes(data=True) if d.get("type") == "risk"
        ]
        propagation_paths = self._find_propagation_paths(g, risk_nodes)

        # クラスタリング（無向グラフに変換）
        ug = g.to_undirected()
        clusters = [
            list(c) for c in nx.connected_components(ug) if len(c) > 1
        ]

        density = nx.density(g)
        is_connected = nx.is_weakly_connected(g) if g.number_of_nodes() > 0 else True

        logger.info(
            "グラフ分析完了: nodes={}, edges={}, clusters={}",
            g.number_of_nodes(),
            g.number_of_edges(),
            len(clusters),
        )

        return GraphAnalysisResult(
            total_nodes=g.number_of_nodes(),
            total_edges=g.number_of_edges(),
            centrality_ranking=centrality,
            propagation_paths=propagation_paths,
            clusters=clusters,
            density=round(density, 4),
            is_connected=is_connected,
        )

    def _find_propagation_paths(
        self, g: Any, risk_nodes: list[str]
    ) -> list[RiskPropagationPath]:
        """リスクノード間の伝播パスを発見"""
        paths: list[RiskPropagationPath] = []

        for i, source in enumerate(risk_nodes):
            for target in risk_nodes[i + 1:]:
                try:
                    path = nx.shortest_path(g, source, target, weight="weight")
                    weight = nx.shortest_path_length(
                        g, source, target, weight="weight"
                    )
                    paths.append(
                        RiskPropagationPath(
                            source_risk=source,
                            target_risk=target,
                            path=path,
                            total_weight=round(weight, 2),
                        )
                    )
                except nx.NetworkXNoPath:
                    continue

        return paths

    def _analyze_simple(self) -> GraphAnalysisResult:
        """NetworkX未インストール時の簡易分析"""
        # 隣接リスト構築
        adjacency: dict[str, list[str]] = {}
        for edge in self._edges:
            adjacency.setdefault(edge.source, []).append(edge.target)

        # 簡易中心性（次数のみ）
        degree_count: dict[str, int] = {}
        for edge in self._edges:
            degree_count[edge.source] = degree_count.get(edge.source, 0) + 1
            degree_count[edge.target] = degree_count.get(edge.target, 0) + 1

        n = max(len(self._nodes), 1)
        centrality = [
            CentralityResult(
                node_id=node_id,
                label=self._nodes.get(
                    node_id, GraphNode(node_id, "", "")
                ).label,
                degree_centrality=round(
                    degree_count.get(node_id, 0) / n, 4
                ),
            )
            for node_id in self._nodes
        ]
        centrality.sort(
            key=lambda c: c.degree_centrality, reverse=True
        )

        return GraphAnalysisResult(
            total_nodes=len(self._nodes),
            total_edges=len(self._edges),
            centrality_ranking=centrality,
            propagation_paths=[],
            clusters=[],
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        """ノード取得"""
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[GraphNode]:
        """ノードタイプ別取得"""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def clear(self) -> None:
        """グラフをクリア"""
        self._nodes.clear()
        self._edges.clear()
