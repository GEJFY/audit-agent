"""リスクテンプレートエンドポイント — 業種別テンプレート管理"""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.risk_templates import (
    get_available_industries,
    get_template,
    list_templates,
    load_all_templates,
)

router = APIRouter()

# 初回ロード
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if not _loaded:
        load_all_templates()
        _loaded = True


@router.get("/")
async def get_templates() -> dict[str, Any]:
    """登録済みテンプレート一覧"""
    _ensure_loaded()
    templates = list_templates()
    return {
        "templates": templates,
        "count": len(templates),
    }


@router.get("/industries")
async def get_industries() -> dict[str, Any]:
    """利用可能な業種コード一覧"""
    _ensure_loaded()
    industries = get_available_industries()
    return {
        "industries": industries,
        "count": len(industries),
    }


@router.get("/{industry_code}")
async def get_template_detail(
    industry_code: str,
    region: str = "JP",
) -> dict[str, Any]:
    """業種テンプレート詳細取得"""
    _ensure_loaded()
    template = get_template(industry_code, region)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found: {industry_code} ({region})",
        )

    return {
        "industry_code": template.industry_code,
        "industry_name": template.industry_name,
        "region": template.region,
        "version": template.version,
        "description": template.description,
        "regulatory_framework": template.regulatory_framework,
        "risk_count": template.risk_count,
        "control_count": template.control_count,
        "categories": template.get_categories(),
        "risks": [
            {
                "risk_code": r.risk_code,
                "risk_name": r.risk_name,
                "category": r.category,
                "subcategory": r.subcategory,
                "default_likelihood": r.default_likelihood,
                "default_impact": r.default_impact,
                "regulatory_ref": r.regulatory_ref,
            }
            for r in template.risks
        ],
        "controls": [
            {
                "control_code": c.control_code,
                "control_name": c.control_name,
                "risk_code": c.risk_code,
                "control_type": c.control_type,
                "frequency": c.frequency,
                "test_approach": c.test_approach,
            }
            for c in template.controls
        ],
    }


@router.get("/{industry_code}/risks")
async def get_template_risks(
    industry_code: str,
    region: str = "JP",
    category: str | None = None,
) -> dict[str, Any]:
    """テンプレートリスク項目取得"""
    _ensure_loaded()
    template = get_template(industry_code, region)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found: {industry_code} ({region})",
        )

    risks = template.risks
    if category:
        risks = template.get_risks_by_category(category)

    return {
        "industry_code": industry_code,
        "category_filter": category,
        "risks": [
            {
                "risk_code": r.risk_code,
                "risk_name": r.risk_name,
                "category": r.category,
                "subcategory": r.subcategory,
                "description": r.description,
                "default_likelihood": r.default_likelihood,
                "default_impact": r.default_impact,
                "regulatory_ref": r.regulatory_ref,
                "tags": r.tags,
            }
            for r in risks
        ],
        "count": len(risks),
    }
