"""業種別リスクテンプレートモデル — 3テーブル"""

from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import TenantBaseModel


class IndustryTemplate(TenantBaseModel):
    """業種別リスクテンプレート

    金融・製造・IT等の業種ごとに標準リスク項目・統制ベースラインを定義。
    新規監査プロジェクト作成時にテンプレートから初期リスクユニバースを自動生成。
    """

    __tablename__ = "industry_templates"

    # finance, manufacturing, it_services
    industry_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    industry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    region: Mapped[str] = mapped_column(String(20), default="JP")  # JP, SG, HK, AU
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulatory_framework: Mapped[str | None] = mapped_column(String(255), nullable=True)  # J-SOX, SOX, FIEA
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_count: Mapped[int] = mapped_column(Integer, default=0)
    control_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, default=dict)


class RiskTemplateItem(TenantBaseModel):
    """テンプレートリスク項目

    各業種テンプレートに紐づくリスク項目。
    業種固有のリスクカテゴリ・サブカテゴリ・デフォルトスコアを保持。
    """

    __tablename__ = "risk_template_items"

    template_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # access_control, financial_process, etc.
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_code: Mapped[str] = mapped_column(String(50), nullable=False)  # FIN-001, MFG-001
    risk_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_likelihood: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    default_impact: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    default_inherent_score: Mapped[float] = mapped_column(Float, default=0.0)
    regulatory_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 基準番号・条文
    applicable_assertions: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)  # 監査アサーション
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ControlBaseline(TenantBaseModel):
    """統制ベースライン — テンプレートリスクに対する標準統制

    各リスク項目に紐づく推奨統制手続き。
    テンプレート適用時にRCMの初期データとして利用。
    """

    __tablename__ = "control_baselines"

    template_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    risk_item_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    control_code: Mapped[str] = mapped_column(String(50), nullable=False)  # AC-001, FP-001
    control_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str] = mapped_column(String(50), nullable=False)  # preventive, detective, corrective
    frequency: Mapped[str] = mapped_column(String(50), nullable=False)  # daily, weekly, monthly, quarterly
    # inquiry, observation, inspection, reperformance
    test_approach: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommended_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    automation_level: Mapped[str] = mapped_column(String(20), default="manual")  # manual, semi_auto, full_auto
    regulatory_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
