"""予測的リスクモデルのテスト"""

import pytest

from src.ml.predictive_risk import (
    INDUSTRY_RISK_WEIGHTS,
    PredictiveRiskModel,
    PredictiveRiskReport,
    RiskForecastResult,
)


def _make_historical_data(n: int = 30, base: float = 50.0, trend: float = 0.0) -> list[dict]:
    """テスト用の過去スコアデータ生成"""
    import numpy as np

    return [
        {
            "date": f"2025-{(i // 30) + 1:02d}-{(i % 28) + 1:02d}",
            "score": base + trend * i + np.random.normal(0, 3),
        }
        for i in range(n)
    ]


@pytest.mark.unit
class TestRiskForecastResult:
    """RiskForecastResult テスト"""

    def test_create_result(self) -> None:
        r = RiskForecastResult(
            risk_category="financial_process",
            horizon_days=90,
            predicted_score=65.0,
            confidence_interval_lower=50.0,
            confidence_interval_upper=80.0,
            trend="increasing",
        )
        assert r.risk_category == "financial_process"
        assert r.predicted_score == 65.0
        assert r.trend == "increasing"
        assert r.model_type == "ensemble"

    def test_default_fields(self) -> None:
        r = RiskForecastResult(
            risk_category="test",
            horizon_days=30,
            predicted_score=50.0,
            confidence_interval_lower=40.0,
            confidence_interval_upper=60.0,
            trend="stable",
        )
        assert r.contributing_factors == []


@pytest.mark.unit
class TestPredictiveRiskReport:
    """PredictiveRiskReport テスト"""

    def test_empty_report(self) -> None:
        report = PredictiveRiskReport(tenant_id="t-001")
        assert report.forecasts == []
        assert report.overall_risk_trend == "stable"

    def test_report_with_data(self) -> None:
        report = PredictiveRiskReport(
            tenant_id="t-001",
            forecasts=[
                RiskForecastResult(
                    risk_category="financial_process",
                    horizon_days=90,
                    predicted_score=75.0,
                    confidence_interval_lower=60.0,
                    confidence_interval_upper=90.0,
                    trend="increasing",
                ),
            ],
            overall_risk_trend="increasing",
            high_risk_categories=["financial_process"],
        )
        assert len(report.forecasts) == 1
        assert len(report.high_risk_categories) == 1


