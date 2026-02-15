"""Risk Scorer テスト"""

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.ml.risk_scorer import RiskScorer
from tests.factories import create_risk_features


@pytest.mark.unit
class TestRiskScorer:
    """XGBoostリスクスコアリングのユニットテスト"""

    def test_rule_based_score(self) -> None:
        """ルールベーススコアリング基本テスト"""
        scorer = RiskScorer()
        features = create_risk_features()

        score = scorer.score(features)

        assert 0.0 <= score <= 100.0

    def test_rule_based_high_risk(self, sample_risk_features: dict[str, Any]) -> None:
        """高リスク特徴量のスコアリング"""
        scorer = RiskScorer()
        score = scorer.score(sample_risk_features)

        # 高リスク: amount=50M, z_score=3.5, anomaly=True等
        assert score >= 50.0

    def test_rule_based_low_risk(self) -> None:
        """低リスク特徴量のスコアリング"""
        scorer = RiskScorer()
        features = create_risk_features(
            amount=10_000,
            is_anomaly=False,
            anomaly_score=0.1,
        )

        score = scorer.score(features)
        assert score < 60.0  # 低リスク

    def test_rule_based_amount_thresholds(self) -> None:
        """金額閾値ごとのスコア差"""
        scorer = RiskScorer()

        score_low = scorer.score(create_risk_features(amount=500_000))
        score_mid = scorer.score(create_risk_features(amount=5_000_000))
        score_high = scorer.score(create_risk_features(amount=50_000_000))
        score_very_high = scorer.score(create_risk_features(amount=500_000_000))

        assert score_low < score_mid
        assert score_mid < score_high
        assert score_high < score_very_high

    def test_batch_score(self) -> None:
        """バッチスコアリング"""
        scorer = RiskScorer()
        features_list = [
            create_risk_features(amount=100_000),
            create_risk_features(amount=50_000_000, is_anomaly=True),
            create_risk_features(amount=1_000),
        ]

        scores = scorer.batch_score(features_list)

        assert len(scores) == 3
        assert all(0.0 <= s <= 100.0 for s in scores)

    def test_feature_extraction(self) -> None:
        """特徴量抽出テスト"""
        scorer = RiskScorer()
        features = create_risk_features()

        vector = scorer._extract_features(features)

        assert vector.shape == (1, len(RiskScorer.FEATURE_NAMES))

    def test_feature_importance_unfitted(self) -> None:
        """未訓練モデルの特徴量重要度は空"""
        scorer = RiskScorer()
        importance = scorer.feature_importance()
        assert importance == {}

    def test_score_bounds(self) -> None:
        """スコアが0-100の範囲内"""
        scorer = RiskScorer()

        # 極端な値
        extreme = {
            "amount": 999_999_999_999,
            "amount_z_score": 100.0,
            "is_anomaly": True,
            "anomaly_score": 1.0,
            "approval_deviation": True,
            "days_since_last_audit": 1000,
            "control_deviation_rate": 100.0,
            "transaction_frequency": 1000,
            "is_manual_entry": True,
            "is_period_end": True,
            "department_risk_history": 100,
        }

        score = scorer.score(extreme)
        assert score <= 100.0

        # 最小値
        minimal = create_risk_features(amount=0)
        score_min = scorer.score(minimal)
        assert score_min >= 0.0


@pytest.mark.unit
class TestRiskScorerEnhanced:
    """Phase 2 追加テスト"""

    def test_anomaly_score_impact(self) -> None:
        """異常スコアの影響確認"""
        scorer = RiskScorer()

        no_anomaly = create_risk_features(is_anomaly=False, anomaly_score=0.0)
        high_anomaly = create_risk_features(is_anomaly=True, anomaly_score=0.9)

        score_no = scorer.score(no_anomaly)
        score_high = scorer.score(high_anomaly)

        assert score_high > score_no

    def test_z_score_thresholds(self) -> None:
        """Z-score閾値ごとのスコア差"""
        scorer = RiskScorer()

        features_z1 = create_risk_features()
        features_z1["amount_z_score"] = 1.0
        features_z2 = create_risk_features()
        features_z2["amount_z_score"] = 2.5
        features_z3 = create_risk_features()
        features_z3["amount_z_score"] = 4.0

        score_z1 = scorer.score(features_z1)
        score_z2 = scorer.score(features_z2)
        score_z3 = scorer.score(features_z3)

        assert score_z1 < score_z2
        assert score_z2 < score_z3

    def test_manual_entry_adds_risk(self) -> None:
        """手入力エントリーはリスク加算"""
        scorer = RiskScorer()

        auto = create_risk_features()
        auto["is_manual_entry"] = False
        manual = create_risk_features()
        manual["is_manual_entry"] = True

        assert scorer.score(manual) > scorer.score(auto)

    def test_period_end_adds_risk(self) -> None:
        """期末はリスク加算"""
        scorer = RiskScorer()

        normal = create_risk_features()
        normal["is_period_end"] = False
        period_end = create_risk_features()
        period_end["is_period_end"] = True

        assert scorer.score(period_end) > scorer.score(normal)

    def test_department_risk_history(self) -> None:
        """部門リスク履歴の影響"""
        scorer = RiskScorer()

        low_history = create_risk_features()
        low_history["department_risk_history"] = 0
        high_history = create_risk_features()
        high_history["department_risk_history"] = 10

        assert scorer.score(high_history) > scorer.score(low_history)

    def test_control_deviation_rate(self) -> None:
        """統制逸脱率の影響"""
        scorer = RiskScorer()

        low_dev = create_risk_features()
        low_dev["control_deviation_rate"] = 1.0
        high_dev = create_risk_features()
        high_dev["control_deviation_rate"] = 15.0

        assert scorer.score(high_dev) > scorer.score(low_dev)

    def test_missing_features_default_to_zero(self) -> None:
        """欠損特徴量は0にデフォルト"""
        scorer = RiskScorer()
        features: dict[str, Any] = {"amount": 1_000_000}

        score = scorer.score(features)
        assert 0.0 <= score <= 100.0

    def test_bool_features_converted(self) -> None:
        """bool特徴量がintに変換される"""
        scorer = RiskScorer()
        features = create_risk_features()
        features["is_anomaly"] = True
        features["is_manual_entry"] = True

        vector = scorer._extract_features(features)
        assert vector.shape == (1, len(RiskScorer.FEATURE_NAMES))

    def test_save_and_load(self) -> None:
        """モデル保存・読込"""
        scorer = RiskScorer()

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name

        try:
            scorer.save(path)
            assert Path(path).exists()

            loaded = RiskScorer(model_path=path)
            score = loaded.score(create_risk_features())
            assert 0.0 <= score <= 100.0
        finally:
            Path(path).unlink(missing_ok=True)

    def test_batch_score_consistency(self) -> None:
        """バッチと個別スコアの一致"""
        scorer = RiskScorer()
        features_list = [
            create_risk_features(amount=100_000),
            create_risk_features(amount=10_000_000),
        ]

        batch_scores = scorer.batch_score(features_list)
        individual_scores = [scorer.score(f) for f in features_list]

        for batch, individual in zip(batch_scores, individual_scores, strict=True):
            assert abs(batch - individual) < 0.01
