"""金融業リスクテンプレートのテスト"""

import pytest

from src.risk_templates.finance import get_finance_template


@pytest.mark.unit
class TestFinanceTemplate:
    """金融業テンプレートのテスト"""

    def test_template_metadata(self) -> None:
        tmpl = get_finance_template()
        assert tmpl.industry_code == "finance"
        assert tmpl.industry_name == "金融業"
        assert tmpl.region == "JP"
        assert tmpl.regulatory_framework == "J-SOX"
        assert tmpl.version == "1.0"

    def test_risk_count(self) -> None:
        tmpl = get_finance_template()
        assert tmpl.risk_count == 10

    def test_control_count(self) -> None:
        tmpl = get_finance_template()
        assert tmpl.control_count == 9

    def test_risk_codes_unique(self) -> None:
        tmpl = get_finance_template()
        codes = [r.risk_code for r in tmpl.risks]
        assert len(codes) == len(set(codes))

    def test_control_codes_unique(self) -> None:
        tmpl = get_finance_template()
        codes = [c.control_code for c in tmpl.controls]
        assert len(codes) == len(set(codes))

    def test_all_controls_reference_valid_risk(self) -> None:
        """全統制が有効なリスクコードを参照していること"""
        tmpl = get_finance_template()
        risk_codes = {r.risk_code for r in tmpl.risks}
        for ctrl in tmpl.controls:
            assert ctrl.risk_code in risk_codes, f"{ctrl.control_code} references unknown risk {ctrl.risk_code}"

    def test_financial_process_risks(self) -> None:
        tmpl = get_finance_template()
        fp_risks = tmpl.get_risks_by_category("financial_process")
        assert len(fp_risks) >= 3
        codes = {r.risk_code for r in fp_risks}
        assert "FIN-001" in codes
        assert "FIN-002" in codes

    def test_access_control_risks(self) -> None:
        tmpl = get_finance_template()
        ac_risks = tmpl.get_risks_by_category("access_control")
        assert len(ac_risks) >= 2

    def test_compliance_risks(self) -> None:
        tmpl = get_finance_template()
        comp_risks = tmpl.get_risks_by_category("compliance")
        assert len(comp_risks) >= 2

    def test_categories_coverage(self) -> None:
        """4カテゴリ以上をカバー"""
        tmpl = get_finance_template()
        cats = tmpl.get_categories()
        assert len(cats) >= 4
        assert "financial_process" in cats
        assert "access_control" in cats
        assert "compliance" in cats
        assert "it_general" in cats

    def test_risk_has_regulatory_ref(self) -> None:
        """J-SOX関連リスクは規制参照を持つ"""
        tmpl = get_finance_template()
        jsox_risks = [r for r in tmpl.risks if "j-sox" in r.tags]
        for risk in jsox_risks:
            assert risk.regulatory_ref, f"{risk.risk_code} missing regulatory_ref"

    def test_to_dict(self) -> None:
        tmpl = get_finance_template()
        d = tmpl.to_dict()
        assert d["industry_code"] == "finance"
        assert d["risk_count"] == 10
        assert d["control_count"] == 9
