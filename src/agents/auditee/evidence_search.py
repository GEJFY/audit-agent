"""Evidence Search Agent — 証跡自動探索（コネクタ横断検索）"""

import asyncio
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditeeState
from src.connectors.base import BaseConnector


class EvidenceSearchAgent(BaseAuditAgent[AuditeeState]):
    """証跡自動探索Agent — 複数システムの横断検索

    SharePoint / SAP / Email の各コネクタを使用して
    監査証跡を横断検索し、メタデータ付きで結果を返す。
    """

    # ソースごとの検索優先度（高い順）
    SOURCE_PRIORITY = {
        "sharepoint": 1,
        "sap": 2,
        "email": 3,
    }

    @property
    def agent_name(self) -> str:
        return "auditee_evidence_search"

    @property
    def agent_description(self) -> str:
        return "証跡自動探索 — SharePoint/SAP/メール横断検索・メタデータ付与"

    async def execute(self, state: AuditeeState) -> AuditeeState:
        """証跡検索を実行"""
        logger.info("Evidence Search: 証跡検索開始")

        search_queue = state.evidence_queue
        results: list[dict[str, Any]] = []

        for request in search_queue:
            search_results = await self._search_sources(request)
            results.extend(search_results)

            # 検索結果を監査証跡に記録
            confidence = min(0.9, 0.3 + 0.1 * len(search_results))
            self.record_decision(
                tenant_id=state.tenant_id,
                decision="evidence_searched",
                reasoning=(
                    f"検索: {request.get('query', '')[:80]}, "
                    f"結果: {len(search_results)}件, "
                    f"ソース: {', '.join(request.get('sources', ['all']))}"
                ),
                confidence=confidence,
                resource_type="evidence",
                resource_id=str(request.get("id", "")),
            )

        state.evidence_search_results = results
        state.current_phase = "searching"
        state.current_agent = self.agent_name

        logger.info("Evidence Search: {}件の証跡候補発見", len(results))
        return state

    async def _search_sources(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """複数ソースから証跡を並列検索"""
        query = request.get("query", request.get("description", ""))
        sources = request.get("sources", ["sharepoint", "sap", "email"])
        max_per_source = request.get("max_per_source", 10)
        file_type = request.get("file_type")

        # 並列で各ソースを検索
        tasks = []
        for source in sources:
            tasks.append(self._search_single_source(source, query, max_results=max_per_source, file_type=file_type))

        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果を統合・スコアリング
        all_results: list[dict[str, Any]] = []
        for source, result in zip(sources, source_results, strict=False):
            if isinstance(result, Exception):
                logger.error("証跡検索エラー ({}): {}", source, str(result))
                continue
            for item in result:  # type: ignore[union-attr]
                item["relevance_score"] = self._calculate_relevance(item, query)
            all_results.extend(result)  # type: ignore[arg-type]

        # 関連度スコアで降順ソート
        all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return all_results

    async def _search_single_source(
        self,
        source: str,
        query: str,
        max_results: int = 10,
        file_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """単一ソースから検索 — コネクタ経由"""
        connector = self._get_connector(source)
        if connector is None:
            logger.debug("コネクタ未対応: source={}", source)
            return []

        try:
            connected = await connector.connect()
            if not connected:
                logger.warning("証跡検索: {}接続失敗", source)
                return []

            kwargs: dict[str, Any] = {"max_results": max_results}
            if file_type:
                kwargs["file_type"] = file_type

            # ソース固有のパラメータ
            if source == "email":
                kwargs["has_attachments"] = True  # 証跡には添付ファイルが重要

            results = await connector.search(query, **kwargs)

            # メタデータを付与
            enriched: list[dict[str, Any]] = []
            for item in results:
                enriched.append(
                    {
                        **item,
                        "evidence_source": source,
                        "search_query": query,
                        "evidence_type": self._classify_evidence_type(item, source),
                    }
                )

            logger.info(
                "証跡検索完了 ({}): query='{}', results={}",
                source,
                query[:50],
                len(enriched),
            )
            return enriched

        except Exception as e:
            logger.error("証跡検索エラー ({}): {}", source, str(e))
            return []
        finally:
            await connector.disconnect()

    def _get_connector(self, source: str) -> BaseConnector | None:
        """ソースタイプに応じたコネクタを取得"""
        if source == "sharepoint":
            from src.connectors.sharepoint import SharePointConnector

            return SharePointConnector()
        elif source in ("sap", "erp"):
            from src.connectors.sap import SAPConnector

            return SAPConnector()
        elif source == "email":
            from src.connectors.email import EmailConnector

            return EmailConnector()
        return None

    def _classify_evidence_type(self, item: dict[str, Any], source: str) -> str:
        """証跡タイプを分類"""
        if source == "email":
            if item.get("has_attachments"):
                return "email_with_attachment"
            return "email"

        if source == "sap":
            module = item.get("module", "")
            if module == "fi":
                return "journal_entry"
            elif module == "mm":
                return "purchase_order"
            return "erp_document"

        # SharePoint / その他
        name = item.get("name", "").lower()
        mime = item.get("mime_type", "").lower()

        if any(ext in name for ext in (".pdf",)):
            return "pdf_document"
        elif any(ext in name for ext in (".xlsx", ".xls", ".csv")):
            return "spreadsheet"
        elif any(ext in name for ext in (".docx", ".doc")):
            return "word_document"
        elif any(ext in name for ext in (".pptx", ".ppt")):
            return "presentation"
        elif "image" in mime:
            return "image"
        return "document"

    def _calculate_relevance(self, item: dict[str, Any], query: str) -> float:
        """関連度スコアを算出（0.0〜1.0）"""
        score = 0.0
        query_lower = query.lower()
        query_terms = query_lower.split()

        # 名前・件名にクエリ語が含まれるか
        name = (item.get("name", "") or item.get("subject", "") or "").lower()
        for term in query_terms:
            if term in name:
                score += 0.3

        # 本文プレビューにクエリ語が含まれるか
        body = (item.get("summary", "") or item.get("body_preview", "") or "").lower()
        for term in query_terms:
            if term in body:
                score += 0.1

        # ソースの優先度ボーナス
        source = item.get("evidence_source", item.get("source", ""))
        priority = self.SOURCE_PRIORITY.get(source, 4)
        score += (4 - priority) * 0.05

        # 添付ファイル付きメールはボーナス
        if item.get("has_attachments"):
            score += 0.1

        return min(score, 1.0)
