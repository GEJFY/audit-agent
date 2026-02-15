"""プロセスマイニング — トランザクションログからプロセスフロー分析

トランザクションログからアクティビティグラフを構築し、
バリアント分析・ボトルネック検出・逸脱検知を実施。
NetworkXベース（Neo4j不要）。
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class ActivityEdge:
    """アクティビティ間の遷移"""

    source: str
    target: str
    count: int = 0
    avg_duration_hours: float = 0.0
    max_duration_hours: float = 0.0


@dataclass
class ProcessVariant:
    """プロセスバリアント — 実行パスの一つのパターン"""

    path: list[str]
    count: int = 0
    avg_duration_hours: float = 0.0
    is_standard: bool = False


@dataclass
class Bottleneck:
    """ボトルネック — 遅延が発生しているアクティビティ遷移"""

    source: str
    target: str
    avg_duration_hours: float
    threshold_hours: float
    severity: str  # high, medium, low
    occurrence_count: int = 0


@dataclass
class ProcessDeviation:
    """プロセス逸脱 — 標準フローからの乖離"""

    case_id: str
    deviation_type: str  # skip, repeat, unexpected_path
    description: str
    severity: str  # high, medium, low
    affected_activities: list[str] = field(default_factory=list)


@dataclass
class ProcessMiningResult:
    """プロセスマイニング分析結果"""

    total_cases: int
    total_activities: int
    unique_activities: int
    variants: list[ProcessVariant]
    bottlenecks: list[Bottleneck]
    deviations: list[ProcessDeviation]
    conformance_rate: float  # 0-1
    edges: list[ActivityEdge] = field(default_factory=list)


class ProcessMiner:
    """プロセスマイニングエンジン

    トランザクションログからプロセスフローを抽出し分析。

    入力形式:
        [{"case_id": "C001", "activity": "入力", "timestamp": "2025-01-01T10:00:00",
          "resource": "UserA", "amount": 1000000}]
    """

    def __init__(
        self,
        bottleneck_threshold_hours: float = 24.0,
        min_variant_count: int = 2,
    ) -> None:
        self._bottleneck_threshold = bottleneck_threshold_hours
        self._min_variant_count = min_variant_count

    def analyze(
        self,
        event_log: list[dict[str, Any]],
        standard_path: list[str] | None = None,
    ) -> ProcessMiningResult:
        """プロセスマイニング分析を実行

        Args:
            event_log: イベントログ（case_id, activity, timestamp必須）
            standard_path: 標準プロセスパス（逸脱検出用）

        Returns:
            ProcessMiningResult
        """
        if not event_log:
            return ProcessMiningResult(
                total_cases=0,
                total_activities=0,
                unique_activities=0,
                variants=[],
                bottlenecks=[],
                deviations=[],
                conformance_rate=1.0,
            )

        # ケース別にイベントをグループ化
        cases = self._group_by_case(event_log)

        # アクティビティグラフ構築
        edges = self._build_activity_graph(cases)

        # バリアント分析
        variants = self._extract_variants(cases)

        # ボトルネック検出
        bottlenecks = self._detect_bottlenecks(edges)

        # 逸脱検出
        deviations: list[ProcessDeviation] = []
        conformance_rate = 1.0
        if standard_path:
            deviations = self._detect_deviations(cases, standard_path)
            conforming = sum(1 for case_id, events in cases.items() if self._is_conforming(events, standard_path))
            conformance_rate = conforming / max(len(cases), 1)

        unique_activities = set()
        for events in cases.values():
            for e in events:
                unique_activities.add(e["activity"])

        total_activities = sum(len(events) for events in cases.values())

        logger.info(
            "プロセスマイニング完了: cases={}, variants={}, bottlenecks={}, deviations={}",
            len(cases),
            len(variants),
            len(bottlenecks),
            len(deviations),
        )

        return ProcessMiningResult(
            total_cases=len(cases),
            total_activities=total_activities,
            unique_activities=len(unique_activities),
            variants=variants,
            bottlenecks=bottlenecks,
            deviations=deviations,
            conformance_rate=conformance_rate,
            edges=edges,
        )

    def _group_by_case(self, event_log: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """ケース別にイベントをグループ化し、タイムスタンプ順にソート"""
        cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in event_log:
            cases[event["case_id"]].append(event)

        # タイムスタンプ順にソート
        for case_id in cases:
            cases[case_id].sort(key=lambda e: e.get("timestamp", ""))

        return dict(cases)

    def _build_activity_graph(self, cases: dict[str, list[dict[str, Any]]]) -> list[ActivityEdge]:
        """アクティビティ遷移グラフを構築"""
        edge_counts: Counter[tuple[str, str]] = Counter()
        edge_durations: dict[tuple[str, str], list[float]] = defaultdict(list)

        for events in cases.values():
            for i in range(len(events) - 1):
                source = events[i]["activity"]
                target = events[i + 1]["activity"]
                edge_key = (source, target)
                edge_counts[edge_key] += 1

                # 所要時間の計算
                ts1 = events[i].get("timestamp", "")
                ts2 = events[i + 1].get("timestamp", "")
                if ts1 and ts2:
                    duration = self._calc_duration_hours(ts1, ts2)
                    if duration >= 0:
                        edge_durations[edge_key].append(duration)

        edges: list[ActivityEdge] = []
        for (source, target), count in edge_counts.items():
            durations = edge_durations.get((source, target), [])
            avg_dur = sum(durations) / len(durations) if durations else 0.0
            max_dur = max(durations) if durations else 0.0
            edges.append(
                ActivityEdge(
                    source=source,
                    target=target,
                    count=count,
                    avg_duration_hours=round(avg_dur, 2),
                    max_duration_hours=round(max_dur, 2),
                )
            )

        return edges

    def _extract_variants(self, cases: dict[str, list[dict[str, Any]]]) -> list[ProcessVariant]:
        """プロセスバリアント（実行パスのパターン）を抽出"""
        path_counter: Counter[tuple[str, ...]] = Counter()

        for events in cases.values():
            path = tuple(e["activity"] for e in events)
            path_counter[path] += 1

        variants: list[ProcessVariant] = []
        for path, count in path_counter.most_common():
            if count >= self._min_variant_count or not variants:
                variants.append(
                    ProcessVariant(
                        path=list(path),
                        count=count,
                        is_standard=len(variants) == 0,  # 最頻パスを標準とする
                    )
                )

        return variants

    def _detect_bottlenecks(self, edges: list[ActivityEdge]) -> list[Bottleneck]:
        """ボトルネック（閾値超過の遅延遷移）を検出"""
        bottlenecks: list[Bottleneck] = []
        for edge in edges:
            if edge.avg_duration_hours > self._bottleneck_threshold:
                ratio = edge.avg_duration_hours / self._bottleneck_threshold
                if ratio > 3:
                    severity = "high"
                elif ratio > 1.5:
                    severity = "medium"
                else:
                    severity = "low"

                bottlenecks.append(
                    Bottleneck(
                        source=edge.source,
                        target=edge.target,
                        avg_duration_hours=edge.avg_duration_hours,
                        threshold_hours=self._bottleneck_threshold,
                        severity=severity,
                        occurrence_count=edge.count,
                    )
                )

        return sorted(
            bottlenecks,
            key=lambda b: b.avg_duration_hours,
            reverse=True,
        )

    def _detect_deviations(
        self,
        cases: dict[str, list[dict[str, Any]]],
        standard_path: list[str],
    ) -> list[ProcessDeviation]:
        """標準パスからの逸脱を検出"""
        deviations: list[ProcessDeviation] = []

        for case_id, events in cases.items():
            actual_path = [e["activity"] for e in events]

            # スキップ検出
            for activity in standard_path:
                if activity not in actual_path:
                    deviations.append(
                        ProcessDeviation(
                            case_id=case_id,
                            deviation_type="skip",
                            description=f"アクティビティ '{activity}' がスキップされました",
                            severity="high" if activity in standard_path[:2] else "medium",
                            affected_activities=[activity],
                        )
                    )

            # 繰り返し検出
            activity_counts = Counter(actual_path)
            for activity, count in activity_counts.items():
                if count > 1 and activity in standard_path:
                    deviations.append(
                        ProcessDeviation(
                            case_id=case_id,
                            deviation_type="repeat",
                            description=f"アクティビティ '{activity}' が{count}回繰り返されました",
                            severity="medium",
                            affected_activities=[activity],
                        )
                    )

            # 予期しないパス（標準にないアクティビティ）
            unexpected = set(actual_path) - set(standard_path)
            if unexpected:
                deviations.append(
                    ProcessDeviation(
                        case_id=case_id,
                        deviation_type="unexpected_path",
                        description=f"予期しないアクティビティ: {', '.join(unexpected)}",
                        severity="low",
                        affected_activities=list(unexpected),
                    )
                )

        return deviations

    def _is_conforming(self, events: list[dict[str, Any]], standard_path: list[str]) -> bool:
        """ケースが標準パスに適合しているか"""
        actual = [e["activity"] for e in events]
        return actual == standard_path

    @staticmethod
    def _calc_duration_hours(ts1: str, ts2: str) -> float:
        """2つのタイムスタンプ間の時間差（時間）"""
        from datetime import datetime

        try:
            t1 = datetime.fromisoformat(ts1.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(ts2.replace("Z", "+00:00"))
            return (t2 - t1).total_seconds() / 3600
        except (ValueError, TypeError):
            return 0.0
