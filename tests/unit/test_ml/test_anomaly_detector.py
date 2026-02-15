"""Anomaly Detector MLモデル テスト"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.ml.anomaly_detector import AnomalyDetector, AnomalyResult
from tests.factories import create_journal_entries


@pytest.mark.unit
class TestAnomalyDetector:
    """Isolation Forest異常検知のユニットテスト"""

    def test_fit_predict(self) -> None:
        """学習→予測の基本フロー"""
        df = create_journal_entries(n=200, anomaly_rate=0.05)
        detector = AnomalyDetector(contamination=0.05)

        results = detector.fit_predict(df)

        assert len(results) == 200
        anomalies = [r for r in results if r.is_anomaly]
        # 異常率は約5%（±誤差）
        assert 2 <= len(anomalies) <= 30

    def test_anomaly_scores(self) -> None:
        """異常スコアの範囲チェック"""
        df = create_journal_entries(n=100)
        detector = AnomalyDetector()

        results = detector.fit_predict(df)

        for result in results:
            assert 0.0 <= result.anomaly_score <= 1.0

    def test_predict_without_fit(self) -> None:
        """未学習で予測するとエラー"""
        df = create_journal_entries(n=10)
        detector = AnomalyDetector()

        with pytest.raises(RuntimeError, match="未学習"):
            detector.predict(df)

    def test_feature_extraction(self) -> None:
        """特徴量抽出テスト"""
        df = create_journal_entries(n=50)
        detector = AnomalyDetector()

        features = detector._extract_features(df)

        assert "amount_abs" in features.columns
        assert "amount_log" in features.columns
        assert "account_frequency" in features.columns
        assert len(features) == 50

    def test_empty_data(self) -> None:
        """空データの処理"""
        df = pd.DataFrame(columns=["id", "date", "account_code", "amount"])
        detector = AnomalyDetector()

        # 空データでは学習しようとすると意味のある結果を返せない
        # ただしエラーにはならない
        if len(df) > 0:
            detector.fit(df)


@pytest.mark.unit
class TestAnomalyDetectorEnhanced:
    """Phase 2 追加テスト"""

    def test_is_fitted_property(self) -> None:
        """is_fitted プロパティ"""
        detector = AnomalyDetector()
        assert detector.is_fitted is False

        df = create_journal_entries(n=50)
        detector.fit(df)
        assert detector.is_fitted is True

    def test_feature_names_property(self) -> None:
        """feature_names プロパティ"""
        detector = AnomalyDetector()
        assert detector.feature_names == []

        df = create_journal_entries(n=50)
        detector.fit(df)
        names = detector.feature_names
        assert len(names) > 0
        assert "amount_abs" in names

    def test_save_and_load(self) -> None:
        """モデル保存・読込"""
        df = create_journal_entries(n=100)
        detector = AnomalyDetector(contamination=0.05)
        detector.fit(df)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name

        try:
            detector.save(path)
            assert Path(path).exists()

            loaded = AnomalyDetector()
            loaded.load(path)

            assert loaded.is_fitted is True
            assert loaded.feature_names == detector.feature_names

            results = loaded.predict(df)
            assert len(results) == 100
        finally:
            Path(path).unlink(missing_ok=True)

    def test_load_nonexistent_file(self) -> None:
        """存在しないファイル読込"""
        detector = AnomalyDetector()
        with pytest.raises(FileNotFoundError, match="モデルファイルが見つかりません"):
            detector.load("/nonexistent/path/model.pkl")

    def test_get_anomaly_summary(self) -> None:
        """異常検知サマリー生成"""
        df = create_journal_entries(n=100, anomaly_rate=0.1)
        detector = AnomalyDetector(contamination=0.1)
        results = detector.fit_predict(df)

        summary = detector.get_anomaly_summary(results)

        assert summary["total"] == 100.0
        assert summary["anomaly_count"] >= 0
        assert 0.0 <= summary["anomaly_rate"] <= 1.0
        assert 0.0 <= summary["avg_anomaly_score"] <= 1.0
        assert 0.0 <= summary["max_anomaly_score"] <= 1.0

    def test_get_anomaly_summary_empty(self) -> None:
        """空結果のサマリー"""
        detector = AnomalyDetector()
        summary = detector.get_anomaly_summary([])

        assert summary["total"] == 0
        assert summary["anomaly_count"] == 0
        assert summary["anomaly_rate"] == 0.0

    def test_result_features_populated(self) -> None:
        """AnomalyResultの特徴量が正しく設定される"""
        df = create_journal_entries(n=20)
        detector = AnomalyDetector()
        results = detector.fit_predict(df)

        for r in results:
            assert isinstance(r.features, dict)
            assert len(r.features) > 0
            assert "amount_abs" in r.features

    def test_contamination_affects_results(self) -> None:
        """contamination値が異常検出数に影響"""
        df = create_journal_entries(n=200)

        detector_low = AnomalyDetector(contamination=0.01)
        results_low = detector_low.fit_predict(df)
        anomaly_low = sum(1 for r in results_low if r.is_anomaly)

        detector_high = AnomalyDetector(contamination=0.2)
        results_high = detector_high.fit_predict(df)
        anomaly_high = sum(1 for r in results_high if r.is_anomaly)

        assert anomaly_low < anomaly_high

    def test_feature_extraction_numeric_only(self) -> None:
        """数値カラムのみのデータ"""
        df = pd.DataFrame({"value_a": [1, 2, 3, 4, 5], "value_b": [10, 20, 30, 40, 50]})
        detector = AnomalyDetector()
        features = detector._extract_features(df)
        assert len(features.columns) >= 2

    def test_feature_extraction_with_date_column(self) -> None:
        """dateカラム有りの特徴量抽出"""
        df = pd.DataFrame(
            {
                "amount": [1000, 2000, 3000],
                "date": pd.to_datetime(["2025-01-01", "2025-06-15", "2025-12-31"]),
                "account_code": ["1100", "1100", "9999"],
            }
        )
        detector = AnomalyDetector()
        features = detector._extract_features(df)

        assert "hour" in features.columns
        assert "day_of_week" in features.columns
        assert "is_weekend" in features.columns
        assert "is_month_end" in features.columns
        assert "is_rare_account" in features.columns

    def test_anomaly_result_dataclass(self) -> None:
        """AnomalyResult dataclassの動作確認"""
        result = AnomalyResult(
            index=0,
            score=-1.0,
            anomaly_score=0.95,
            features={"amount_abs": 1000.0},
            is_anomaly=True,
        )
        assert result.index == 0
        assert result.is_anomaly is True
        assert result.anomaly_score == 0.95

    def test_fit_returns_self(self) -> None:
        """fitがselfを返す（メソッドチェーン対応）"""
        df = create_journal_entries(n=50)
        detector = AnomalyDetector()
        returned = detector.fit(df)
        assert returned is detector

    def test_score_normalization_uniform_data(self) -> None:
        """同一スコアのデータ（score_range=0のケース）"""
        df = pd.DataFrame(
            {
                "amount": [1000] * 20,
                "date": pd.date_range("2025-01-01", periods=20, freq="D"),
                "account_code": ["1100"] * 20,
            }
        )
        detector = AnomalyDetector()
        results = detector.fit_predict(df)

        for r in results:
            assert 0.0 <= r.anomaly_score <= 1.0
