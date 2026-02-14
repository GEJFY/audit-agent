"""SAP コネクタ — OData API経由でERPデータ取得"""

from typing import Any

import httpx
from loguru import logger

from src.config.settings import get_settings
from src.connectors.base import BaseConnector


class SAPConnector(BaseConnector):
    """SAP OData コネクタ

    SAP S/4HANA, ECC のOData APIを使用して
    各モジュール (FI, MM, SD) のデータを取得する。
    認証: Basic Auth or SAP OAuth 2.0
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.sap_base_url
        self._username = settings.sap_username
        self._password = settings.sap_password
        self._client_id = settings.sap_client_id
        self._access_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def connector_name(self) -> str:
        return "sap"

    async def connect(self) -> bool:
        """SAP接続確立 — Basic Auth or OAuth"""
        if not self._base_url:
            logger.warning("SAP: 接続先URLが設定されていません")
            return False

        try:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                verify=True,
            )

            # OAuth認証（client_idが設定されている場合）
            if self._client_id:
                token_url = f"{self._base_url}/sap/bc/sec/oauth2/token"
                response = await self._client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                    },
                    auth=(self._username, self._password),
                )
                response.raise_for_status()
                self._access_token = response.json()["access_token"]
            else:
                # Basic Authの場合は接続テスト
                response = await self._client.get(
                    f"{self._base_url}/sap/opu/odata/sap/API_JOURNALENTRYITEMBASIC_SRV/",
                    auth=(self._username, self._password),
                    headers={"Accept": "application/json"},
                )
                if response.status_code in (200, 401, 403):
                    # 401/403でもSAPは動いている
                    pass

            logger.info("SAP接続成功: {}", self._base_url)
            return True
        except Exception as e:
            logger.error("SAP接続エラー: {}", str(e))
            return False

    async def disconnect(self) -> None:
        """接続切断"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None

    def _get_auth(self) -> tuple[str, str] | None:
        """認証情報を取得"""
        if self._access_token:
            return None  # Bearerトークンを使用
        return (self._username, self._password)

    def _get_headers(self) -> dict[str, str]:
        """リクエストヘッダーを構築"""
        headers = {
            "Accept": "application/json",
            "sap-client": "100",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """SAPデータ検索 — OData APIクエリ実行

        Args:
            query: ODataフィルタ式 or 自然言語クエリ
            kwargs:
                entity_set: ODataエンティティセット名
                    (例: JournalEntryItemBasic, PurchaseOrder)
                service: ODataサービスパス
                    (例: API_JOURNALENTRYITEMBASIC_SRV)
                filters: $filter パラメータ
                select: $select フィールド一覧
                top: $top 件数制限 (default: 100)
                module: SAPモジュール (fi, mm, sd)
        """
        if not self._client:
            connected = await self.connect()
            if not connected:
                return []

        assert self._client is not None

        module = kwargs.get("module", "fi")
        entity_set = kwargs.get("entity_set")
        service = kwargs.get("service")
        top = kwargs.get("top", 100)
        select_fields = kwargs.get("select")
        filters = kwargs.get("filters")

        # モジュールに応じたデフォルトサービス
        if not service:
            service_map = {
                "fi": "API_JOURNALENTRYITEMBASIC_SRV",
                "mm": "API_PURCHASEORDER_PROCESS_SRV",
                "sd": "API_SALES_ORDER_SRV",
                "ap": "API_SUPPLIERINVOICE_PROCESS_SRV",
                "ar": "API_BILLING_DOCUMENT_SRV",
            }
            service = service_map.get(module, "API_JOURNALENTRYITEMBASIC_SRV")

        if not entity_set:
            entity_map = {
                "API_JOURNALENTRYITEMBASIC_SRV": "A_JournalEntryItemBasic",
                "API_PURCHASEORDER_PROCESS_SRV": "A_PurchaseOrder",
                "API_SALES_ORDER_SRV": "A_SalesOrder",
                "API_SUPPLIERINVOICE_PROCESS_SRV": "A_SupplierInvoice",
                "API_BILLING_DOCUMENT_SRV": "A_BillingDocument",
            }
            entity_set = entity_map.get(service, "A_JournalEntryItemBasic")

        url = f"{self._base_url}/sap/opu/odata/sap/{service}/{entity_set}"

        params: dict[str, str] = {
            "$top": str(top),
            "$format": "json",
            "$inlinecount": "allpages",
        }
        if filters or query:
            params["$filter"] = filters or query
        if select_fields:
            params["$select"] = select_fields

        try:
            response = await self._client.get(
                url,
                params=params,
                headers=self._get_headers(),
                auth=self._get_auth(),
            )
            response.raise_for_status()
            data = response.json()

            results_raw = data.get("d", {}).get("results", [])
            results: list[dict[str, Any]] = []
            for item in results_raw:
                # __metadata などSAP内部フィールドを除去
                clean = {
                    k: v for k, v in item.items() if not k.startswith("__")
                }
                clean["source"] = "sap"
                clean["module"] = module
                results.append(clean)

            logger.info(
                "SAP検索完了: service={}, entity={}, results={}",
                service, entity_set, len(results),
            )
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._access_token = None
                await self.connect()
                return await self.search(query, **kwargs)
            logger.error("SAP検索エラー: {} (status={})", str(e), e.response.status_code)
            return []
        except Exception as e:
            logger.error("SAP検索エラー: {}", str(e))
            return []

    async def get_journal_entries(
        self,
        company_code: str,
        fiscal_year: int,
        posting_date_from: str | None = None,
        posting_date_to: str | None = None,
        top: int = 1000,
    ) -> list[dict[str, Any]]:
        """仕訳データ取得 — FIモジュール"""
        filters_parts = [
            f"CompanyCode eq '{company_code}'",
            f"FiscalYear eq '{fiscal_year}'",
        ]
        if posting_date_from:
            filters_parts.append(
                f"PostingDate ge datetime'{posting_date_from}T00:00:00'"
            )
        if posting_date_to:
            filters_parts.append(
                f"PostingDate le datetime'{posting_date_to}T23:59:59'"
            )

        return await self.search(
            "",
            module="fi",
            filters=" and ".join(filters_parts),
            select="CompanyCode,FiscalYear,AccountingDocument,PostingDate,"
                   "GLAccount,AmountInCompanyCodeCurrency,DocumentDate,"
                   "AccountingDocumentType,CreatedByUser",
            top=top,
        )

    async def get_purchase_orders(
        self,
        company_code: str,
        top: int = 500,
    ) -> list[dict[str, Any]]:
        """発注データ取得 — MMモジュール"""
        return await self.search(
            "",
            module="mm",
            filters=f"CompanyCode eq '{company_code}'",
            top=top,
        )

    async def health_check(self) -> bool:
        """接続チェック"""
        if not self._client:
            return False
        try:
            response = await self._client.get(
                f"{self._base_url}/sap/opu/odata/sap/API_JOURNALENTRYITEMBASIC_SRV/",
                headers=self._get_headers(),
                auth=self._get_auth(),
            )
            return response.status_code in (200, 401, 403)
        except Exception:
            return False
