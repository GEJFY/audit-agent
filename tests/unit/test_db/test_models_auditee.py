"""Auditee DBモデル テスト"""

import pytest

from src.db.models.auditee import (
    AuditeeResponse,
    ControlsStatus,
    EvidenceRegistry,
    PrepChecklist,
    RiskAlert,
    SelfAssessment,
)


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestAuditeeResponse:
    def test_tablename(self) -> None:
        assert AuditeeResponse.__tablename__ == "auditee_responses"

    def test_has_required_columns(self) -> None:
        for col in ["dialogue_message_id", "question_text", "response_text", "quality_score"]:
            assert _has_column(AuditeeResponse, col), f"Missing column: {col}"

    def test_default_is_reused(self) -> None:
        assert AuditeeResponse.__table__.columns["is_reused"].default.arg is False

    def test_default_generated_by_agent(self) -> None:
        assert AuditeeResponse.__table__.columns["generated_by_agent"].default.arg is False


@pytest.mark.unit
class TestEvidenceRegistry:
    def test_tablename(self) -> None:
        assert EvidenceRegistry.__tablename__ == "evidence_registry"

    def test_has_required_columns(self) -> None:
        for col in ["file_name", "file_type", "file_size_bytes", "s3_path", "file_hash"]:
            assert _has_column(EvidenceRegistry, col), f"Missing column: {col}"

    def test_default_is_encrypted(self) -> None:
        assert EvidenceRegistry.__table__.columns["is_encrypted"].default.arg is True

    def test_default_virus_scanned(self) -> None:
        assert EvidenceRegistry.__table__.columns["virus_scanned"].default.arg is False


@pytest.mark.unit
class TestRiskAlert:
    def test_tablename(self) -> None:
        assert RiskAlert.__tablename__ == "risk_alerts"

    def test_has_required_columns(self) -> None:
        for col in ["alert_type", "severity", "title", "description", "source", "status"]:
            assert _has_column(RiskAlert, col), f"Missing column: {col}"

    def test_default_status(self) -> None:
        assert RiskAlert.__table__.columns["status"].default.arg == "open"

    def test_default_escalated(self) -> None:
        assert RiskAlert.__table__.columns["escalated_to_auditor"].default.arg is False


@pytest.mark.unit
class TestControlsStatus:
    def test_tablename(self) -> None:
        assert ControlsStatus.__tablename__ == "controls_status"

    def test_has_required_columns(self) -> None:
        for col in ["control_id", "control_name", "category", "status", "execution_rate", "deviation_rate"]:
            assert _has_column(ControlsStatus, col), f"Missing column: {col}"

    def test_default_rates(self) -> None:
        assert ControlsStatus.__table__.columns["execution_rate"].default.arg == 0.0
        assert ControlsStatus.__table__.columns["deviation_rate"].default.arg == 0.0


@pytest.mark.unit
class TestSelfAssessment:
    def test_tablename(self) -> None:
        assert SelfAssessment.__tablename__ == "self_assessments"

    def test_has_required_columns(self) -> None:
        for col in ["assessment_period", "department", "overall_score", "status"]:
            assert _has_column(SelfAssessment, col), f"Missing column: {col}"

    def test_default_status(self) -> None:
        assert SelfAssessment.__table__.columns["status"].default.arg == "draft"


@pytest.mark.unit
class TestPrepChecklist:
    def test_tablename(self) -> None:
        assert PrepChecklist.__tablename__ == "prep_checklists"

    def test_has_required_columns(self) -> None:
        for col in ["checklist_type", "completion_rate", "generated_by_agent"]:
            assert _has_column(PrepChecklist, col), f"Missing column: {col}"

    def test_default_completion_rate(self) -> None:
        assert PrepChecklist.__table__.columns["completion_rate"].default.arg == 0.0

    def test_default_generated_by_agent(self) -> None:
        assert PrepChecklist.__table__.columns["generated_by_agent"].default.arg is False
