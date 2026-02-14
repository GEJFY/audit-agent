"""監査側モデル — 11テーブル"""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import TenantBaseModel


class AuditProject(TenantBaseModel):
    """監査プロジェクト"""

    __tablename__ = "audit_projects"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # ProjectStatus
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_type: Mapped[str] = mapped_column(String(100), nullable=False)  # j-sox, operational, compliance, it
    lead_auditor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    target_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auditee_tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    agent_mode: Mapped[str] = mapped_column(String(20), default="audit")  # AgentMode
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)


class RiskUniverse(TenantBaseModel):
    """リスクユニバース"""

    __tablename__ = "risk_universe"

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    inherent_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    residual_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    likelihood: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    impact: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    risk_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_controls: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)


class AuditPlan(TenantBaseModel):
    """監査計画"""

    __tablename__ = "audit_plans"

    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # annual, engagement, test
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[list | None] = mapped_column(JSONB, default=list)
    risk_assessment: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    resource_allocation: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    timeline: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class RCM(TenantBaseModel):
    """リスクコントロールマトリクス"""

    __tablename__ = "rcm"

    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=False)
    risk_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("risk_universe.id"), nullable=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    control_name: Mapped[str] = mapped_column(String(500), nullable=False)
    control_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str] = mapped_column(String(50), nullable=False)  # preventive, detective, corrective
    control_frequency: Mapped[str] = mapped_column(String(50), nullable=False)  # daily, weekly, monthly, quarterly
    assertion: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 存在性, 完全性, 権利と義務, 評価, 表示
    test_approach: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)


class TestResult(TenantBaseModel):
    """統制テスト結果"""

    __tablename__ = "test_results"

    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=False)
    rcm_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("rcm.id"), nullable=False)
    test_date: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)  # ControlTestResult
    sample_tested: Mapped[int] = mapped_column(Integer, default=0)
    exceptions_found: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    evidence_refs: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    tested_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class Anomaly(TenantBaseModel):
    """異常検知結果"""

    __tablename__ = "anomalies"

    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # RiskLevel
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    detection_method: Mapped[str] = mapped_column(String(100), nullable=False)  # isolation_forest, rule_based, llm
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None=未レビュー
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    related_finding_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class Finding(TenantBaseModel):
    """検出事項"""

    __tablename__ = "findings"

    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=False)
    finding_ref: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # RiskLevel
    status: Mapped[str] = mapped_column(String(50), default="draft")  # FindingStatus
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)  # 判断基準
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)  # 現状
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)  # 原因
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)  # 影響
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)  # 推奨事項
    management_response: Mapped[str | None] = mapped_column(Text, nullable=True)  # 経営者回答
    evidence_refs: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    generated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)


class Report(TenantBaseModel):
    """監査報告書"""

    __tablename__ = "reports"

    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # draft, final, executive_summary
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_structured: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    finding_ids: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    s3_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    generated_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)


class RemediationAction(TenantBaseModel):
    """改善措置"""

    __tablename__ = "remediation_actions"

    finding_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("findings.id"), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="planned")  # planned, in_progress, completed, overdue
    completion_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_of_completion: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class AgentDecision(TenantBaseModel):
    """Agent判断記録 — 全AIの判断を記録"""

    __tablename__ = "agent_decisions"

    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("audit_projects.id"), nullable=True)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)  # AuditorAgentType / AuditeeAgentType
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    output_summary: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class ApprovalQueue(TenantBaseModel):
    """承認キュー — Human-in-the-Loop"""

    __tablename__ = "approval_queue"

    decision_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("agent_decisions.id"), nullable=False)
    approval_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # critical, high, medium, low
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, rejected, deferred
    requested_by_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
