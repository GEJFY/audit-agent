"""LLMプロンプトテンプレートテスト"""

import pytest


@pytest.mark.unit
class TestAnomalyPrompts:
    """異常検知プロンプトテスト"""

    def test_system_prompt_exists(self) -> None:
        """システムプロンプトが定義されている"""
        from src.llm_gateway.prompts.anomaly import SYSTEM_PROMPT

        assert len(SYSTEM_PROMPT) > 100
        assert "内部監査" in SYSTEM_PROMPT
        assert "J-SOX" in SYSTEM_PROMPT

    def test_analysis_prompt_placeholders(self) -> None:
        """分析プロンプトにプレースホルダーがある"""
        from src.llm_gateway.prompts.anomaly import ANOMALY_ANALYSIS_PROMPT

        assert "{data}" in ANOMALY_ANALYSIS_PROMPT
        assert "{ml_results}" in ANOMALY_ANALYSIS_PROMPT
        assert "anomalies" in ANOMALY_ANALYSIS_PROMPT

    def test_analysis_prompt_format(self) -> None:
        """分析プロンプトのフォーマット可能性"""
        from src.llm_gateway.prompts.anomaly import ANOMALY_ANALYSIS_PROMPT

        result = ANOMALY_ANALYSIS_PROMPT.format(data="テストデータ", ml_results="ML結果")
        assert "テストデータ" in result
        assert "ML結果" in result

    def test_confirmation_prompt_placeholders(self) -> None:
        """確認プロンプトにプレースホルダーがある"""
        from src.llm_gateway.prompts.anomaly import ANOMALY_CONFIRMATION_PROMPT

        assert "{anomaly}" in ANOMALY_CONFIRMATION_PROMPT
        assert "{context}" in ANOMALY_CONFIRMATION_PROMPT


@pytest.mark.unit
class TestReportPrompts:
    """報告書プロンプトテスト"""

    def test_system_prompt_exists(self) -> None:
        """システムプロンプトが定義されている"""
        from src.llm_gateway.prompts.report import SYSTEM_PROMPT

        assert len(SYSTEM_PROMPT) > 100
        assert "報告書" in SYSTEM_PROMPT
        assert "IIA" in SYSTEM_PROMPT

    def test_report_prompt_placeholders(self) -> None:
        """報告書プロンプトにプレースホルダーがある"""
        from src.llm_gateway.prompts.report import REPORT_GENERATION_PROMPT

        assert "{project_info}" in REPORT_GENERATION_PROMPT
        assert "{findings}" in REPORT_GENERATION_PROMPT
        assert "{test_results}" in REPORT_GENERATION_PROMPT

    def test_report_prompt_5c_elements(self) -> None:
        """5C要素が含まれている"""
        from src.llm_gateway.prompts.report import SYSTEM_PROMPT

        assert "Criteria" in SYSTEM_PROMPT
        assert "Condition" in SYSTEM_PROMPT
        assert "Cause" in SYSTEM_PROMPT
        assert "Consequence" in SYSTEM_PROMPT
        assert "Corrective Action" in SYSTEM_PROMPT


@pytest.mark.unit
class TestResponsePrompts:
    """回答生成プロンプトテスト"""

    def test_system_prompt_exists(self) -> None:
        """システムプロンプトが定義されている"""
        from src.llm_gateway.prompts.response import SYSTEM_PROMPT

        assert len(SYSTEM_PROMPT) > 50
        assert "被監査" in SYSTEM_PROMPT

    def test_response_prompt_placeholders(self) -> None:
        """回答プロンプトにプレースホルダーがある"""
        from src.llm_gateway.prompts.response import RESPONSE_GENERATION_PROMPT

        assert "{question}" in RESPONSE_GENERATION_PROMPT
        assert "{regulations}" in RESPONSE_GENERATION_PROMPT
        assert "{past_responses}" in RESPONSE_GENERATION_PROMPT
        assert "{evidence}" in RESPONSE_GENERATION_PROMPT
