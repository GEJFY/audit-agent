"""SharePoint コネクタ — Microsoft Graph API経由で証跡検索"""

from typing import Any

import httpx
from loguru import logger

from src.config.settings import get_settings
from src.connectors.base import BaseConnector


class SharePointConnector(BaseConnector):
    """SharePoint Online コネクタ

    Microsoft Graph APIを使用してSharePoint上の
    ドキュメントライブラリを検索・取得する。
    認証: Azure AD OAuth 2.0 client_credentials フロー
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._tenant_id = settings.azure_tenant_id
        self._client_id = settings.azure_client_id
        self._client_secret = settings.azure_client_secret
        self._access_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def connector_name(self) -> str:
        return "sharepoint"

    async def connect(self) -> bool:
        """Azure AD OAuth2.0 client_credentials でアクセストークン取得"""
        if not all([self._tenant_id, self._client_id, self._client_secret]):
            logger.warning("SharePoint: Azure AD設定が不完全です")
            return False

        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            response = await self._client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            response.raise_for_status()
            self._access_token = response.json()["access_token"]
            logger.info("SharePoint接続成功")
            return True
        except Exception as e:
            logger.error("SharePoint接続エラー: {}", str(e))
            return False

    async def disconnect(self) -> None:
        """接続切断"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """SharePoint全文検索 — Microsoft Graph Search API

        Args:
            query: 検索クエリ文字列
            kwargs:
                file_type: ファイル種類フィルタ (pdf, xlsx, docx)
                max_results: 最大取得件数 (default: 25)
        """
        if not self._access_token or not self._client:
            connected = await self.connect()
            if not connected:
                return []

        assert self._client is not None

        max_results = kwargs.get("max_results", 25)
        file_type = kwargs.get("file_type")

        search_query = f"{query} filetype:{file_type}" if file_type else query
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await self._client.post(
                "https://graph.microsoft.com/v1.0/search/query",
                headers=headers,
                json={
                    "requests": [
                        {
                            "entityTypes": ["driveItem"],
                            "query": {"queryString": search_query},
                            "from": 0,
                            "size": max_results,
                        }
                    ]
                },
            )
            response.raise_for_status()
            data = response.json()

            results: list[dict[str, Any]] = []
            for hit_container in data.get("value", []):
                for container in hit_container.get("hitsContainers", []):
                    for hit in container.get("hits", []):
                        resource = hit.get("resource", {})
                        results.append(
                            {
                                "id": resource.get("id", ""),
                                "name": resource.get("name", ""),
                                "web_url": resource.get("webUrl", ""),
                                "size": resource.get("size", 0),
                                "created_datetime": resource.get("createdDateTime", ""),
                                "last_modified_datetime": resource.get("lastModifiedDateTime", ""),
                                "created_by": (resource.get("createdBy", {}).get("user", {}).get("displayName", "")),
                                "mime_type": (resource.get("file", {}).get("mimeType", "")),
                                "source": "sharepoint",
                                "summary": hit.get("summary", ""),
                            }
                        )

            logger.info("SharePoint検索完了: query='{}', results={}", query, len(results))
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._access_token = None
                await self.connect()
                return await self.search(query, **kwargs)
            logger.error("SharePoint検索エラー: {}", str(e))
            return []
        except Exception as e:
            logger.error("SharePoint検索エラー: {}", str(e))
            return []

    async def get_file_content(self, drive_item_id: str) -> bytes | None:
        """ファイルコンテンツをダウンロード"""
        if not self._access_token or not self._client:
            return None

        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            response = await self._client.get(
                f"https://graph.microsoft.com/v1.0/drives/{drive_item_id}/content",
                headers=headers,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error("SharePointファイルダウンロードエラー: {}", str(e))
            return None

    async def list_libraries(self, site_id: str) -> list[dict[str, Any]]:
        """サイトのドキュメントライブラリ一覧"""
        if not self._access_token or not self._client:
            return []

        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            response = await self._client.get(
                f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives",
                headers=headers,
            )
            response.raise_for_status()
            return [
                {
                    "id": d["id"],
                    "name": d["name"],
                    "web_url": d.get("webUrl", ""),
                }
                for d in response.json().get("value", [])
            ]
        except Exception as e:
            logger.error("SharePointライブラリ一覧エラー: {}", str(e))
            return []

    async def health_check(self) -> bool:
        """接続チェック"""
        if not self._access_token or not self._client:
            return False
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = await self._client.get(
                "https://graph.microsoft.com/v1.0/sites/root",
                headers=headers,
            )
            return response.status_code == 200
        except Exception:
            return False
