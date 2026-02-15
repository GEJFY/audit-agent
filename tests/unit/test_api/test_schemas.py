"""Pydantic スキーマ バリデーションテスト"""

import pytest
from pydantic import ValidationError

from src.api.schemas.agents import (
    AgentDecisionResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    ApprovalActionRequest,
)
from src.api.schemas.dialogue import (
    DialogueApproveRequest,
    DialogueMessageDetail,
    DialogueSendRequest,
)
from src.api.schemas.evidence import (
    EvidenceDownloadResponse,
    EvidenceResponse,
    EvidenceUploadResponse,
)
from src.api.schemas.projects import (
    FindingCreate,
    FindingResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)


@pytest.mark.unit
class TestProjectSchemas:
    def test_project_create_minimal(self) -> None:
        p = ProjectCreate(name="テスト", fiscal_year=2026, audit_type="j-sox")
        assert p.name == "テスト"
        assert p.agent_mode == "audit"

    def test_project_create_full(self) -> None:
        p = ProjectCreate(
            name="テスト",
            fiscal_year=2026,
            audit_type="j-sox",
            description="詳細",
            target_department="経理部",
            agent_mode="assist",
        )
        assert p.description == "詳細"

    def test_project_create_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ProjectCreate(name="テスト")  # fiscal_year, audit_type missing

    def test_project_update_partial(self) -> None:
        p = ProjectUpdate(name="更新名")
        assert p.name == "更新名"
        assert p.status is None

    def test_project_response(self) -> None:
        p = ProjectResponse(
            id="id-001",
            name="テスト",
            status="draft",
            fiscal_year=2026,
            audit_type="j-sox",
            tenant_id="t-001",
        )
        assert p.id == "id-001"

    def test_project_list_response(self) -> None:
        pl = ProjectListResponse(items=[], total=0, offset=0, limit=20)
        assert pl.total == 0

    def test_finding_create(self) -> None:
        f = FindingCreate(
            project_id="p-001",
            title="テスト検出",
            description="詳細",
            risk_level="high",
        )
        assert f.risk_level == "high"

    def test_finding_response(self) -> None:
        f = FindingResponse(
            id="f-001",
            project_id="p-001",
            finding_ref="F-001",
            title="テスト",
            description="詳細",
            risk_level="medium",
            status="draft",
        )
        assert f.finding_ref == "F-001"


@pytest.mark.unit
class TestAgentSchemas:
    def test_execute_request_minimal(self) -> None:
        r = AgentExecuteRequest(agent_name="auditor_planner")
        assert r.project_id is None
        assert r.parameters is None

    def test_execute_request_full(self) -> None:
        r = AgentExecuteRequest(
            agent_name="auditor_planner",
            project_id="p-001",
            parameters={"key": "value"},
        )
        assert r.parameters["key"] == "value"

    def test_execute_response(self) -> None:
        r = AgentExecuteResponse(
            agent_name="auditor_planner",
            status="accepted",
            message="実行開始",
        )
        assert r.status == "accepted"

    def test_decision_response(self) -> None:
        d = AgentDecisionResponse(
            id="d-001",
            agent_type="auditor_planner",
            decision_type="plan_generated",
            confidence=0.85,
            model_used="claude-sonnet",
        )
        assert d.confidence == 0.85

    def test_approval_action_request(self) -> None:
        a = ApprovalActionRequest(action="approved", comment="OK")
        assert a.action == "approved"


@pytest.mark.unit
class TestDialogueSchemas:
    def test_send_request(self) -> None:
        r = DialogueSendRequest(
            to_tenant_id="t-001",
            message_type="question",
            content="テスト質問",
        )
        assert r.to_agent is None
        assert r.attachments is None

    def test_message_detail(self) -> None:
        m = DialogueMessageDetail(
            id="m-001",
            from_tenant_id="t-001",
            to_tenant_id="t-002",
            from_agent="auditor_planner",
            message_type="question",
            content="テスト",
        )
        assert m.is_escalated is False

    def test_approve_request_default(self) -> None:
        a = DialogueApproveRequest()
        assert a.approved is True
        assert a.comment is None


@pytest.mark.unit
class TestEvidenceSchemas:
    def test_upload_response(self) -> None:
        r = EvidenceUploadResponse(
            id="e-001",
            file_name="doc.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="sha256:abc",
            s3_path="s3://bucket/path",
            status="uploaded",
        )
        assert r.file_name == "doc.pdf"

    def test_evidence_response_defaults(self) -> None:
        r = EvidenceResponse(
            id="e-001",
            file_name="doc.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="sha256:abc",
            s3_path="s3://bucket/path",
        )
        assert r.is_encrypted is True
        assert r.virus_scanned is False

    def test_download_response(self) -> None:
        r = EvidenceDownloadResponse(
            id="e-001",
            file_name="doc.pdf",
            download_url="https://s3.example.com/...",
        )
        assert r.expires_in == 3600
