"""Auditor DBモデル テスト"""

import pytest

from src.db.models.auditor import (
    RCM,
    AgentDecision,
    Anomaly,
    ApprovalQueue,
    AuditPlan,
    AuditProject,
    Finding,
    RemediationAction,
    Report,
    RiskUniverse,
    TestResult,
)


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestAuditProject:
    def test_tablename(self) -> None:
        assert AuditProject.__tablename__ == "audit_projects"

    def test_has_required_columns(self) -> None:
        for col in ["id", "tenant_id", "name", "fiscal_year", "audit_type", "status", "region"]:
            assert _has_column(AuditProject, col), f"Missing column: {col}"

    def test_default_status(self) -> None:
        col = AuditProject.__table__.columns["status"]
        assert col.default.arg == "draft"

    def test_default_region(self) -> None:
        col = AuditProject.__table__.columns["region"]
        assert col.default.arg == "JP"

    def test_default_agent_mode(self) -> None:
        col = AuditProject.__table__.columns["agent_mode"]
        assert col.default.arg == "audit"

    def test_has_timestamps(self) -> None:
        assert _has_column(AuditProject, "created_at")
        assert _has_column(AuditProject, "updated_at")


@pytest.mark.unit
class TestRiskUniverse:
    def test_tablename(self) -> None:
        assert RiskUniverse.__tablename__ == "risk_universe"

    def test_has_required_columns(self) -> None:
        for col in ["category", "risk_name", "inherent_risk_score", "residual_risk_score"]:
            assert _has_column(RiskUniverse, col), f"Missing column: {col}"

    def test_default_scores(self) -> None:
        assert RiskUniverse.__table__.columns["inherent_risk_score"].default.arg == 0.0
        assert RiskUniverse.__table__.columns["residual_risk_score"].default.arg == 0.0

    def test_default_likelihood_impact(self) -> None:
        assert RiskUniverse.__table__.columns["likelihood"].default.arg == 3
        assert RiskUniverse.__table__.columns["impact"].default.arg == 3


@pytest.mark.unit
class TestAuditPlan:
    def test_tablename(self) -> None:
        assert AuditPlan.__tablename__ == "audit_plans"

    def test_has_required_columns(self) -> None:
        for col in ["project_id", "plan_type", "scope", "generated_by_agent"]:
            assert _has_column(AuditPlan, col), f"Missing column: {col}"

    def test_default_generated_by_agent(self) -> None:
        assert AuditPlan.__table__.columns["generated_by_agent"].default.arg is False

    def test_has_fk_project(self) -> None:
        fks = [fk.target_fullname for fk in AuditPlan.__table__.columns["project_id"].foreign_keys]
        assert "audit_projects.id" in fks


@pytest.mark.unit
class TestRCM:
    def test_tablename(self) -> None:
        assert RCM.__tablename__ == "rcm"

    def test_has_required_columns(self) -> None:
        for col in ["project_id", "control_id", "control_name", "control_type", "control_frequency"]:
            assert _has_column(RCM, col), f"Missing column: {col}"


@pytest.mark.unit
class TestTestResult:
    def test_tablename(self) -> None:
        assert TestResult.__tablename__ == "test_results"

    def test_has_required_columns(self) -> None:
        for col in ["project_id", "rcm_id", "test_date", "result", "sample_tested"]:
            assert _has_column(TestResult, col), f"Missing column: {col}"

    def test_default_sample_tested(self) -> None:
        assert TestResult.__table__.columns["sample_tested"].default.arg == 0

    def test_default_exceptions_found(self) -> None:
        assert TestResult.__table__.columns["exceptions_found"].default.arg == 0

    def test_default_tested_by_agent(self) -> None:
        assert TestResult.__table__.columns["tested_by_agent"].default.arg is False


@pytest.mark.unit
class TestAnomaly:
    def test_tablename(self) -> None:
        assert Anomaly.__tablename__ == "anomalies"

    def test_has_required_columns(self) -> None:
        for col in ["project_id", "anomaly_type", "severity", "description", "detection_method", "confidence_score"]:
            assert _has_column(Anomaly, col), f"Missing column: {col}"


@pytest.mark.unit
class TestFinding:
    def test_tablename(self) -> None:
        assert Finding.__tablename__ == "findings"

    def test_has_required_columns(self) -> None:
        for col in ["project_id", "finding_ref", "title", "description", "risk_level", "status"]:
            assert _has_column(Finding, col), f"Missing column: {col}"

    def test_default_status(self) -> None:
        assert Finding.__table__.columns["status"].default.arg == "draft"

    def test_finding_ref_unique(self) -> None:
        col = Finding.__table__.columns["finding_ref"]
        assert col.unique is True

    def test_default_generated_by_agent(self) -> None:
        assert Finding.__table__.columns["generated_by_agent"].default.arg is False


@pytest.mark.unit
class TestReport:
    def test_tablename(self) -> None:
        assert Report.__tablename__ == "reports"

    def test_has_required_columns(self) -> None:
        for col in ["project_id", "report_type", "title", "status"]:
            assert _has_column(Report, col), f"Missing column: {col}"

    def test_default_status(self) -> None:
        assert Report.__table__.columns["status"].default.arg == "draft"


@pytest.mark.unit
class TestRemediationAction:
    def test_tablename(self) -> None:
        assert RemediationAction.__tablename__ == "remediation_actions"

    def test_has_required_columns(self) -> None:
        for col in ["finding_id", "action_description", "status"]:
            assert _has_column(RemediationAction, col), f"Missing column: {col}"

    def test_default_status(self) -> None:
        assert RemediationAction.__table__.columns["status"].default.arg == "planned"

    def test_has_fk_finding(self) -> None:
        fks = [fk.target_fullname for fk in RemediationAction.__table__.columns["finding_id"].foreign_keys]
        assert "findings.id" in fks


@pytest.mark.unit
class TestAgentDecision:
    def test_tablename(self) -> None:
        assert AgentDecision.__tablename__ == "agent_decisions"

    def test_has_required_columns(self) -> None:
        for col in ["agent_type", "decision_type", "confidence", "model_used", "execution_mode"]:
            assert _has_column(AgentDecision, col), f"Missing column: {col}"

    def test_default_execution_mode(self) -> None:
        assert AgentDecision.__table__.columns["execution_mode"].default.arg == "assist"


@pytest.mark.unit
class TestApprovalQueue:
    def test_tablename(self) -> None:
        assert ApprovalQueue.__tablename__ == "approval_queue"

    def test_has_required_columns(self) -> None:
        for col in ["decision_id", "approval_type", "priority", "status", "requested_by_agent"]:
            assert _has_column(ApprovalQueue, col), f"Missing column: {col}"

    def test_default_priority(self) -> None:
        assert ApprovalQueue.__table__.columns["priority"].default.arg == "medium"

    def test_default_status(self) -> None:
        assert ApprovalQueue.__table__.columns["status"].default.arg == "pending"

    def test_has_fk_decision(self) -> None:
        fks = [fk.target_fullname for fk in ApprovalQueue.__table__.columns["decision_id"].foreign_keys]
        assert "agent_decisions.id" in fks
