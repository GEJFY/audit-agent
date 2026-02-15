"""リスクスコア算出 — XGBoost + ルールベースハイブリッド"""

import pickle
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


class RiskScorer:
    """XGBoostベースのリスクスコアリング

    リスク要因を総合的に評価して0-100のリスクスコアを算出。
    モデル訓練済み: XGBoost予測 / 未訓練: ルールベースフォールバック。
    """

    FEATURE_NAMES = [
        "amount",
        "amount_z_score",
        "is_anomaly",
        "anomaly_score",
        "approval_deviation",
        "days_since_last_audit",
        "control_deviation_rate",
        "transaction_frequency",
        "is_manual_entry",
        "is_period_end",
        "department_risk_history",
    ]

    def __init__(self, model_path: str | None = None) -> None:
        self._model: Any = None
        self._is_fitted = False

        if model_path and Path(model_path).exists():
            self.load(model_path)

    def _extract_features(self, features: dict[str, Any]) -> np.ndarray:
        """特徴量辞書をベクトルに変換"""
        values = []
        for name in self.FEATURE_NAMES:
            val = features.get(name, 0)
            if isinstance(val, bool):
                val = int(val)
            values.append(float(val))
        return np.array([values])

    def fit(
        self,
        x_data: list[dict[str, Any]],
        y: list[float],
        params: dict[str, Any] | None = None,
    ) -> None:
        """モデル訓練"""
        if not HAS_XGBOOST:
            logger.warning("XGBoost未インストール、ルールベースで動作")
            return

        features_array = np.vstack([self._extract_features(x) for x in x_data])
        labels = np.array(y)

        default_params = {
            "objective": "reg:squarederror",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
        }
        if params:
            default_params.update(params)

        self._model = xgb.XGBRegressor(**default_params)
        self._model.fit(features_array, labels)
        self._is_fitted = True
        logger.info("RiskScorer訓練完了: samples={}", len(x_data))

    def score(self, features: dict[str, Any]) -> float:
        """リスクスコア算出 (0-100)"""
        if self._is_fitted and self._model is not None:
            x_data = self._extract_features(features)
            prediction = float(self._model.predict(x_data)[0])
            return min(100.0, max(0.0, prediction))
        return self._score_rule_based(features)

    def _score_rule_based(self, features: dict[str, Any]) -> float:
        """ルールベースのスコアリング"""
        score = 30.0

        amount = abs(features.get("amount", 0))
        if amount > 100_000_000:
            score += 30
        elif amount > 10_000_000:
            score += 20
        elif amount > 1_000_000:
            score += 10

        z_score = abs(features.get("amount_z_score", 0))
        if z_score > 3:
            score += 15
        elif z_score > 2:
            score += 8

        if features.get("is_anomaly", False):
            anomaly_score = features.get("anomaly_score", 0.5)
            score += 25 * anomaly_score

        if features.get("approval_deviation", False):
            score += 15

        deviation_rate = features.get("control_deviation_rate", 0)
        if deviation_rate > 10:
            score += 15
        elif deviation_rate > 5:
            score += 8

        if features.get("is_manual_entry", False):
            score += 5
        if features.get("is_period_end", False):
            score += 10

        history = features.get("department_risk_history", 0)
        if history > 5:
            score += 10
        elif history > 2:
            score += 5

        return min(100.0, max(0.0, score))

    def batch_score(self, features_list: list[dict[str, Any]]) -> list[float]:
        """バッチスコアリング"""
        if self._is_fitted and self._model is not None and HAS_XGBOOST:
            x_data = np.vstack([self._extract_features(f) for f in features_list])
            predictions = self._model.predict(x_data)
            return [min(100.0, max(0.0, float(p))) for p in predictions]
        return [self._score_rule_based(f) for f in features_list]

    def feature_importance(self) -> dict[str, float]:
        """特徴量重要度"""
        if not self._is_fitted or self._model is None:
            return {}
        importance = self._model.feature_importances_
        return dict(zip(self.FEATURE_NAMES, [float(v) for v in importance], strict=False))

    def save(self, path: str) -> None:
        """モデル保存"""
        with open(path, "wb") as f:
            pickle.dump({"model": self._model, "is_fitted": self._is_fitted}, f)

    def load(self, path: str) -> None:
        """モデル読み込み"""
        with open(path, "rb") as f:
            data = pickle.load(f)  # noqa: S301
        self._model = data["model"]
        self._is_fitted = data["is_fitted"]
