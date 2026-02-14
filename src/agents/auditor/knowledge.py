"""Knowledge Agent — 監査基準RAG検索（pgvector連携）"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState
from src.storage.vector import VectorStore

# RAG回答生成用プロンプト
RAG_SYSTEM_PROMPT = """あなたはJ-SOX、IIA国際基準、内部統制の専門家AIです。
以下のルールに従って回答してください:
- 提供された参照情報を最優先で使用する
- 参照情報に該当する内容がない場合は、一般的な監査基準知識で補完する
- 推測や不確実な情報は明示する
- 関連する基準・条文番号を可能な限り引用する
"""

RAG_PROMPT_TEMPLATE = """以下の質問に、提供された参照情報に基づいて回答してください。

## 質問
{question}

## 参照情報（ベクトル検索結果）
{context}

## 回答形式
以下のJSON形式で回答してください:
{{
    "answer": "回答テキスト（マークダウン形式）",
    "confidence": 0.0-1.0,
    "referenced_standards": ["引用した基準・規程名"],
    "related_topics": ["関連トピック"],
    "needs_further_research": false
}}
"""


class KnowledgeAgent(BaseAuditAgent[AuditorState]):
    """Knowledge Agent — 監査基準・規程のRAG検索

    pgvectorを使用して監査基準（J-SOX、IIA基準）、社内規程等を
    セマンティック検索し、検索結果をコンテキストとしてLLMで回答を生成する。
    """

    # 検索するドキュメントタイプ
    KNOWLEDGE_DOC_TYPES = [
        "audit_standard",  # J-SOX, IIA基準
        "regulation",  # 社内規程
        "guidance",  # ガイダンス
    ]

    @property
    def agent_name(self) -> str:
        return "auditor_knowledge"

    @property
    def agent_description(self) -> str:
        return "監査基準RAG — J-SOX・IIA基準・社内規程のベクトル検索"

    async def execute(self, state: AuditorState) -> AuditorState:
        """知識検索を実行"""
        logger.info("Knowledge: 知識検索開始")

        pending = state.pending_questions
        if not pending:
            logger.info("Knowledge: 未回答の質問なし")
            state.current_agent = self.agent_name
            return state

        answered_count = 0
        for question in pending:
            result = await self._search_knowledge_base(question, state.tenant_id)
            state.dialogue_history.append(
                {
                    "agent": self.agent_name,
                    "question": question,
                    "answer": result.get("answer", ""),
                    "confidence": result.get("confidence", 0.5),
                    "references": result.get("referenced_standards", []),
                    "sources_used": result.get("sources_used", 0),
                }
            )
            answered_count += 1

            # 判断を記録
            confidence = result.get("confidence", 0.5)
            query_str = str(question.get("content", question) if isinstance(question, dict) else question)
            self.record_decision(
                tenant_id=state.tenant_id,
                decision="knowledge_searched",
                reasoning=(
                    f"質問: {query_str[:100]}, 検索結果: {result.get('sources_used', 0)}件, 信頼度: {confidence}"
                ),
                confidence=confidence,
                resource_type="knowledge_base",
                resource_id=str(question.get("id", "")) if isinstance(question, dict) else "",
            )

        state.current_agent = self.agent_name
        logger.info("Knowledge: {}件の質問に回答完了", answered_count)
        return state

    async def _search_knowledge_base(self, question: dict[str, Any] | str, tenant_id: str) -> dict[str, Any]:
        """pgvectorからRAG検索してLLMで回答生成"""
        query = question.get("content", str(question)) if isinstance(question, dict) else str(question)

        # pgvectorでセマンティック検索
        context_docs = await self._retrieve_context(query, tenant_id)

        # コンテキストがある場合はRAG、なければLLM直接回答
        if context_docs:
            return await self._generate_rag_answer(query, context_docs)
        else:
            return await self._generate_direct_answer(query)

    async def _retrieve_context(self, query: str, tenant_id: str) -> list[dict[str, Any]]:
        """pgvectorから関連文書を検索"""
        all_results: list[dict[str, Any]] = []

        try:
            vector_store = VectorStore()

            # 各ドキュメントタイプを検索
            for doc_type in self.KNOWLEDGE_DOC_TYPES:
                results = await vector_store.search(
                    query=query,
                    tenant_id=tenant_id,
                    top_k=3,
                    doc_type=doc_type,
                )
                all_results.extend(results)

            # テナントを問わない公共基準も検索（全テナント共通）
            general_results = await vector_store.search(
                query=query,
                tenant_id="common",  # 共通知識ベース
                top_k=3,
                doc_type="audit_standard",
            )
            all_results.extend(general_results)

        except Exception as e:
            logger.warning("VectorStore検索エラー: {}", str(e))

        # 類似度でソートして上位を返す
        all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        # 類似度0.3以上のみ（低品質結果を除外）
        filtered = [r for r in all_results if r.get("similarity", 0) >= 0.3]

        logger.debug(
            "知識ベース検索: query='{}', total={}, filtered={}",
            query[:50],
            len(all_results),
            len(filtered),
        )
        return filtered[:8]  # 最大8件

    async def _generate_rag_answer(self, query: str, context_docs: list[dict[str, Any]]) -> dict[str, Any]:
        """RAG: 検索結果をコンテキストとしてLLM回答を生成"""
        # コンテキストを整形
        context_parts: list[str] = []
        for i, doc in enumerate(context_docs, 1):
            metadata = doc.get("metadata", {})
            doc_name = metadata.get("doc_name", doc.get("doc_type", "不明"))
            section = metadata.get("section", "")
            similarity = doc.get("similarity", 0)

            context_parts.append(
                f"### 参照 {i} ({doc_name}"
                f"{f' / {section}' if section else ''}"
                f", 類似度: {similarity:.2f})\n"
                f"{doc.get('content', '')}"
            )

        context_text = "\n\n".join(context_parts)

        prompt = RAG_PROMPT_TEMPLATE.format(
            question=query,
            context=context_text,
        )

        response = await self.call_llm(
            prompt=prompt,
            system_prompt=RAG_SYSTEM_PROMPT,
        )

        # JSON解析
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "answer": response,
                "confidence": 0.6,
                "referenced_standards": [],
                "related_topics": [],
                "needs_further_research": False,
            }

        result["sources_used"] = len(context_docs)
        result["search_method"] = "rag"
        return result

    async def _generate_direct_answer(self, query: str) -> dict[str, Any]:
        """フォールバック: VectorStore結果なしのLLM直接回答"""
        logger.info("Knowledge: ベクトル検索結果なし、LLM直接回答にフォールバック")

        response = await self.call_llm(
            prompt=(
                "以下の監査関連質問に回答してください。"
                "ベクトル検索データベースに該当する文書が見つからなかったため、"
                "一般的な監査基準知識に基づいて回答します。\n\n"
                f"質問: {query}\n\n"
                "JSON形式で回答してください:\n"
                '{"answer": "回答", "confidence": 0.0-1.0, '
                '"referenced_standards": [], "needs_further_research": true}'
            ),
            system_prompt=RAG_SYSTEM_PROMPT,
            use_fast_model=True,
        )

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "answer": response,
                "confidence": 0.4,
                "referenced_standards": [],
                "needs_further_research": True,
            }

        result["sources_used"] = 0
        result["search_method"] = "direct_llm"
        # 直接回答の信頼度は低く設定
        if result.get("confidence", 0) > 0.7:
            result["confidence"] = 0.7

        return result
