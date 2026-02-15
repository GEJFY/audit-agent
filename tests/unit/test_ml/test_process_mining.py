"""プロセスマイニング テスト"""

from typing import Any

import pytest

from src.ml.process_mining import (
    ActivityEdge,
    Bottleneck,
    ProcessDeviation,
    ProcessMiner,
    ProcessMiningResult,
    ProcessVariant,
)


def _make_event(
    case_id: str,
    activity: str,
    timestamp: str,
    resource: str = "UserA",
    amount: float = 0,
) -> dict[str, Any]:
    """テスト用イベント生成ヘルパー"""
    return {
        "case_id": case_id,
        "activity": activity,
        "timestamp": timestamp,
        "resource": resource,
        "amount": amount,
    }


def _standard_event_log() -> list[dict[str, Any]]:
    """標準的なイベントログ（3ケース）"""
    return [
        # ケース1: 標準フロー
        _make_event("C001", "入力", "2025-01-01T09:00:00"),
        _make_event("C001", "承認", "2025-01-01T10:00:00"),
        _make_event("C001", "転記", "2025-01-01T11:00:00"),
        _make_event("C001", "完了", "2025-01-01T12:00:00"),
        # ケース2: 標準フロー
        _make_event("C002", "入力", "2025-01-02T09:00:00"),
        _make_event("C002", "承認", "2025-01-02T10:00:00"),
        _make_event("C002", "転記", "2025-01-02T11:00:00"),
        _make_event("C002", "完了", "2025-01-02T12:00:00"),
        # ケース3: 標準フロー
        _make_event("C003", "入力", "2025-01-03T09:00:00"),
        _make_event("C003", "承認", "2025-01-03T10:00:00"),
        _make_event("C003", "転記", "2025-01-03T11:00:00"),
        _make_event("C003", "完了", "2025-01-03T12:00:00"),
    ]


STANDARD_PATH = ["入力", "承認", "転記", "完了"]


@pytest.mark.unit
class TestProcessMinerBasic:
    """ProcessMiner 基本テスト"""

    def test_empty_event_log(self) -> None:
        """空のイベントログで安全に結果を返す"""
        miner = ProcessMiner()
        result = miner.analyze([])

        assert result.total_cases == 0
        assert result.total_activities == 0
        assert result.unique_activities == 0
        assert result.variants == []
        assert result.bottlenecks == []
        assert result.deviations == []
        assert result.conformance_rate == 1.0

    def test_single_case(self) -> None:
        """1ケースの分析"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "承認", "2025-01-01T10:00:00"),
            _make_event("C001", "完了", "2025-01-01T11:00:00"),
        ]
        miner = ProcessMiner()
        result = miner.analyze(events)

        assert result.total_cases == 1
        assert result.total_activities == 3
        assert result.unique_activities == 3

    def test_multiple_cases(self) -> None:
        """複数ケースの分析"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())

        assert result.total_cases == 3
        assert result.total_activities == 12
        assert result.unique_activities == 4

    def test_result_type(self) -> None:
        """結果がProcessMiningResult型"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())
        assert isinstance(result, ProcessMiningResult)


@pytest.mark.unit
class TestActivityGraph:
    """アクティビティグラフ構築テスト"""

    def test_edges_created(self) -> None:
        """遷移エッジが正しく作成される"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())

        assert len(result.edges) > 0
        edge_pairs = [(e.source, e.target) for e in result.edges]
        assert ("入力", "承認") in edge_pairs
        assert ("承認", "転記") in edge_pairs
        assert ("転記", "完了") in edge_pairs

    def test_edge_counts(self) -> None:
        """エッジのカウントが正しい"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())

        # 3ケース全て同じフロー → 各遷移3回
        for edge in result.edges:
            assert edge.count == 3

    def test_edge_duration(self) -> None:
        """エッジの所要時間が計算される"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "承認", "2025-01-01T11:00:00"),  # 2時間後
        ]
        miner = ProcessMiner()
        result = miner.analyze(events)

        assert len(result.edges) == 1
        assert result.edges[0].avg_duration_hours == 2.0
        assert result.edges[0].max_duration_hours == 2.0

    def test_edge_type(self) -> None:
        """ActivityEdgeデータクラスの構造確認"""
        edge = ActivityEdge(
            source="入力",
            target="承認",
            count=5,
            avg_duration_hours=1.5,
            max_duration_hours=3.0,
        )
        assert edge.source == "入力"
        assert edge.target == "承認"
        assert edge.count == 5


