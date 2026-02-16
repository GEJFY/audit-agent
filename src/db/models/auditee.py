"""被監査側モデル — 6テーブル"""

from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import TenantBaseModel


class AuditeeResponse(TenantBaseModel):
    """質問への回答履歴"""

    __tablename__ = "auditee_responses"

    dialogue_message_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_draft: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI生成ドラフト
    evidence_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 品質スコア(0-1)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_reused: Mapped[bool] = mapped_column(Boolean, default=False)  # 過去回答再利用
    source_response_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)


class EvidenceRegistry(TenantBaseModel):
    """証跡ファイルメタデータ・インデックス"""

    __tablename__ = "evidence_registry"

    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, xlsx, csv, image, email
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA-256
    source_system: Mapped[str | None] = mapped_column(String(100), nullable=True)  # sharepoint, sap, box, gdrive, email
    source_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # OCR結果
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, default=dict)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=True)
    virus_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    virus_scan_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class RiskAlert(TenantBaseModel):
    """リスクアラート履歴・ステータス"""

    __tablename__ = "risk_alerts"

    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # RiskLevel
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # risk_alert_agent, controls_monitor, external
    detection_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="open")
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    escalated_to_auditor: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ControlsStatus(TenantBaseModel):
    """統制運用状況スコアカード"""

    __tablename__ = "controls_status"

    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    control_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # green, yellow, red
    execution_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 実施率 (0-100)
    deviation_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 逸脱率 (0-100)
    last_checked_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)  # improving, stable, declining
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)
    threshold_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)  # 閾値設定


class SelfAssessment(TenantBaseModel):
    """セルフアセスメント結果"""

    __tablename__ = "self_assessments"

    assessment_period: Mapped[str] = mapped_column(String(20), nullable=False)  # 2026-Q1, 2026-Q2
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    questionnaire: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)  # 質問・回答一覧
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_areas: Mapped[list[Any] | None] = mapped_column(JSONB, default=list)
    action_items: Mapped[list[Any] | None] = mapped_column(JSONB, default=list)
    completed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, submitted, reviewed


class PrepChecklist(TenantBaseModel):
    """監査準備チェックリスト"""

    __tablename__ = "prep_checklists"

    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    checklist_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pre_audit, during_audit, post_audit
    items: Mapped[list[Any] | None] = mapped_column(JSONB, default=list)  # [{task, status, assignee, due_date}]
    predicted_questions: Mapped[list[Any] | None] = mapped_column(JSONB, default=list)  # AI予測質問
    pre_collected_evidence: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    generated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)
