"""業種別リスクテンプレートのテスト"""

import pytest

from src.risk_templates import (
    ControlItem,
    IndustryTemplateDefinition,
    RiskItem,
    get_available_industries,
    get_template,
    list_templates,
    load_all_templates,
    register_template,
)


@pytest.mark.unit
class TestRiskItem:
    """リスク項目データクラスのテスト"""

    def test_risk_item_creation(self) -> None:
        item = RiskItem(
            risk_code="TEST-001",
            risk_name="テストリスク",
            category="financial_process",
        )
        assert item.risk_code == "TEST-001"
        assert item.risk_name == "テストリスク"
        assert item.category == "financial_process"
        assert item.default_likelihood == 3
        assert item.default_impact == 3

    def test_risk_item_with_all_fields(self) -> None:
        item = RiskItem(
            risk_code="TEST-002",
            risk_name="詳細リスク",
            category="access_control",
            subcategory="privileged_access",
            description="テスト説明",
            default_likelihood=5,
            default_impact=4,
            regulatory_ref="J-SOX 3.1",
            applicable_assertions=["存在性", "完全性"],
            tags=["j-sox", "access"],
        )
        assert item.default_likelihood == 5
        assert item.default_impact == 4
        assert len(item.applicable_assertions) == 2
        assert len(item.tags) == 2


@pytest.mark.unit
class TestControlItem:
    """統制項目データクラスのテスト"""

    def test_control_item_creation(self) -> None:
        item = ControlItem(
            control_code="TC-001",
            control_name="テスト統制",
            risk_code="TEST-001",
        )
        assert item.control_code == "TC-001"
        assert item.control_type == "detective"
        assert item.frequency == "monthly"
        assert item.recommended_sample_size == 25
        assert item.automation_level == "manual"

    def test_control_item_with_all_fields(self) -> None:
        item = ControlItem(
            control_code="TC-002",
            control_name="自動統制",
            risk_code="TEST-001",
            control_type="preventive",
            frequency="daily",
            test_approach="observation",
            recommended_sample_size=0,
            automation_level="full_auto",
            description="自動化された統制",
            regulatory_ref="ISO 27001",
        )
        assert item.control_type == "preventive"
        assert item.frequency == "daily"
        assert item.automation_level == "full_auto"


@pytest.mark.unit
class TestIndustryTemplateDefinition:
    """テンプレート定義のテスト"""

    def _make_template(self) -> IndustryTemplateDefinition:
        return IndustryTemplateDefinition(
            industry_code="test",
            industry_name="テスト業種",
            risks=[
                RiskItem(risk_code="T-001", risk_name="リスクA", category="cat1"),
                RiskItem(risk_code="T-002", risk_name="リスクB", category="cat1"),
                RiskItem(risk_code="T-003", risk_name="リスクC", category="cat2"),
            ],
            controls=[
                ControlItem(control_code="TC-001", control_name="統制A", risk_code="T-001"),
                ControlItem(control_code="TC-002", control_name="統制B", risk_code="T-001"),
                ControlItem(control_code="TC-003", control_name="統制C", risk_code="T-003"),
            ],
        )

    def test_risk_count(self) -> None:
        tmpl = self._make_template()
        assert tmpl.risk_count == 3

    def test_control_count(self) -> None:
        tmpl = self._make_template()
        assert tmpl.control_count == 3

    def test_get_risks_by_category(self) -> None:
        tmpl = self._make_template()
        cat1_risks = tmpl.get_risks_by_category("cat1")
        assert len(cat1_risks) == 2
        cat2_risks = tmpl.get_risks_by_category("cat2")
        assert len(cat2_risks) == 1
        empty = tmpl.get_risks_by_category("nonexistent")
        assert len(empty) == 0

    def test_get_controls_for_risk(self) -> None:
        tmpl = self._make_template()
        controls = tmpl.get_controls_for_risk("T-001")
        assert len(controls) == 2
        controls_t3 = tmpl.get_controls_for_risk("T-003")
        assert len(controls_t3) == 1
        empty = tmpl.get_controls_for_risk("T-999")
        assert len(empty) == 0

    def test_get_categories(self) -> None:
        tmpl = self._make_template()
        cats = tmpl.get_categories()
        assert cats == ["cat1", "cat2"]

    def test_to_dict(self) -> None:
        tmpl = self._make_template()
        d = tmpl.to_dict()
        assert d["industry_code"] == "test"
        assert d["industry_name"] == "テスト業種"
        assert d["risk_count"] == 3
        assert d["control_count"] == 3
        assert "categories" in d


@pytest.mark.unit
class TestTemplateRegistry:
    """テンプレートレジストリのテスト"""

    def test_register_and_get_template(self) -> None:
        tmpl = IndustryTemplateDefinition(
            industry_code="reg_test",
            industry_name="レジストリテスト",
            region="JP",
        )
        register_template(tmpl)
        result = get_template("reg_test", "JP")
        assert result is not None
        assert result.industry_code == "reg_test"

    def test_get_template_not_found(self) -> None:
        result = get_template("nonexistent_industry", "XX")
        assert result is None

    def test_list_templates(self) -> None:
        templates = list_templates()
        assert isinstance(templates, list)

    def test_load_all_templates(self) -> None:
        count = load_all_templates()
        assert count == 3

    def test_get_available_industries_after_load(self) -> None:
        load_all_templates()
        industries = get_available_industries()
        assert "finance" in industries
        assert "manufacturing" in industries
        assert "it_services" in industries
