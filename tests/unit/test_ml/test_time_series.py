"""Time Series Analyzer テスト"""

import pytest

from src.ml.time_series import TimeSeriesAnalyzer
from tests.factories import create_time_series


@pytest.mark.unit
class TestTimeSeriesAnalyzer:
    """時系列分析のユニットテスト"""

    async def test_detect_anomaly_trend(self, sample_time_series_data: list[float]) -> None:
        """異常トレンド検出基本テスト"""
        analyzer = TimeSeriesAnalyzer()

        result = await analyzer.detect_anomaly_trend(
            series_data=sample_time_series_data,
            period="daily",
        )

        assert "trend" in result
        assert "seasonality" in result
        assert "anomaly_probability" in result
        assert "anomalies" in result
        assert "forecast" in result
        assert isinstance(result["anomalies"], list)
        assert isinstance(result["forecast"], list)

    async def test_detect_anomaly_short_data(self) -> None:
        """短いデータ（10未満）での分析"""
        analyzer = TimeSeriesAnalyzer()

        result = await analyzer.detect_anomaly_trend(
            series_data=[1.0, 2.0, 3.0],
            period="daily",
        )

        # 10未満はデフォルト値を返す
        assert result["trend"] == 0.0
        assert result["anomaly_probability"] == 0.0
        assert result["anomalies"] == []

    async def test_detect_anomaly_with_timestamps(self) -> None:
        """タイムスタンプ指定での分析"""
        values, timestamps = create_time_series(n=30)
        analyzer = TimeSeriesAnalyzer()

        result = await analyzer.detect_anomaly_trend(
            series_data=values,
            timestamps=timestamps,
            period="daily",
        )

        assert "trend" in result
        assert len(result["forecast"]) > 0

    async def test_statsmodels_fallback(self) -> None:
        """statsmodelsフォールバックでの分析"""
        values, _ = create_time_series(n=50, trend=1.0, noise_level=5.0)
        analyzer = TimeSeriesAnalyzer()

        # statsmodelsフォールバック（Prophet未インストール環境）
        import pandas as pd

        dates = pd.date_range("2025-01-01", periods=50, freq="D")
        df = pd.DataFrame({"ds": dates, "y": values})

        result = analyzer._analyze_statsmodels(df)

        assert "trend" in result
        assert "seasonality" in result
        assert len(result["forecast"]) == 30
        for f in result["forecast"]:
            assert "date" in f
            assert "predicted" in f
            assert "lower" in f
            assert "upper" in f
            assert f["lower"] < f["upper"]

    async def test_forecast_kpi(self) -> None:
        """KPI予測テスト"""
        analyzer = TimeSeriesAnalyzer()
        historical = [{"date": f"2025-01-{i + 1:02d}", "value": 100 + i * 2.0} for i in range(30)]

        forecast = await analyzer.forecast_kpi(historical, periods=10)

        assert len(forecast) == 10
        for point in forecast:
            assert "date" in point
            assert "predicted" in point

    async def test_forecast_kpi_empty(self) -> None:
        """空データでのKPI予測"""
        analyzer = TimeSeriesAnalyzer()
        forecast = await analyzer.forecast_kpi([], periods=10)
        assert forecast == []

    async def test_anomaly_probability_range(self) -> None:
        """異常確率が0-1の範囲内"""
        values, timestamps = create_time_series(n=50, noise_level=10.0)
        analyzer = TimeSeriesAnalyzer()

        result = await analyzer.detect_anomaly_trend(
            series_data=values,
            timestamps=timestamps,
        )

        assert 0.0 <= result["anomaly_probability"] <= 1.0
