"""監査プロジェクトエンドポイント — DB連携"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.middleware.auth import require_permission
from src.api.schemas.projects import (
    AnomalyResponse,
    FindingCreate,
    FindingResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    RemediationCreate,
    RemediationResponse,
    ReportResponse,
)
from src.db.models.auditor import (
    Anomaly,
    AuditProject,
    Finding,
    RemediationAction,
    Report,
)
from src.security.auth import TokenPayload

router = APIRouter()


def _project_to_response(p: AuditProject) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        name=p.name,
        status=p.status,
        fiscal_year=p.fiscal_year,
        audit_type=p.audit_type,
        tenant_id=p.tenant_id,
        description=p.description,
        target_department=p.target_department,
        auditee_tenant_id=p.auditee_tenant_id,
        agent_mode=p.agent_mode,
        start_date=p.start_date,
        end_date=p.end_date,
        lead_auditor_id=p.lead_auditor_id,
        created_at=p.created_at if hasattr(p, "created_at") else None,
        updated_at=p.updated_at if hasattr(p, "updated_at") else None,
    )


# ── プロジェクトCRUD ───────────────────────────────────


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    user: TokenPayload = Depends(require_permission("project:read")),
    session: AsyncSession = Depends(get_db_session),
    offset: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
    fiscal_year: int | None = None,
) -> ProjectListResponse:
    """監査プロジェクト一覧"""
    query = select(AuditProject).where(AuditProject.tenant_id == user.tenant_id)

    if status_filter:
        query = query.where(AuditProject.status == status_filter)
    if fiscal_year:
        query = query.where(AuditProject.fiscal_year == fiscal_year)

    # 総数
    count_q = select(func.count()).select_from(query.subquery())  # type: ignore[attr-defined]
    total = (await session.execute(count_q)).scalar_one()

    # ページネーション
    query = query.order_by(AuditProject.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        items=[_project_to_response(p) for p in projects],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user: TokenPayload = Depends(require_permission("project:create")),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """監査プロジェクト作成"""
    project = AuditProject(
        tenant_id=user.tenant_id,
        name=data.name,
        description=data.description,
        fiscal_year=data.fiscal_year,
        audit_type=data.audit_type,
        target_department=data.target_department,
        agent_mode=data.agent_mode,
        auditee_tenant_id=data.auditee_tenant_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status="draft",
        lead_auditor_id=user.sub,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: TokenPayload = Depends(require_permission("project:read")),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """監査プロジェクト詳細"""
    result = await session.execute(
        select(AuditProject).where(  # type: ignore[call-arg]
            AuditProject.id == project_id,
            AuditProject.tenant_id == user.tenant_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    user: TokenPayload = Depends(require_permission("project:create")),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    """監査プロジェクト更新"""
    result = await session.execute(
        select(AuditProject).where(  # type: ignore[call-arg]
            AuditProject.id == project_id,
            AuditProject.tenant_id == user.tenant_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata":
            project.metadata_ = value
        else:
            setattr(project, field, value)

    await session.commit()
    await session.refresh(project)

    return _project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: TokenPayload = Depends(require_permission("project:create")),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """監査プロジェクト削除"""
    result = await session.execute(
        select(AuditProject).where(  # type: ignore[call-arg]
            AuditProject.id == project_id,
            AuditProject.tenant_id == user.tenant_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    await session.delete(project)
    await session.commit()


# ── Findings ───────────────────────────────────────────


@router.get("/{project_id}/findings", response_model=list[FindingResponse])
async def list_findings(
    project_id: str,
    user: TokenPayload = Depends(require_permission("project:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[FindingResponse]:
    """プロジェクトの検出事項一覧"""
    result = await session.execute(
        select(Finding)
        .where(  # type: ignore[call-arg]
            Finding.project_id == project_id,
            Finding.tenant_id == user.tenant_id,
        )
        .order_by(Finding.created_at.desc())
    )
    findings = result.scalars().all()
    return [
        FindingResponse(
            id=f.id,
            project_id=f.project_id,
            finding_ref=f.finding_ref,
            title=f.title,
            description=f.description,
            risk_level=f.risk_level,
            status=f.status,
            criteria=f.criteria,
            condition=f.condition,
            cause=f.cause,
            effect=f.effect,
            recommendation=f.recommendation,
            management_response=f.management_response,
            evidence_refs=f.evidence_refs,
            generated_by_agent=f.generated_by_agent,
            created_at=f.created_at if hasattr(f, "created_at") else None,
        )
        for f in findings
    ]


@router.post("/{project_id}/findings", response_model=FindingResponse, status_code=201)
async def create_finding(
    project_id: str,
    data: FindingCreate,
    user: TokenPayload = Depends(require_permission("project:create")),
    session: AsyncSession = Depends(get_db_session),
) -> FindingResponse:
    """検出事項を追加"""
    # 採番
    count_result = await session.execute(
        select(func.count()).select_from(Finding).where(Finding.project_id == project_id)  # type: ignore[arg-type]
    )
    seq = (count_result.scalar_one() or 0) + 1
    finding_ref = f"F-{project_id[:8].upper()}-{seq:03d}"

    finding = Finding(
        tenant_id=user.tenant_id,
        project_id=project_id,
        finding_ref=finding_ref,
        title=data.title,
        description=data.description,
        risk_level=data.risk_level,
        criteria=data.criteria,
        condition=data.condition,
        cause=data.cause,
        effect=data.effect,
        recommendation=data.recommendation,
        status="draft",
    )
    session.add(finding)
    await session.commit()
    await session.refresh(finding)

    return FindingResponse(
        id=finding.id,
        project_id=finding.project_id,
        finding_ref=finding.finding_ref,
        title=finding.title,
        description=finding.description,
        risk_level=finding.risk_level,
        status=finding.status,
        criteria=finding.criteria,
        condition=finding.condition,
        cause=finding.cause,
        effect=finding.effect,
        recommendation=finding.recommendation,
    )


# ── Anomalies ─────────────────────────────────────────


@router.get("/{project_id}/anomalies", response_model=list[AnomalyResponse])
async def list_anomalies(
    project_id: str,
    user: TokenPayload = Depends(require_permission("project:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[AnomalyResponse]:
    """プロジェクトの異常検知結果一覧"""
    result = await session.execute(
        select(Anomaly)
        .where(  # type: ignore[call-arg]
            Anomaly.project_id == project_id,
            Anomaly.tenant_id == user.tenant_id,
        )
        .order_by(Anomaly.created_at.desc())
    )
    anomalies = result.scalars().all()
    return [
        AnomalyResponse(
            id=a.id,
            project_id=a.project_id,
            anomaly_type=a.anomaly_type,
            severity=a.severity,
            description=a.description,
            detection_method=a.detection_method,
            confidence_score=a.confidence_score,
            is_confirmed=a.is_confirmed,
            source_data=a.source_data,
            created_at=a.created_at if hasattr(a, "created_at") else None,
        )
        for a in anomalies
    ]


# ── Reports ────────────────────────────────────────────


@router.get("/{project_id}/reports", response_model=list[ReportResponse])
async def list_reports(
    project_id: str,
    user: TokenPayload = Depends(require_permission("project:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[ReportResponse]:
    """プロジェクトの報告書一覧"""
    result = await session.execute(
        select(Report)
        .where(  # type: ignore[call-arg]
            Report.project_id == project_id,
            Report.tenant_id == user.tenant_id,
        )
        .order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return [
        ReportResponse(
            id=r.id,
            project_id=r.project_id,
            report_type=r.report_type,
            title=r.title,
            status=r.status,
            content=r.content,
            s3_path=r.s3_path,
            generated_by_agent=r.generated_by_agent,
            approved_by=r.approved_by,
            created_at=r.created_at if hasattr(r, "created_at") else None,
        )
        for r in reports
    ]


# ── Remediation Actions ───────────────────────────────


@router.get("/{project_id}/remediations", response_model=list[RemediationResponse])
async def list_remediations(
    project_id: str,
    user: TokenPayload = Depends(require_permission("project:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[RemediationResponse]:
    """プロジェクトの改善措置一覧"""
    result = await session.execute(
        select(RemediationAction)
        .join(Finding, Finding.id == RemediationAction.finding_id)  # type: ignore[arg-type]
        .where(  # type: ignore[attr-defined]
            Finding.project_id == project_id,
            RemediationAction.tenant_id == user.tenant_id,
        )
        .order_by(RemediationAction.created_at.desc())
    )
    actions = result.scalars().all()
    return [
        RemediationResponse(
            id=a.id,
            finding_id=a.finding_id,
            action_description=a.action_description,
            responsible_person=a.responsible_person,
            due_date=a.due_date,
            status=a.status,
            completion_date=a.completion_date,
            created_at=a.created_at if hasattr(a, "created_at") else None,
        )
        for a in actions
    ]


@router.post("/{project_id}/remediations", response_model=RemediationResponse, status_code=201)
async def create_remediation(
    project_id: str,
    data: RemediationCreate,
    user: TokenPayload = Depends(require_permission("project:create")),
    session: AsyncSession = Depends(get_db_session),
) -> RemediationResponse:
    """改善措置を追加"""
    action = RemediationAction(
        tenant_id=user.tenant_id,
        finding_id=data.finding_id,
        action_description=data.action_description,
        responsible_person=data.responsible_person,
        due_date=data.due_date,
        status="planned",
    )
    session.add(action)
    await session.commit()
    await session.refresh(action)

    return RemediationResponse(
        id=action.id,
        finding_id=action.finding_id,
        action_description=action.action_description,
        responsible_person=action.responsible_person,
        due_date=action.due_date,
        status=action.status,
    )
