"""リスクテンプレートDBモデルのテスト"""

import pytest

from src.db.models.forecasts import CrossCompanyPattern, RiskForecast
from src.db.models.risk_templates import (
    ControlBaseline,
    IndustryTemplate,
    RiskTemplateItem,
)


@pytest.mark.unit
class TestIndustryTemplateModel:
    """IndustryTemplateモデルのテスト"""

    def test_tablename(self) -> None:
        assert IndustryTemplate.__tablename__ == "industry_templates"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in IndustryTemplate.__table__.columns}
        assert "industry_code" in columns
        assert "industry_name" in columns
        assert "version" in columns
        assert "region" in columns
        assert "is_active" in columns
        assert "risk_count" in columns
        assert "control_count" in columns
        assert "tenant_id" in columns

    def test_inherits_tenant_base(self) -> None:
        columns = {c.name for c in IndustryTemplate.__table__.columns}
        assert "id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
        assert "tenant_id" in columns


@pytest.mark.unit
class TestRiskTemplateItemModel:
    """RiskTemplateItemモデルのテスト"""

    def test_tablename(self) -> None:
        assert RiskTemplateItem.__tablename__ == "risk_template_items"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in RiskTemplateItem.__table__.columns}
        assert "template_id" in columns
        assert "category" in columns
        assert "risk_code" in columns
        assert "risk_name" in columns
        assert "default_likelihood" in columns
        assert "default_impact" in columns


@pytest.mark.unit
class TestControlBaselineModel:
    """ControlBaselineモデルのテスト"""

    def test_tablename(self) -> None:
        assert ControlBaseline.__tablename__ == "control_baselines"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in ControlBaseline.__table__.columns}
        assert "template_id" in columns
        assert "risk_item_id" in columns
        assert "control_code" in columns
        assert "control_name" in columns
        assert "control_type" in columns
        assert "frequency" in columns
        assert "automation_level" in columns


@pytest.mark.unit
class TestRiskForecastModel:
    """RiskForecastモデルのテスト"""

    def test_tablename(self) -> None:
        assert RiskForecast.__tablename__ == "risk_forecasts"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in RiskForecast.__table__.columns}
        assert "forecast_period" in columns
        assert "horizon_days" in columns
        assert "predicted_score" in columns
        assert "model_type" in columns
        assert "confidence_interval_lower" in columns
        assert "confidence_interval_upper" in columns
        assert "trend" in columns


@pytest.mark.unit
class TestCrossCompanyPatternModel:
    """CrossCompanyPatternモデルのテスト"""

    def test_tablename(self) -> None:
        assert CrossCompanyPattern.__tablename__ == "cross_company_patterns"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in CrossCompanyPattern.__table__.columns}
        assert "pattern_type" in columns
        assert "industry_code" in columns
        assert "region" in columns
        assert "pattern_data" in columns
        assert "benchmark_scores" in columns
        assert "sample_size" in columns


@pytest.mark.unit
class TestAuditProjectExtension:
    """AuditProjectフィールド拡張のテスト"""

    def test_has_region_field(self) -> None:
        from src.db.models.auditor import AuditProject

        columns = {c.name for c in AuditProject.__table__.columns}
        assert "region" in columns

    def test_has_industry_field(self) -> None:
        from src.db.models.auditor import AuditProject

        columns = {c.name for c in AuditProject.__table__.columns}
        assert "industry" in columns


@pytest.mark.unit
class TestAgentDecisionExtension:
    """AgentDecisionフィールド拡張のテスト"""

    def test_has_execution_mode_field(self) -> None:
        from src.db.models.auditor import AgentDecision

        columns = {c.name for c in AgentDecision.__table__.columns}
        assert "execution_mode" in columns

    def test_has_auto_approved_reason_field(self) -> None:
        from src.db.models.auditor import AgentDecision

        columns = {c.name for c in AgentDecision.__table__.columns}
        assert "auto_approved_reason" in columns
