"""予測的リスクモデル — 3ヶ月先リスク確率予測

アンサンブル手法（XGBoost + 時系列 + ルールベース）で
90日先のリスクスコアを予測。業種別重み付け対応。
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class RiskForecastResult:
    """リスク予測結果"""

    risk_category: str
    horizon_days: int
    predicted_score: float  # 0-100
    confidence_interval_lower: float
    confidence_interval_upper: float
    trend: str  # increasing, stable, decreasing
    contributing_factors: list[dict[str, Any]] = field(default_factory=list)
    model_type: str = "ensemble"


@dataclass
class PredictiveRiskReport:
    """予測リスクレポート"""

    tenant_id: str
    forecasts: list[RiskForecastResult] = field(default_factory=list)
    overall_risk_trend: str = "stable"
    high_risk_categories: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── 業種別リスクカテゴリ重み ─────────────────────────────
INDUSTRY_RISK_WEIGHTS: dict[str, dict[str, float]] = {
    "finance": {
        "financial_process": 1.5,
        "access_control": 1.3,
        "compliance": 1.4,
        "it_general": 1.0,
    },
    "manufacturing": {
        "financial_process": 1.2,
        "access_control": 1.0,
        "compliance": 1.1,
        "it_general": 0.9,
    },
    "it_services": {
        "financial_process": 1.0,
        "access_control": 1.5,
        "compliance": 1.2,
        "it_general": 1.4,
    },
}


class PredictiveRiskModel:
    """予測的リスクモデル

    3つのコンポーネントのアンサンブル:
    1. 時系列トレンド予測（移動平均 + 線形回帰）
    2. 特徴量ベーススコアリング（ルールベース / XGBoost）
    3. 季節性パターン（四半期末・年度末の周期性）

    Phase 3: XGBoost/Prophet 未インストール時はルールベースフォールバック
    """

    def __init__(
        self,
        industry: str = "finance",
        ensemble_weights: dict[str, float] | None = None,
    ) -> None:
        self._industry = industry
        self._risk_weights = INDUSTRY_RISK_WEIGHTS.get(industry, {})
        # アンサンブル重み: trend + feature + seasonal
        self._ensemble_weights = ensemble_weights or {
            "trend": 0.4,
            "feature": 0.35,
            "seasonal": 0.25,
        }

    def forecast(
        self,
        historical_scores: list[dict[str, Any]],
        risk_category: str,
        horizon_days: int = 90,
        current_features: dict[str, Any] | None = None,
    ) -> RiskForecastResult:
        """リスクスコア予測

        Args:
            historical_scores: [{"date": "YYYY-MM-DD", "score": float}]
            risk_category: リスクカテゴリ
            horizon_days: 予測ホライゾン（日数）
            current_features: 現在の特徴量（スコアリング用）

        Returns:
            RiskForecastResult
        """
        if not historical_scores or len(historical_scores) < 5:
            return RiskForecastResult(
                risk_category=risk_category,
                horizon_days=horizon_days,
                predicted_score=50.0,
                confidence_interval_lower=30.0,
                confidence_interval_upper=70.0,
                trend="stable",
                model_type="insufficient_data",
            )

        scores = [h["score"] for h in historical_scores]
        dates = [h.get("date", "") for h in historical_scores]

        # 1. 時系列トレンド予測
        trend_score, trend_direction = self._predict_trend(scores, horizon_days)

        # 2. 特徴量ベーススコア
        feature_score = self._predict_feature_based(
            current_features or {}, risk_category
        )

        # 3. 季節性パターン
        seasonal_score = self._predict_seasonal(dates, scores, horizon_days)

        # アンサンブル結合
        w = self._ensemble_weights
        predicted = (
            w["trend"] * trend_score
            + w["feature"] * feature_score
            + w["seasonal"] * seasonal_score
        )
        predicted = min(100.0, max(0.0, predicted))

        # 業種別重み付け
        industry_weight = self._risk_weights.get(risk_category, 1.0)
        predicted = min(100.0, predicted * industry_weight)

        # 信頼区間
        std = float(np.std(scores)) if len(scores) > 1 else 10.0
        uncertainty = std * (1 + horizon_days / 180)  # 期間が長いほど不確実
        ci_lower = max(0.0, predicted - uncertainty)
        ci_upper = min(100.0, predicted + uncertainty)

        # 寄与要因
        factors = self._identify_factors(
            trend_score, feature_score, seasonal_score, current_features
        )

        return RiskForecastResult(
            risk_category=risk_category,
            horizon_days=horizon_days,
            predicted_score=round(predicted, 2),
            confidence_interval_lower=round(ci_lower, 2),
            confidence_interval_upper=round(ci_upper, 2),
            trend=trend_direction,
            contributing_factors=factors,
            model_type="ensemble",
        )

    def forecast_multi_category(
        self,
        category_data: dict[str, list[dict[str, Any]]],
        horizon_days: int = 90,
        current_features: dict[str, Any] | None = None,
    ) -> PredictiveRiskReport:
        """複数カテゴリ一括予測

        Args:
            category_data: {category: [{"date": ..., "score": ...}]}
            horizon_days: 予測ホライゾン

        Returns:
            PredictiveRiskReport
        """
        forecasts: list[RiskForecastResult] = []
        for category, data in category_data.items():
            result = self.forecast(
                data, category, horizon_days, current_features
            )
            forecasts.append(result)

        # 全体トレンド判定
        trends = [f.trend for f in forecasts]
        if trends.count("increasing") > len(trends) / 2:
            overall_trend = "increasing"
        elif trends.count("decreasing") > len(trends) / 2:
            overall_trend = "decreasing"
        else:
            overall_trend = "stable"

        # 高リスクカテゴリ
        high_risk = [
            f.risk_category for f in forecasts if f.predicted_score > 70
        ]

        # 推奨事項
        recommendations = self._generate_recommendations(forecasts)

        return PredictiveRiskReport(
            tenant_id="",
            forecasts=forecasts,
            overall_risk_trend=overall_trend,
            high_risk_categories=high_risk,
            recommendations=recommendations,
        )

    def _predict_trend(
        self, scores: list[float], horizon_days: int
    ) -> tuple[float, str]:
        """時系列トレンド予測"""
        arr = np.array(scores)
        n = len(arr)

        # 線形回帰
        x = np.arange(n)
        coeffs = np.polyfit(x, arr, 1)
        slope = coeffs[0]

        # horizon_days先の予測値
        future_x = n + horizon_days / max(n, 1)
        predicted = float(coeffs[0] * future_x + coeffs[1])
        predicted = min(100.0, max(0.0, predicted))

        # トレンド方向
        if slope > 0.5:
            direction = "increasing"
        elif slope < -0.5:
            direction = "decreasing"
        else:
            direction = "stable"

        return predicted, direction

    def _predict_feature_based(
        self, features: dict[str, Any], risk_category: str
    ) -> float:
        """特徴量ベースのリスクスコア予測"""
        base_score = 40.0

        # 統制逸脱率
        deviation = features.get("control_deviation_rate", 0)
        if deviation > 15:
            base_score += 25
        elif deviation > 5:
            base_score += 15
        elif deviation > 0:
            base_score += 5

        # 異常検知率
        anomaly_rate = features.get("anomaly_rate", 0)
        base_score += min(20.0, anomaly_rate * 100)

        # 過去のインシデント数
        incidents = features.get("past_incidents", 0)
        base_score += min(15.0, incidents * 3.0)

        # カテゴリ別調整
        if risk_category == "access_control" and features.get(
            "privileged_access_count", 0
        ) > 10:
            base_score += 10

        return min(100.0, max(0.0, base_score))

    def _predict_seasonal(
        self,
        dates: list[str],
        scores: list[float],
        horizon_days: int,
    ) -> float:
        """季節性パターン予測"""
        if not dates or not dates[0]:
            return float(np.mean(scores)) if scores else 50.0

        try:
            parsed_dates = pd.to_datetime(dates)
            months = parsed_dates.month.to_list()
        except Exception:
            return float(np.mean(scores)) if scores else 50.0

        # 月別平均スコア
        monthly_avg: dict[int, list[float]] = {}
        for month, score in zip(months, scores, strict=False):
            monthly_avg.setdefault(month, []).append(score)

        # 予測月のスコアを推定
        target_date = pd.Timestamp.now() + pd.Timedelta(days=horizon_days)
        target_month = target_date.month

        if target_month in monthly_avg:
            return float(np.mean(monthly_avg[target_month]))

        # 同月データがない場合は全体平均
        return float(np.mean(scores))

    def _identify_factors(
        self,
        trend_score: float,
        feature_score: float,
        seasonal_score: float,
        features: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """寄与要因を特定"""
        factors: list[dict[str, Any]] = []

        if trend_score > 60:
            factors.append({
                "factor": "上昇トレンド",
                "contribution": "high",
                "description": "過去データに上昇傾向",
            })

        if feature_score > 60:
            factors.append({
                "factor": "現在のリスク指標",
                "contribution": "high",
                "description": "統制逸脱・異常検知等の現在指標が高い",
            })

        if seasonal_score > 60:
            factors.append({
                "factor": "季節性パターン",
                "contribution": "medium",
                "description": "過去同月のリスクスコアが高い傾向",
            })

        if features:
            if features.get("control_deviation_rate", 0) > 10:
                factors.append({
                    "factor": "統制逸脱率",
                    "contribution": "high",
                    "description": f"逸脱率 {features['control_deviation_rate']}%",
                })
            if features.get("anomaly_rate", 0) > 0.1:
                factors.append({
                    "factor": "異常検知率",
                    "contribution": "medium",
                    "description": f"異常率 {features['anomaly_rate']:.1%}",
                })

        return factors

    def _generate_recommendations(
        self, forecasts: list[RiskForecastResult]
    ) -> list[str]:
        """予測結果から推奨事項を生成"""
        recs: list[str] = []

        for f in forecasts:
            if f.predicted_score > 80:
                recs.append(
                    f"[緊急] {f.risk_category}: 予測スコア {f.predicted_score:.0f} — "
                    "即座の統制強化が必要"
                )
            elif f.predicted_score > 60 and f.trend == "increasing":
                recs.append(
                    f"[注意] {f.risk_category}: 上昇トレンド — "
                    "モニタリング頻度の増加を推奨"
                )

        if not recs:
            recs.append("全カテゴリのリスクスコアが安定しています")

        return recs

    @property
    def industry(self) -> str:
        return self._industry

    @property
    def ensemble_weights(self) -> dict[str, float]:
        return self._ensemble_weights
