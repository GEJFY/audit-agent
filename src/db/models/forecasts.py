"""予測・クロス企業分析モデル — 2テーブル"""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import TenantBaseModel


class RiskForecast(TenantBaseModel):
    """リスク予測結果 — 3ヶ月先予測

    予測的リスクモデルが生成する将来リスクスコア。
    週次バッチで更新し、CFO/CLOダッシュボードに表示。
    """

    __tablename__ = "risk_forecasts"

    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    forecast_period: Mapped[str] = mapped_column(String(20), nullable=False)  # 2026-Q2, 2026-M04
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)  # 30, 60, 90
    risk_category: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_lower: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_interval_upper: Mapped[float] = mapped_column(Float, default=1.0)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ensemble, xgboost, prophet, arima
    feature_importance: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    contributing_factors: Mapped[list | None] = mapped_column(JSONB, default=list)  # 寄与要因リスト
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)  # increasing, stable, decreasing
    alert_triggered: Mapped[str | None] = mapped_column(String(20), nullable=True)  # high, medium, none
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)


class CrossCompanyPattern(TenantBaseModel):
    """クロス企業パターン — マルチ企業分析結果

    複数企業間の異常相関・業種ベンチマーク結果を保存。
    ポートフォリオリスク集約の基盤データ。
    """

    __tablename__ = "cross_company_patterns"

    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)  # anomaly_correlation, benchmark, trend
    industry_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(20), default="JP")
    source_tenant_ids: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)  # 匿名化ID
    pattern_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)  # パターン詳細
    benchmark_scores: Mapped[dict | None] = mapped_column(JSONB, default=dict)  # 業種ベンチマークスコア
    risk_correlation: Mapped[dict | None] = mapped_column(JSONB, default=dict)  # リスク相関マトリクス
    sample_size: Mapped[int] = mapped_column(Integer, default=0)  # 対象企業数
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_version: Mapped[str] = mapped_column(String(20), default="1.0")
