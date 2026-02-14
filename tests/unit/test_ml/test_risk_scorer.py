"""Risk Scorer テスト"""

import pytest
from typing import Any

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