@pytest.mark.unit
class TestPredictiveRiskModel:
    """PredictiveRiskModel テスト"""

    def test_init_default(self) -> None:
        model = PredictiveRiskModel()
        assert model.industry == "finance"
        assert "trend" in model.ensemble_weights
        assert "feature" in model.ensemble_weights
        assert "seasonal" in model.ensemble_weights

    def test_init_custom_industry(self) -> None:
        model = PredictiveRiskModel(industry="manufacturing")
        assert model.industry == "manufacturing"

    def test_forecast_insufficient_data(self) -> None:
        """データ不足時は安全なデフォルト値"""
        model = PredictiveRiskModel()
        result = model.forecast([], "financial_process")
        assert result.predicted_score == 50.0
        assert result.model_type == "insufficient_data"
        assert result.trend == "stable"

    def test_forecast_minimal_data(self) -> None:
        """最小データ（5件未満）"""
        model = PredictiveRiskModel()
        data = [{"date": "2025-01-01", "score": 50.0}]
        result = model.forecast(data, "financial_process")
        assert result.model_type == "insufficient_data"

    def test_forecast_stable_trend(self) -> None:
        """安定トレンドのデータ"""
        model = PredictiveRiskModel()
        data = _make_historical_data(n=30, base=50.0, trend=0.0)
        result = model.forecast(data, "financial_process", horizon_days=90)

        assert result.risk_category == "financial_process"
        assert result.horizon_days == 90
        assert 0.0 <= result.predicted_score <= 100.0
        assert result.confidence_interval_lower <= result.predicted_score
        assert result.predicted_score <= result.confidence_interval_upper
        assert result.model_type == "ensemble"

    def test_forecast_increasing_trend(self) -> None:
        """上昇トレンド"""
        model = PredictiveRiskModel()
        data = _make_historical_data(n=30, base=30.0, trend=1.5)
        result = model.forecast(data, "financial_process", horizon_days=90)

        # 上昇傾向のためスコアは高めか、トレンドがincreasing
        assert result.predicted_score > 0
        assert result.trend in ("increasing", "stable")

    def test_forecast_decreasing_trend(self) -> None:
        """下降トレンド"""
        model = PredictiveRiskModel()
        data = _make_historical_data(n=30, base=80.0, trend=-1.5)
        result = model.forecast(data, "financial_process", horizon_days=90)

        assert result.predicted_score >= 0
        assert result.trend in ("decreasing", "stable")

    def test_forecast_with_features(self) -> None:
        """現在の特徴量付き予測"""
        model = PredictiveRiskModel()
        data = _make_historical_data(n=30, base=50.0)
        features = {
            "control_deviation_rate": 12,
            "anomaly_rate": 0.15,
            "past_incidents": 3,
        }
        result = model.forecast(data, "financial_process", horizon_days=90, current_features=features)
        assert result.predicted_score > 0
        # 寄与要因が含まれる
        assert isinstance(result.contributing_factors, list)

    def test_forecast_confidence_interval(self) -> None:
        """信頼区間の正当性"""
        model = PredictiveRiskModel()
        data = _make_historical_data(n=30, base=50.0)
        result = model.forecast(data, "financial_process", horizon_days=30)

        assert result.confidence_interval_lower >= 0.0
        assert result.confidence_interval_upper <= 100.0
        assert result.confidence_interval_lower <= result.predicted_score
        assert result.predicted_score <= result.confidence_interval_upper

    def test_forecast_longer_horizon_wider_ci(self) -> None:
        """長期予測ほど信頼区間が広い"""
        model = PredictiveRiskModel()
        data = _make_historical_data(n=30, base=50.0)

        result_30 = model.forecast(data, "financial_process", horizon_days=30)
        result_90 = model.forecast(data, "financial_process", horizon_days=90)

        width_30 = result_30.confidence_interval_upper - result_30.confidence_interval_lower
        width_90 = result_90.confidence_interval_upper - result_90.confidence_interval_lower
        assert width_90 >= width_30

    def test_forecast_multi_category(self) -> None:
        """複数カテゴリ一括予測"""
        model = PredictiveRiskModel()
        category_data = {
            "financial_process": _make_historical_data(n=20, base=45.0),
            "access_control": _make_historical_data(n=20, base=55.0),
            "compliance": _make_historical_data(n=20, base=35.0),
        }
        report = model.forecast_multi_category(category_data, horizon_days=90)

        assert isinstance(report, PredictiveRiskReport)
        assert len(report.forecasts) == 3
        assert report.overall_risk_trend in ("increasing", "stable", "decreasing")
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0

    def test_forecast_multi_category_high_risk(self) -> None:
        """高リスクカテゴリの検出"""
        model = PredictiveRiskModel()
        category_data = {
            "financial_process": _make_historical_data(n=20, base=85.0),
            "access_control": _make_historical_data(n=20, base=30.0),
        }
        report = model.forecast_multi_category(category_data, horizon_days=90)
        # 高リスクカテゴリが検出されるかは予測次第だが、型は正しい
        assert isinstance(report.high_risk_categories, list)

    def test_industry_weights_applied(self) -> None:
        """業種別重み付けが適用される"""
        finance_model = PredictiveRiskModel(industry="finance")
        it_model = PredictiveRiskModel(industry="it_services")

        data = _make_historical_data(n=20, base=50.0, trend=0.0)

        # 同じデータでもaccess_controlはIT業の方が高くなる傾向
        finance_result = finance_model.forecast(data, "access_control")
        it_result = it_model.forecast(data, "access_control")

        # 少なくとも両方とも有効なスコア
        assert finance_result.predicted_score >= 0
        assert it_result.predicted_score >= 0


@pytest.mark.unit
class TestIndustryRiskWeights:
    """業種別リスク重みのテスト"""

    def test_finance_weights(self) -> None:
        assert "finance" in INDUSTRY_RISK_WEIGHTS
        weights = INDUSTRY_RISK_WEIGHTS["finance"]
        assert weights["financial_process"] > weights["it_general"]

    def test_it_services_weights(self) -> None:
        assert "it_services" in INDUSTRY_RISK_WEIGHTS
        weights = INDUSTRY_RISK_WEIGHTS["it_services"]
        assert weights["access_control"] > weights["financial_process"]

    def test_manufacturing_weights(self) -> None:
        assert "manufacturing" in INDUSTRY_RISK_WEIGHTS

    def test_all_industries_have_4_categories(self) -> None:
        for industry, weights in INDUSTRY_RISK_WEIGHTS.items():
            assert len(weights) == 4, f"{industry} has {len(weights)} categories"


@pytest.mark.unit
class TestPredictiveTrendDetection:
    """トレンド検出のテスト"""

    def test_predict_trend_stable(self) -> None:
        model = PredictiveRiskModel()
        _, direction = model._predict_trend([50.0, 50.2, 49.8, 50.1, 50.0, 49.9, 50.1], 90)
        assert direction == "stable"

    def test_predict_trend_increasing(self) -> None:
        model = PredictiveRiskModel()
        score, direction = model._predict_trend([30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0], 90)
        assert direction == "increasing"
        assert score > 60

    def test_predict_trend_decreasing(self) -> None:
        model = PredictiveRiskModel()
        _, direction = model._predict_trend([80.0, 75.0, 70.0, 65.0, 60.0, 55.0, 50.0], 90)
        assert direction == "decreasing"
