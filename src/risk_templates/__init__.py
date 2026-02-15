"""業種別リスクテンプレートローダー

テンプレート定義を読み込み、監査プロジェクトの初期データ生成に利用。
対応業種: finance（金融）, manufacturing（製造）, it_services（IT）
"""

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class RiskItem:
    """テンプレートリスク項目"""

    risk_code: str
    risk_name: str
    category: str
    subcategory: str = ""
    description: str = ""
    default_likelihood: int = 3
    default_impact: int = 3
    regulatory_ref: str = ""
    applicable_assertions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class ControlItem:
    """テンプレート統制項目"""

    control_code: str
    control_name: str
    risk_code: str  # 紐づくリスクコード
    control_type: str = "detective"  # preventive, detective, corrective
    frequency: str = "monthly"
    test_approach: str = "inspection"
    recommended_sample_size: int = 25
    automation_level: str = "manual"
    description: str = ""
    regulatory_ref: str = ""


@dataclass
class IndustryTemplateDefinition:
    """業種テンプレート定義"""

    industry_code: str
    industry_name: str
    region: str = "JP"
    version: str = "1.0"
    description: str = ""
    regulatory_framework: str = ""
    risks: list[RiskItem] = field(default_factory=list)
    controls: list[ControlItem] = field(default_factory=list)

    @property
    def risk_count(self) -> int:
        return len(self.risks)

    @property
    def control_count(self) -> int:
        return len(self.controls)

    def get_risks_by_category(self, category: str) -> list[RiskItem]:
        """カテゴリ別リスク取得"""
        return [r for r in self.risks if r.category == category]

    def get_controls_for_risk(self, risk_code: str) -> list[ControlItem]:
        """リスクコードに紐づく統制取得"""
        return [c for c in self.controls if c.risk_code == risk_code]

    def get_categories(self) -> list[str]:
        """全カテゴリ一覧"""
        return sorted({r.category for r in self.risks})

    def to_dict(self) -> dict[str, Any]:
        """辞書変換（API応答用）"""
        return {
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "region": self.region,
            "version": self.version,
            "description": self.description,
            "regulatory_framework": self.regulatory_framework,
            "risk_count": self.risk_count,
            "control_count": self.control_count,
            "categories": self.get_categories(),
        }


# ── テンプレートレジストリ ──────────────────────────────
_TEMPLATE_REGISTRY: dict[str, IndustryTemplateDefinition] = {}


def register_template(template: IndustryTemplateDefinition) -> None:
    """テンプレートをレジストリに登録"""
    key = f"{template.industry_code}_{template.region}"
    _TEMPLATE_REGISTRY[key] = template
    logger.info(
        f"テンプレート登録: {template.industry_name} ({template.region}), "
        f"リスク={template.risk_count}, 統制={template.control_count}"
    )


def get_template(industry_code: str, region: str = "JP") -> IndustryTemplateDefinition | None:
    """テンプレート取得"""
    return _TEMPLATE_REGISTRY.get(f"{industry_code}_{region}")


def list_templates() -> list[dict[str, Any]]:
    """登録済みテンプレート一覧"""
    return [t.to_dict() for t in _TEMPLATE_REGISTRY.values()]


def get_available_industries() -> list[str]:
    """利用可能な業種コード一覧"""
    return sorted({t.industry_code for t in _TEMPLATE_REGISTRY.values()})


def load_all_templates() -> int:
    """全業種テンプレートをロード

    Returns:
        ロードしたテンプレート数
    """
    from src.risk_templates.finance import get_finance_template
    from src.risk_templates.it_services import get_it_services_template
    from src.risk_templates.manufacturing import get_manufacturing_template

    templates = [
        get_finance_template(),
        get_manufacturing_template(),
        get_it_services_template(),
    ]

    for template in templates:
        register_template(template)

    logger.info(f"全テンプレートロード完了: {len(templates)}業種")
    return len(templates)
