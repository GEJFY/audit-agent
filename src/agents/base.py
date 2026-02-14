"""BaseAuditAgent — 全14エージェントの共通基盤"""

import time
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from loguru import logger
from pydantic import BaseModel

from src.config.constants import CONFIDENCE_THRESHOLD
from src.llm_gateway.gateway import LLMGateway
from src.monitoring.metrics import (
    agent_confidence_score,
    agent_execution_duration_seconds,
    agent_executions_total,
)
from src.security.audit_trail import AuditTrailService

StateT = TypeVar("StateT", bound=BaseModel)


class AgentResult(BaseModel):
    """Agent実行結果"""

    success: bool
    output: dict[str, Any]
    confidence: float = 0.0
    reasoning: str = ""
    requires_human_review: bool = False
    errors: list[str] = []
    processing_time_ms: float = 0.0


class BaseAuditAgent(ABC, Generic[StateT]):
    """全エージェント共通基盤

    - LLMゲートウェイ連携
    - 監査証跡の自動記録
    - 信頼度スコアに基づくエスカレーション
    - Prometheusメトリクス
    """

    def __init__(
        self,
        llm_gateway: LLMGateway,
        audit_trail: AuditTrailService | None = None,
    ) -> None:
        self._llm = llm_gateway
        self._audit_trail = audit_trail or AuditTrailService()

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent識別名"""
        ...

    @property
    @abstractmethod
    def agent_description(self) -> str:
        """Agent説明"""
        ...

    @abstractmethod
    async def execute(self, state: StateT) -> StateT:
        """Agentのメイン処理を実行

        LangGraphのノードとして呼び出される。
        Stateを受け取り、更新されたStateを返す。
        """
        ...

    async def run(self, state: StateT) -> StateT:
        """Agent実行ラッパー — メトリクス・証跡・エスカレーション管理"""
        start = time.monotonic()

        logger.info(f"Agent実行開始: {self.agent_name}")

        try:
            # メイン処理実行
            updated_state = await self.execute(state)

            elapsed_ms = (time.monotonic() - start) * 1000

            # メトリクス記録
            agent_executions_total.labels(
                agent_type=self.agent_name,
                status="success",
            ).inc()
            agent_execution_duration_seconds.labels(
                agent_type=self.agent_name,
            ).observe(elapsed_ms / 1000)

            logger.info(
                f"Agent実行完了: {self.agent_name}",
                elapsed_ms=round(elapsed_ms, 1),
            )

            return updated_state

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            agent_executions_total.labels(
                agent_type=self.agent_name,
                status="error",
            ).inc()
            logger.error(
                f"Agent実行エラー: {self.agent_name}",
                error=str(e),
                elapsed_ms=round(elapsed_ms, 1),
            )
            raise

    def should_escalate(self, confidence: float) -> bool:
        """信頼度スコアに基づくエスカレーション判定"""
        should = confidence < CONFIDENCE_THRESHOLD
        if should:
            logger.warning(
                f"エスカレーション必要: {self.agent_name}",
                confidence=confidence,
                threshold=CONFIDENCE_THRESHOLD,
            )
        agent_confidence_score.labels(agent_type=self.agent_name).observe(confidence)
        return should

    def record_decision(
        self,
        tenant_id: str,
        decision: str,
        reasoning: str,
        confidence: float,
        resource_type: str,
        resource_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Agent判断を監査証跡に記録"""
        from uuid import UUID

        self._audit_trail.record_agent_decision(
            tenant_id=UUID(tenant_id),
            agent_name=self.agent_name,
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
            resource_type=resource_type,
            resource_id=resource_id,
            input_data=input_data,
        )

    async def call_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        use_fast_model: bool = False,
        **kwargs: Any,
    ) -> str:
        """LLM呼び出しヘルパー"""
        response = await self._llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            use_fast_model=use_fast_model,
            **kwargs,
        )
        return response.content
