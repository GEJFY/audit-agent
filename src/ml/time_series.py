"""時系列分析 — Prophet + statsmodels"""

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

try:
    from prophet import Prophet

    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False


class TimeSeriesAnalyzer:
    """Prophetベースの時系列分析

    KPI急変検知、トレンド分析、予測的リスク評価。
    Prophet未インストール時はstatsmodelsフォールバック。
    """

    def __init__(self, interval_width: float = 0.95) -> None:
        self._interval_width = interval_width

    async def detect_anomaly_trend(
        self,
        series_data: list[float],
        timestamps: list[str] | None = None,
        period: str = "daily",
    ) -> dict[str, Any]:
        """時系列異常トレンド検出

        Args:
            series_data: 数値データ系列
            timestamps: ISO8601タイムスタンプ（省略時は自動生成）
            period: データ粒度 (daily, weekly, monthly)

        Returns:
            trend, seasonality, anomaly_probability, anomalies, forecast
        """
        if len(series_data) < 10:
            return {
                "trend": 0.0,
                "seasonality": 0.0,
                "anomaly_probability": 0.0,
                "anomalies": [],
                "forecast": [],
            }

        # DataFrameを構成
        if timestamps:
            dates = pd.to_datetime(timestamps)
        else:
            freq_map = {"daily": "D", "weekly": "W", "monthly": "MS"}
            freq = freq_map.get(period, "D")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=len(series_data), freq=freq)

        df = pd.DataFrame({"ds": dates, "y": series_data})

        if HAS_PROPHET:
            return await self._analyze_prophet(df)
        return self._analyze_statsmodels(df)

    async def _analyze_prophet(self, df: pd.DataFrame) -> dict[str, Any]:
        """Prophetによる分析"""
        model = Prophet(
            interval_width=self._interval_width,
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05,
        )
        model.fit(df)

        # 将来30期間の予測
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)

        # トレンド成分の抽出
        trend_values = forecast["trend"].values
        trend_direction = float(trend_values[-1] - trend_values[0]) / max(
            abs(trend_values[0]), 1.0
        )

        # 季節性の大きさ
        if "weekly" in forecast.columns:
            seasonality_magnitude = float(forecast["weekly"].std())
        else:
            seasonality_magnitude = 0.0

        # 異常検知: 実測値が信頼区間外
        merged = forecast[: len(df)].copy()
        merged["actual"] = df["y"].values
        anomalies: list[dict[str, Any]] = []

        for idx, row in merged.iterrows():
            actual = row["actual"]
            if actual < row["yhat_lower"] or actual > row["yhat_upper"]:
                anomalies.append({
                    "index": int(idx),
                    "date": str(row["ds"]),
                    "actual": float(actual),
                    "expected": float(row["yhat"]),
                    "lower": float(row["yhat_lower"]),
                    "upper": float(row["yhat_upper"]),
                    "deviation": float(actual - row["yhat"]),
                })

        anomaly_probability = len(anomalies) / max(len(df), 1)

        # 将来予測
        future_forecast = [
            {
                "date": str(row["ds"]),
                "predicted": float(row["yhat"]),
                "lower": float(row["yhat_lower"]),
                "upper": float(row["yhat_upper"]),
            }
            for _, row in forecast[len(df) :].iterrows()
        ]

        logger.info(
            "Prophet分析完了: anomalies={}, trend={:.3f}",
            len(anomalies),
            trend_direction,
        )

        return {
            "trend": trend_direction,
            "seasonality": seasonality_magnitude,
            "anomaly_probability": anomaly_probability,
            "anomalies": anomalies,
            "forecast": future_forecast,
        }

    def _analyze_statsmodels(self, df: pd.DataFrame) -> dict[str, Any]:
        """statsmodelsフォールバック — 移動平均ベース"""
        values = df["y"].values
        n = len(values)

        # 移動平均 (window=7 or データ長の1/4)
        window = min(7, max(3, n // 4))
        ma = pd.Series(values).rolling(window=window, center=True).mean().fillna(method="bfill").fillna(method="ffill")

        # トレンド: 線形回帰
        x = np.arange(n)
        coeffs = np.polyfit(x, values, 1)
        trend_direction = float(coeffs[0] * n) / max(abs(values.mean()), 1.0)

        # 残差ベースの異常検知
        residuals = values - ma.values
        std = float(np.std(residuals))
        mean = float(np.mean(residuals))

        anomalies: list[dict[str, Any]] = []
        for i, (val, res) in enumerate(zip(values, residuals)):
            z = abs(res - mean) / max(std, 1e-10)
            if z > 2.5:
                anomalies.append({
                    "index": i,
                    "date": str(df["ds"].iloc[i]),
                    "actual": float(val),
                    "expected": float(ma.values[i]),
                    "deviation": float(res),
                    "z_score": float(z),
                })

        anomaly_probability = len(anomalies) / max(n, 1)

        # 簡易予測（線形トレンド延長）
        forecast: list[dict[str, Any]] = []
        for i in range(30):
            pred = float(coeffs[0] * (n + i) + coeffs[1])
            forecast.append({
                "date": str(df["ds"].iloc[-1] + pd.Timedelta(days=i + 1)),
                "predicted": pred,
                "lower": pred - 2 * std,
                "upper": pred + 2 * std,
            })

        return {
            "trend": trend_direction,
            "seasonality": float(std),
            "anomaly_probability": anomaly_probability,
            "anomalies": anomalies,
            "forecast": forecast,
        }

    async def forecast_kpi(
        self,
        historical_data: list[dict[str, Any]],
        periods: int = 30,
    ) -> list[dict[str, Any]]:
        """KPI予測

        Args:
            historical_data: [{"date": "YYYY-MM-DD", "value": float}]
            periods: 予測期間数
        """
        if not historical_data:
            return []

        df = pd.DataFrame(historical_data)
        df.columns = ["ds", "y"]
        df["ds"] = pd.to_datetime(df["ds"])

        if HAS_PROPHET:
            model = Prophet(interval_width=self._interval_width)
            model.fit(df)
            future = model.make_future_dataframe(periods=periods)
            forecast = model.predict(future)

            return [
                {
                    "date": str(row["ds"].date()),
                    "predicted": float(row["yhat"]),
                    "lower": float(row["yhat_lower"]),
                    "upper": float(row["yhat_upper"]),
                }
                for _, row in forecast[len(df) :].iterrows()
            ]

        # フォールバック: 線形予測
        values = df["y"].values
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        std = float(np.std(values))

        return [
            {
                "date": str((df["ds"].iloc[-1] + pd.Timedelta(days=i + 1)).date()),
                "predicted": float(coeffs[0] * (len(values) + i) + coeffs[1]),
                "lower": float(coeffs[0] * (len(values) + i) + coeffs[1] - 2 * std),
                "upper": float(coeffs[0] * (len(values) + i) + coeffs[1] + 2 * std),
            }
            for i in range(periods)
        ]
