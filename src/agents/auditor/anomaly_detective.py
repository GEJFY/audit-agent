"""Anomaly Detective Agent — 異常検知 (Phase 0 MVP)"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState
from src.llm_gateway.prompts.anomaly import (
    ANOMALY_ANALYSIS_PROMPT,
    ANOMALY_CONFIRMATION_PROMPT,
    SYSTEM_PROMPT,
)


class AnomalyDetectiveAgent(BaseAuditAgent[AuditorState]):
    """異常検知Agent — ML + LLMのハイブリッド異常検知

    Phase 0 MVPのコア機能:
    1. MLモデル（Isolation Forest）で統計的異常を検出
    2. LLM（Claude）で監査的観点から異常を評価
    3. 偽陽性フィルタリングと信頼度スコア付与
    """

    @property
    def agent_name(self) -> str:
        return "auditor_anomaly_detective"

    @property
    def agent_description(self) -> str:
        return "異常検知 — ML+LLMハイブリッドで仕訳・取引の異常を検出"

    async def execute(self, state: AuditorState) -> AuditorState:
        """異常検知フロー: ML検出 → LLM評価 → 結果統合"""
        logger.info("Anomaly Detective: 異常検知開始")

        # 分析対象データを取得
        data = state.metadata.get("collected_data", [])

        # Step 1: ML異常検知
        ml_results = await self._run_ml_detection(data)
        logger.info(f"ML検知結果: {len(ml_results)}件の候補")

        # Step 2: LLM による分析・評価
        llm_analysis = await self._analyze_with_llm(data, ml_results)

        # Step 3: 結果統合
        confirmed_anomalies = await self._confirm_anomalies(ml_results, llm_analysis)

        state.anomalies = confirmed_anomalies

        # 重大な異常があればFindingに昇格
        findings = self._promote_to_findings(confirmed_anomalies, state)
        state.findings.extend(findings)

        state.current_agent = self.agent_name
        logger.info(f"Anomaly Detective: 完了 — {len(confirmed_anomalies)}件確認, {len(findings)}件がFindingに昇格")
        return state

    async def _run_ml_detection(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """MLモデルで統計的異常検出"""
        try:
            from src.ml.anomaly_detector import AnomalyDetector

            _detector = AnomalyDetector()
            # 実際のデータがある場合はMLモデルを実行
            # PoC段階ではプレースホルダー
            return []
        except Exception as e:
            logger.warning(f"ML検知スキップ: {e}")
            return []

    async def _analyze_with_llm(
        self,
        data: list[dict[str, Any]],
        ml_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """LLMで監査的観点から異常を分析"""
        prompt = ANOMALY_ANALYSIS_PROMPT.format(
            data=json.dumps(data[:50], ensure_ascii=False, default=str),  # 上限50件
            ml_results=json.dumps(ml_results, ensure_ascii=False, default=str),
        )

        response = await self.call_llm(prompt, system_prompt=SYSTEM_PROMPT)

        try:
            return json.loads(response)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {"raw_analysis": response, "anomalies": []}

    async def _confirm_anomalies(
        self,
        ml_results: list[dict[str, Any]],
        llm_analysis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """ML結果とLLM分析を統合して異常を確定"""
        confirmed: list[dict[str, Any]] = []

        # LLM検出の異常を処理
        llm_anomalies = llm_analysis.get("anomalies", [])
        for anomaly in llm_anomalies:
            confidence = anomaly.get("confidence", 0.5)
            if confidence >= 0.3:  # 低閾値で候補を保持
                confirmed.append(
                    {
                        **anomaly,
                        "detection_method": "llm",
                        "confirmed": confidence >= 0.7,
                    }
                )

        # ML検出の異常をLLMで確認
        for ml_anomaly in ml_results:
            prompt = ANOMALY_CONFIRMATION_PROMPT.format(
                anomaly=json.dumps(ml_anomaly, ensure_ascii=False, default=str),
                context="仕訳データの統計的異常検知結果",
            )
            response = await self.call_llm(prompt, system_prompt=SYSTEM_PROMPT, use_fast_model=True)

            try:
                evaluation = json.loads(response)
                if evaluation.get("is_true_positive", False):
                    confirmed.append(
                        {
                            **ml_anomaly,
                            "detection_method": "ml+llm",
                            "llm_evaluation": evaluation,
                            "confirmed": True,
                        }
                    )
            except json.JSONDecodeError:
                confirmed.append(
                    {
                        **ml_anomaly,
                        "detection_method": "ml",
                        "confirmed": False,
                    }
                )

        return confirmed

    def _promote_to_findings(
        self,
        anomalies: list[dict[str, Any]],
        state: AuditorState,
    ) -> list[dict[str, Any]]:
        """重大な異常をFindingに昇格"""
        findings: list[dict[str, Any]] = []

        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            confidence = anomaly.get("confidence", 0.0)

            if severity in ("critical", "high") and confidence >= 0.7:
                finding = {
                    "title": anomaly.get("description", "異常検知"),
                    "risk_level": severity,
                    "description": anomaly.get("description", ""),
                    "source_anomaly": anomaly,
                    "generated_by_agent": True,
                }
                findings.append(finding)

                self.record_decision(
                    tenant_id=state.tenant_id,
                    decision="anomaly_promoted_to_finding",
                    reasoning=f"Severity: {severity}, Confidence: {confidence}",
                    confidence=confidence,
                    resource_type="finding",
                    resource_id=state.project_id,
                )

        return findings