@pytest.mark.unit
class TestVariantAnalysis:
    """バリアント分析テスト"""

    def test_single_variant(self) -> None:
        """全ケース同一パス → 1バリアント"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())

        assert len(result.variants) >= 1
        assert result.variants[0].path == STANDARD_PATH
        assert result.variants[0].count == 3

    def test_standard_variant_flag(self) -> None:
        """最頻バリアントがis_standard=True"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())

        assert result.variants[0].is_standard is True

    def test_multiple_variants(self) -> None:
        """異なるパスを持つケースがある場合、複数バリアント"""
        events = [
            *_standard_event_log(),
            _make_event("C004", "入力", "2025-01-04T09:00:00"),
            _make_event("C004", "確認", "2025-01-04T10:00:00"),
            _make_event("C004", "完了", "2025-01-04T11:00:00"),
        ]
        miner = ProcessMiner(min_variant_count=1)
        result = miner.analyze(events)

        # 標準フロー (3回) + 別フロー (1回)
        assert len(result.variants) >= 2

    def test_min_variant_count_filter(self) -> None:
        """min_variant_countで頻度の低いバリアントをフィルタ"""
        events = [
            *_standard_event_log(),
            _make_event("C004", "入力", "2025-01-04T09:00:00"),
            _make_event("C004", "確認", "2025-01-04T10:00:00"),
        ]
        miner = ProcessMiner(min_variant_count=3)
        result = miner.analyze(events)

        # min_variant_count=3 なので1回のバリアントは除外される可能性
        # ただし最頻バリアントは常に含まれる
        assert len(result.variants) >= 1

    def test_variant_dataclass(self) -> None:
        """ProcessVariantデータクラスの構造確認"""
        variant = ProcessVariant(
            path=["入力", "承認", "完了"],
            count=5,
            is_standard=True,
        )
        assert variant.path == ["入力", "承認", "完了"]
        assert variant.count == 5
        assert variant.avg_duration_hours == 0.0


@pytest.mark.unit
class TestBottleneckDetection:
    """ボトルネック検出テスト"""

    def test_no_bottleneck_under_threshold(self) -> None:
        """閾値以下の遅延はボトルネックにならない"""
        miner = ProcessMiner(bottleneck_threshold_hours=24.0)
        result = miner.analyze(_standard_event_log())

        # 標準ログは各ステップ1時間 → 閾値24時間以下
        assert len(result.bottlenecks) == 0

    def test_bottleneck_detected(self) -> None:
        """閾値超過の遅延がボトルネックとして検出される"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "承認", "2025-01-03T09:00:00"),  # 48時間後
        ]
        miner = ProcessMiner(bottleneck_threshold_hours=24.0)
        result = miner.analyze(events)

        assert len(result.bottlenecks) == 1
        assert result.bottlenecks[0].source == "入力"
        assert result.bottlenecks[0].target == "承認"
        assert result.bottlenecks[0].avg_duration_hours == 48.0

    def test_bottleneck_severity_high(self) -> None:
        """ratio > 3 → severity=high"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "承認", "2025-01-05T09:00:00"),  # 96時間後
        ]
        miner = ProcessMiner(bottleneck_threshold_hours=24.0)
        result = miner.analyze(events)

        assert result.bottlenecks[0].severity == "high"

    def test_bottleneck_severity_medium(self) -> None:
        """ratio 1.5-3 → severity=medium"""
        events = [
            _make_event("C001", "入力", "2025-01-01T00:00:00"),
            _make_event("C001", "承認", "2025-01-03T12:00:00"),  # 60時間後
        ]
        miner = ProcessMiner(bottleneck_threshold_hours=24.0)
        result = miner.analyze(events)

        # 60/24 = 2.5 → medium
        assert result.bottlenecks[0].severity == "medium"

    def test_bottleneck_severity_low(self) -> None:
        """ratio 1.0-1.5 → severity=low"""
        events = [
            _make_event("C001", "入力", "2025-01-01T00:00:00"),
            _make_event("C001", "承認", "2025-01-02T06:00:00"),  # 30時間後
        ]
        miner = ProcessMiner(bottleneck_threshold_hours=24.0)
        result = miner.analyze(events)

        # 30/24 = 1.25 → low
        assert result.bottlenecks[0].severity == "low"

    def test_bottleneck_sorted_by_duration(self) -> None:
        """ボトルネックが所要時間の降順でソートされる"""
        events = [
            _make_event("C001", "A", "2025-01-01T00:00:00"),
            _make_event("C001", "B", "2025-01-03T00:00:00"),  # 48h
            _make_event("C001", "C", "2025-01-07T00:00:00"),  # 96h
        ]
        miner = ProcessMiner(bottleneck_threshold_hours=24.0)
        result = miner.analyze(events)

        assert len(result.bottlenecks) == 2
        assert (
            result.bottlenecks[0].avg_duration_hours
            >= result.bottlenecks[1].avg_duration_hours
        )


