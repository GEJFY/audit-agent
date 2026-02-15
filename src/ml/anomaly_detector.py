"""異常検知MLモデル — Isolation Forest (Phase 0 MVP)"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class AnomalyResult:
    """異常検知結果"""

    index: int
    score: float  # -1=異常, 1=正常 (sklearn convention)
    anomaly_score: float  # 0-1 (正規化。1=最も異常)
    features: dict[str, float] = field(default_factory=dict)
    is_anomaly: bool = False


class AnomalyDetector:
    """Isolation Forest による統計的異常検知

    仕訳データの以下の特徴量で異常を検出:
    - 金額（絶対値、対数スケール）
    - 仕訳時刻（営業時間外フラグ）
    - 勘定科目の使用頻度（レア科目の検出）
    - 相手勘定の異常な組み合わせ
    - 期末集中度
    """

    def __init__(
        self,
        contamination: float = 0.05,  # 異常率の事前推定
        n_estimators: int = 200,
        random_state: int = 42,
    ) -> None:
        self._model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        self._scaler = StandardScaler()
        self._is_fitted = False
        self._feature_names: list[str] = []

    def fit(self, data: pd.DataFrame) -> "AnomalyDetector":
        """モデル学習"""
        features = self._extract_features(data)
        self._feature_names = list(features.columns)

        scaled = self._scaler.fit_transform(features)
        self._model.fit(scaled)
        self._is_fitted = True

        logger.info(
            "異常検知モデル学習完了",
            n_samples=len(data),
            n_features=len(self._feature_names),
        )
        return self

    def predict(self, data: pd.DataFrame) -> list[AnomalyResult]:
        """異常検知を実行"""
        if not self._is_fitted:
            raise RuntimeError("モデルが未学習。先にfit()を実行してください。")

        features = self._extract_features(data)
        scaled = self._scaler.transform(features)

        # 予測
        predictions = self._model.predict(scaled)  # -1=anomaly, 1=normal
        scores = self._model.decision_function(scaled)  # 低い=より異常

        # スコア正規化 (0-1, 1=最も異常)
        min_score = scores.min()
        max_score = scores.max()
        score_range = max_score - min_score if max_score != min_score else 1.0
        normalized_scores = 1 - (scores - min_score) / score_range

        results: list[AnomalyResult] = []
        for i in range(len(data)):
            result = AnomalyResult(
                index=i,
                score=float(predictions[i]),
                anomaly_score=float(normalized_scores[i]),
                features={name: float(features.iloc[i][name]) for name in self._feature_names},
                is_anomaly=predictions[i] == -1,
            )
            results.append(result)

        anomaly_count = sum(1 for r in results if r.is_anomaly)
        logger.info(
            f"異常検知完了: {anomaly_count}/{len(results)}件が異常",
            anomaly_rate=round(anomaly_count / max(len(results), 1) * 100, 1),
        )

        return results

    def fit_predict(self, data: pd.DataFrame) -> list[AnomalyResult]:
        """学習と検知を一括実行"""
        self.fit(data)
        return self.predict(data)

    def _extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """仕訳データから特徴量を抽出"""
        features = pd.DataFrame()

        # 金額関連
        if "amount" in data.columns:
            features["amount_abs"] = data["amount"].abs()
            features["amount_log"] = np.log1p(data["amount"].abs())

        # 時刻関連
        if "timestamp" in data.columns or "date" in data.columns:
            date_col = "timestamp" if "timestamp" in data.columns else "date"
            dates = pd.to_datetime(data[date_col], errors="coerce")
            features["hour"] = dates.dt.hour.fillna(12)
            features["day_of_week"] = dates.dt.dayofweek.fillna(0)
            features["is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
            features["is_month_end"] = (dates.dt.day >= 25).astype(int)
            features["month"] = dates.dt.month.fillna(6)

        # 勘定科目関連
        if "account_code" in data.columns:
            account_freq = data["account_code"].value_counts(normalize=True)
            features["account_frequency"] = data["account_code"].map(account_freq).fillna(0)
            features["is_rare_account"] = (features["account_frequency"] < 0.01).astype(int)

        # デフォルト特徴量（データが不足時）
        if features.empty:
            for col in data.select_dtypes(include=[np.number]).columns:
                features[col] = data[col].fillna(0)

        return features.fillna(0)
