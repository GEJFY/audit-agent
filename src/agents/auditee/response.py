"""Response Agent — 質問自動回答（VectorStore連携）"""

import json
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditeeState
from src.db.models.auditee import AuditeeResponse, EvidenceRegistry
from src.db.session import get_session
from src.llm_gateway.prompts.response import RESPONSE_GENERATION_PROMPT, SYSTEM_PROMPT
from src.storage.vector import VectorStore


class ResponseAgent(BaseAuditAgent[AuditeeState]):
    """質問自動回答Agent — NLP解析→知識検索→ドラフト生成

    1. 質問をNLP解析して意図・キーワードを抽出
    2. VectorStoreで過去回答・社内規程をセマンティック検索
    3. DB/コネクタ経由で関連証跡を検索
    4. LLMで回答ドラフトを自動生成
    5. 信頼度が低い場合は部門長承認フローへエスカレーション
    """

    @property
    def agent_name(self) -> str:
        return "auditee_response"

    @property
    def agent_description(self) -> str:
        return "質問自動回答 — NLP解析→知識検索→ドラフト生成→承認フロー"

    async def execute(self, state: AuditeeState) -> AuditeeState:
        """質問に対する回答ドラフトを生成"""
        logger.info("Response Agent: 回答生成開始")

        questions = state.incoming_questions
        drafted: list[dict[str, Any]] = []

        for question in questions:
            draft = await self._generate_response(question, state)
            drafted.append(draft)

            confidence = draft.get("confidence", 0.5)
            if self.should_escalate(confidence):
                state.requires_approval = True
                state.approval_context = {
                    "type": "response_review",
                    "draft": draft,
                    "reason": "回答の信頼度が低いため人間レビューが必要",
                }

            self.record_decision(
                tenant_id=state.tenant_id,
                decision="response_drafted",
                reasoning=f"質問: {question.get('content', '')[:100]}",
                confidence=confidence,
                resource_type="auditee_response",
                resource_id=str(question.get("id", "")),
            )

        state.drafted_responses = drafted
        state.current_phase = "responding"
        state.current_agent = self.agent_name

        logger.info("Response Agent: {}件の回答ドラフト生成完了", len(drafted))
        return state

    async def _generate_response(
        self,
        question: dict[str, Any],
        state: AuditeeState,
    ) -> dict[str, Any]:
        """個別質問への回答ドラフト生成"""
        # 過去の類似回答を検索
        past_responses = await self._search_past_responses(question, state.tenant_id)

        # 関連規程を検索
        regulations = await self._search_regulations(question, state.tenant_id)

        # 関連証跡を検索
        evidence = await self._search_evidence(question, state.tenant_id)

        prompt = RESPONSE_GENERATION_PROMPT.format(
            question=json.dumps(question, ensure_ascii=False, default=str),
            regulations=json.dumps(regulations, ensure_ascii=False, default=str),
            past_responses=json.dumps(past_responses, ensure_ascii=False, default=str),
            evidence=json.dumps(evidence, ensure_ascii=False, default=str),
        )

        response = await self.call_llm(prompt, system_prompt=SYSTEM_PROMPT)

        try:
            draft = json.loads(response)
        except json.JSONDecodeError:
            draft = {
                "response_draft": response,
                "confidence": 0.5,
                "referenced_documents": [],
                "evidence_to_attach": [],
            }

        draft["question_id"] = question.get("id", "")
        draft["is_reused"] = bool(past_responses)

        # 過去回答の再利用元を記録
        if past_responses:
            draft["reused_source_ids"] = [r.get("source_id", "") for r in past_responses if r.get("source_id")]

        return draft  # type: ignore[no-any-return]

    async def _search_past_responses(self, question: dict[str, Any], tenant_id: str) -> list[dict[str, Any]]:
        """過去の類似回答をVectorStoreとDBから検索"""
        query_text = question.get("content", question.get("text", ""))
        if not query_text:
            return []

        results: list[dict[str, Any]] = []

        # VectorStoreからセマンティック検索
        try:
            vector_store = VectorStore()
            vector_results = await vector_store.search(
                query=query_text,
                tenant_id=tenant_id,
                top_k=3,
                doc_type="past_response",
            )
            for vr in vector_results:
                if vr.get("similarity", 0) >= 0.7:  # 類似度70%以上のみ
                    results.append(
                        {
                            "content": vr.get("content", ""),
                            "similarity": vr.get("similarity", 0),
                            "source_id": vr.get("source_id", ""),
                            "metadata": vr.get("metadata", {}),
                            "source": "vector_search",
                        }
                    )
        except Exception as e:
            logger.warning("VectorStore検索エラー (past_responses): {}", str(e))

        # DBからも直近の回答を補完
        try:
            async for session in get_session():
                db_results = await self._query_past_responses_db(session, tenant_id, query_text)
                results.extend(db_results)
                break
        except Exception as e:
            logger.warning("DB検索エラー (past_responses): {}", str(e))

        logger.debug("過去回答検索: {}件 (query='{}')", len(results), query_text[:50])
        return results

    async def _query_past_responses_db(self, session: AsyncSession, tenant_id: str, query: str) -> list[dict[str, Any]]:
        """DBから過去の回答履歴を取得"""
        result = await session.execute(
            select(AuditeeResponse)
            .where(
                AuditeeResponse.tenant_id == tenant_id,
                AuditeeResponse.quality_score >= 0.7,  # 品質スコア70%以上のみ
            )
            .order_by(AuditeeResponse.created_at.desc())
            .limit(5)
        )
        rows = result.scalars().all()
        return [
            {
                "content": r.response_text,
                "question": r.question_text,
                "quality_score": r.quality_score,
                "source_id": str(r.id),
                "is_agent_generated": r.generated_by_agent,
                "source": "db_history",
            }
            for r in rows
        ]

    async def _search_regulations(self, question: dict[str, Any], tenant_id: str) -> list[dict[str, Any]]:
        """関連する社内規程をVectorStoreから検索"""
        query_text = question.get("content", question.get("text", ""))
        if not query_text:
            return []

        try:
            vector_store = VectorStore()
            results = await vector_store.search(
                query=query_text,
                tenant_id=tenant_id,
                top_k=5,
                doc_type="regulation",
            )
            return [
                {
                    "content": r.get("content", ""),
                    "similarity": r.get("similarity", 0),
                    "doc_name": r.get("metadata", {}).get("doc_name", ""),
                    "section": r.get("metadata", {}).get("section", ""),
                    "source_id": r.get("source_id", ""),
                }
                for r in results
                if r.get("similarity", 0) >= 0.5  # 類似度50%以上
            ]
        except Exception as e:
            logger.warning("VectorStore検索エラー (regulations): {}", str(e))
            return []

    async def _search_evidence(self, question: dict[str, Any], tenant_id: str) -> list[dict[str, Any]]:
        """関連証跡をDBから検索"""
        query_text = question.get("content", question.get("text", ""))
        if not query_text:
            return []

        results: list[dict[str, Any]] = []

        # VectorStoreから証跡のセマンティック検索
        try:
            vector_store = VectorStore()
            vector_results = await vector_store.search(
                query=query_text,
                tenant_id=tenant_id,
                top_k=5,
                doc_type="evidence",
            )
            for vr in vector_results:
                if vr.get("similarity", 0) >= 0.5:
                    results.append(
                        {
                            "content_preview": vr.get("content", "")[:200],
                            "similarity": vr.get("similarity", 0),
                            "source_id": vr.get("source_id", ""),
                            "metadata": vr.get("metadata", {}),
                        }
                    )
        except Exception as e:
            logger.warning("VectorStore検索エラー (evidence): {}", str(e))

        # EvidenceRegistryからメタデータ検索
        try:
            async for session in get_session():
                db_evidence = await self._query_evidence_db(session, tenant_id, query_text)
                results.extend(db_evidence)
                break
        except Exception as e:
            logger.warning("DB検索エラー (evidence): {}", str(e))

        logger.debug("証跡検索: {}件 (query='{}')", len(results), query_text[:50])
        return results

    async def _query_evidence_db(self, session: AsyncSession, tenant_id: str, query: str) -> list[dict[str, Any]]:
        """EvidenceRegistryから関連証跡を検索"""
        # extracted_textが存在する証跡をキーワード検索
        keywords = [w for w in query.split() if len(w) >= 2]
        if not keywords:
            return []

        result = await session.execute(
            select(EvidenceRegistry)
            .where(
                EvidenceRegistry.tenant_id == tenant_id,
            )
            .order_by(EvidenceRegistry.created_at.desc())
            .limit(20)
        )
        rows = result.scalars().all()

        matched: list[dict[str, Any]] = []
        for r in rows:
            text_content = (r.extracted_text or "") + " " + (r.file_name or "")
            text_lower = text_content.lower()
            match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
            if match_count > 0:
                matched.append(
                    {
                        "file_name": r.file_name,
                        "file_type": r.file_type,
                        "source_system": r.source_system,
                        "evidence_id": str(r.id),
                        "keyword_matches": match_count,
                        "source": "evidence_registry",
                    }
                )

        # マッチ数で降順ソート
        matched.sort(key=lambda x: x.get("keyword_matches", 0), reverse=True)
        return matched[:5]
