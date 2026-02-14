"""プロジェクトスキーマ"""

from typing import Any

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    fiscal_year: int
    audit_type: str
    target_department: str | None = None
    agent_mode: str = "audit"
    auditee_tenant_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    target_department: str | None = None
    agent_mode: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    metadata: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    status: str
    fiscal_year: int
    audit_type: str
    tenant_id: str
    description: str | None = None
    target_department: str | None = None
    auditee_tenant_id: str | None = None
    agent_mode: str = "audit"
    start_date: str | None = None
    end_date: str | None = None
    lead_auditor_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    offset: int
    limit: int


class FindingCreate(BaseModel):
    project_id: str
    title: str
    description: str
    risk_level: str
    criteria: str | None = None
    condition: str | None = None
    cause: str | None = None
    effect: str | None = None
    recommendation: str | None = None


class FindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    risk_level: str | None = None
    status: str | None = None
    management_response: str | None = None
    recommendation: str | None = None


class FindingResponse(BaseModel):
    id: str
    project_id: str
    finding_ref: str
    title: str
    description: str
    risk_level: str
    status: str
    criteria: str | None = None
    condition: str | None = None
    cause: str | None = None
    effect: str | None = None
    recommendation: str | None = None
    management_response: str | None = None
    evidence_refs: list[str] | None = None
    generated_by_agent: bool = False
    created_at: str | None = None

    model_config = {"from_attributes": True}


class AnomalyResponse(BaseModel):
    id: str
    project_id: str
    anomaly_type: str
    severity: str
    description: str
    detection_method: str
    confidence_score: float
    is_confirmed: bool | None = None
    source_data: dict[str, Any] | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    project_id: str
    report_type: str = "draft"
    title: str


class ReportResponse(BaseModel):
    id: str
    project_id: str
    report_type: str
    title: str
    status: str
    content: str | None = None
    s3_path: str | None = None
    generated_by_agent: bool = False
    approved_by: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class RemediationCreate(BaseModel):
    finding_id: str
    action_description: str
    responsible_person: str | None = None
    due_date: str | None = None


class RemediationResponse(BaseModel):
    id: str
    finding_id: str
    action_description: str
    responsible_person: str | None = None
    due_date: str | None = None
    status: str
    completion_date: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}
