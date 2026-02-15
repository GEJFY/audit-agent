"""Forecasts DBモデル テスト"""

import pytest

from src.db.models.forecasts import CrossCompanyPattern, RiskForecast


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestRiskForecast:
    def test_tablename(self) -> None:
        assert RiskForecast.__tablename__ == "risk_forecasts"

    def test_has_required_columns(self) -> None:
        for col in [
            "forecast_period",
            "horizon_days",
            "risk_category",
            "predicted_score",
            "model_type",
        ]:
            assert _has_column(RiskForecast, col), f"Missing column: {col}"

    def test_confidence_interval_defaults(self) -> None:
        assert RiskForecast.__table__.columns["confidence_interval_lower"].default.arg == 0.0
        assert RiskForecast.__table__.columns["confidence_interval_upper"].default.arg == 1.0

    def test_has_project_id_indexed(self) -> None:
        col = RiskForecast.__table__.columns["project_id"]
        assert col.index is True

    def test_has_trend_and_alert(self) -> None:
        assert _has_column(RiskForecast, "trend")
        assert _has_column(RiskForecast, "alert_triggered")


@pytest.mark.unit
class TestCrossCompanyPattern:
    def test_tablename(self) -> None:
        assert CrossCompanyPattern.__tablename__ == "cross_company_patterns"

    def test_has_required_columns(self) -> None:
        for col in ["pattern_type", "industry_code", "region", "sample_size"]:
            assert _has_column(CrossCompanyPattern, col), f"Missing column: {col}"

    def test_default_region(self) -> None:
        assert CrossCompanyPattern.__table__.columns["region"].default.arg == "JP"

    def test_default_sample_size(self) -> None:
        assert CrossCompanyPattern.__table__.columns["sample_size"].default.arg == 0

    def test_default_analysis_version(self) -> None:
        assert CrossCompanyPattern.__table__.columns["analysis_version"].default.arg == "1.0"

    def test_industry_code_indexed(self) -> None:
        col = CrossCompanyPattern.__table__.columns["industry_code"]
        assert col.index is True
