"""リスクテンプレート統合テスト

テンプレートのロード → リスク取得 → 統制取得のフローを検証。
"""

import pytest

from src.risk_templates import (
    get_available_industries,
    get_template,
    list_templates,
    load_all_templates,
)


@pytest.mark.integration
class TestTemplateLoadingFlow:
    """テンプレートロードフロー"""

    def test_load_all_templates(self) -> None:
        """全テンプレートロード"""
        count = load_all_templates()
        assert count == 3

    def test_list_after_load(self) -> None:
        """ロード後の一覧取得"""
        load_all_templates()
        templates = list_templates()
        assert len(templates) >= 3
        codes = [t["industry_code"] for t in templates]
        assert "finance" in codes
        assert "manufacturing" in codes
        assert "it_services" in codes

    def test_available_industries(self) -> None:
        """利用可能業種コード"""
        load_all_templates()
        industries = get_available_industries()
        assert set(industries) >= {"finance", "manufacturing", "it_services"}


@pytest.mark.integration
class TestFinanceTemplateFlow:
    """金融テンプレートフロー"""

    def test_finance_template_detail(self) -> None:
        """金融テンプレート詳細"""
        load_all_templates()
        template = get_template("finance", "JP")
        assert template is not None
        assert template.industry_code == "finance"
        assert template.risk_count >= 10
        assert template.control_count >= 9

    def test_finance_risk_categories(self) -> None:
        """金融テンプレートのリスクカテゴリ"""
        load_all_templates()
        template = get_template("finance", "JP")
        assert template is not None
        categories = template.get_categories()
        assert "financial_process" in categories
        assert "access_control" in categories
        assert "compliance" in categories

    def test_finance_risk_control_mapping(self) -> None:
        """リスクと統制の紐付け"""
        load_all_templates()
        template = get_template("finance", "JP")
        assert template is not None

        # FIN-001 に対する統制がある
        controls = template.get_controls_for_risk("FIN-001")
        assert len(controls) >= 1
        for c in controls:
            assert c.risk_code == "FIN-001"

    def test_finance_risks_by_category(self) -> None:
        """カテゴリ別リスク取得"""
        load_all_templates()
        template = get_template("finance", "JP")
        assert template is not None

        compliance_risks = template.get_risks_by_category("compliance")
        assert len(compliance_risks) >= 1
        for r in compliance_risks:
            assert r.category == "compliance"


@pytest.mark.integration
class TestCrossTemplateConsistency:
    """テンプレート横断整合性テスト"""

    def test_all_templates_have_risks_and_controls(self) -> None:
        """全テンプレートにリスクと統制がある"""
        load_all_templates()
        for industry in get_available_industries():
            template = get_template(industry, "JP")
            assert template is not None, f"Template not found: {industry}"
            assert template.risk_count > 0, f"No risks in: {industry}"
            assert template.control_count > 0, f"No controls in: {industry}"

    def test_all_templates_have_to_dict(self) -> None:
        """全テンプレートのto_dict()が正常動作"""
        load_all_templates()
        for industry in get_available_industries():
            template = get_template(industry, "JP")
            assert template is not None
            d = template.to_dict()
            assert "industry_code" in d
            assert "risk_count" in d
            assert "categories" in d

    def test_nonexistent_template(self) -> None:
        """存在しないテンプレートはNone"""
        load_all_templates()
        assert get_template("nonexistent", "JP") is None
        assert get_template("finance", "XX") is None