@pytest.mark.unit
class TestDeviationDetection:
    """逸脱検出テスト"""

    def test_no_deviation_conforming(self) -> None:
        """標準パスに適合 → 逸脱なし"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log(), standard_path=STANDARD_PATH)

        assert result.deviations == []
        assert result.conformance_rate == 1.0

    def test_skip_deviation(self) -> None:
        """アクティビティスキップの検出"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "転記", "2025-01-01T10:00:00"),  # 承認スキップ
            _make_event("C001", "完了", "2025-01-01T11:00:00"),
        ]
        miner = ProcessMiner()
        result = miner.analyze(events, standard_path=STANDARD_PATH)

        skip_devs = [d for d in result.deviations if d.deviation_type == "skip"]
        assert len(skip_devs) >= 1
        assert "承認" in skip_devs[0].affected_activities

    def test_repeat_deviation(self) -> None:
        """アクティビティ繰り返しの検出"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "承認", "2025-01-01T10:00:00"),
            _make_event("C001", "承認", "2025-01-01T11:00:00"),  # 承認2回
            _make_event("C001", "転記", "2025-01-01T12:00:00"),
            _make_event("C001", "完了", "2025-01-01T13:00:00"),
        ]
        miner = ProcessMiner()
        result = miner.analyze(events, standard_path=STANDARD_PATH)

        repeat_devs = [d for d in result.deviations if d.deviation_type == "repeat"]
        assert len(repeat_devs) >= 1

    def test_unexpected_path_deviation(self) -> None:
        """標準にないアクティビティの検出"""
        events = [
            _make_event("C001", "入力", "2025-01-01T09:00:00"),
            _make_event("C001", "特別承認", "2025-01-01T10:00:00"),  # 標準にない
            _make_event("C001", "承認", "2025-01-01T11:00:00"),
            _make_event("C001", "転記", "2025-01-01T12:00:00"),
            _make_event("C001", "完了", "2025-01-01T13:00:00"),
        ]
        miner = ProcessMiner()
        result = miner.analyze(events, standard_path=STANDARD_PATH)

        unexpected_devs = [
            d for d in result.deviations if d.deviation_type == "unexpected_path"
        ]
        assert len(unexpected_devs) >= 1
        assert "特別承認" in unexpected_devs[0].affected_activities

    def test_conformance_rate(self) -> None:
        """適合率の計算"""
        events = [
            *_standard_event_log(),
            # ケース4: 非適合（承認スキップ）
            _make_event("C004", "入力", "2025-01-04T09:00:00"),
            _make_event("C004", "転記", "2025-01-04T10:00:00"),
            _make_event("C004", "完了", "2025-01-04T11:00:00"),
        ]
        miner = ProcessMiner()
        result = miner.analyze(events, standard_path=STANDARD_PATH)

        # 3/4 = 0.75
        assert result.conformance_rate == 0.75

    def test_no_standard_path_no_deviations(self) -> None:
        """standard_path未指定時は逸脱検出しない"""
        miner = ProcessMiner()
        result = miner.analyze(_standard_event_log())

        assert result.deviations == []
        assert result.conformance_rate == 1.0


@pytest.mark.unit
class TestDurationCalculation:
    """時間差計算テスト"""

    def test_calc_duration_hours(self) -> None:
        """正常なタイムスタンプの時間差計算"""
        duration = ProcessMiner._calc_duration_hours(
            "2025-01-01T09:00:00", "2025-01-01T12:00:00"
        )
        assert duration == 3.0

    def test_calc_duration_with_timezone(self) -> None:
        """Zサフィックス付きタイムスタンプ"""
        duration = ProcessMiner._calc_duration_hours(
            "2025-01-01T09:00:00Z", "2025-01-01T12:00:00Z"
        )
        assert duration == 3.0

    def test_calc_duration_invalid(self) -> None:
        """不正なタイムスタンプは0.0を返す"""
        duration = ProcessMiner._calc_duration_hours("invalid", "also-invalid")
        assert duration == 0.0


@pytest.mark.unit
class TestDataclasses:
    """データクラス構造テスト"""

    def test_bottleneck_dataclass(self) -> None:
        """Bottleneckデータクラス"""
        b = Bottleneck(
            source="入力",
            target="承認",
            avg_duration_hours=48.0,
            threshold_hours=24.0,
            severity="high",
            occurrence_count=10,
        )
        assert b.source == "入力"
        assert b.severity == "high"

    def test_process_deviation_dataclass(self) -> None:
        """ProcessDeviationデータクラス"""
        d = ProcessDeviation(
            case_id="C001",
            deviation_type="skip",
            description="テスト",
            severity="high",
            affected_activities=["承認"],
        )
        assert d.case_id == "C001"
        assert d.affected_activities == ["承認"]

    def test_process_mining_result_dataclass(self) -> None:
        """ProcessMiningResultデータクラス"""
        r = ProcessMiningResult(
            total_cases=10,
            total_activities=40,
            unique_activities=4,
            variants=[],
            bottlenecks=[],
            deviations=[],
            conformance_rate=0.9,
        )
        assert r.total_cases == 10
        assert r.edges == []  # default_factory
