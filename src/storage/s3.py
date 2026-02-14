"""S3 証跡ストレージ"""

from typing import Any

import boto3
from loguru import logger

from src.config.settings import get_settings
from src.security.encryption import EncryptionService


class S3Storage:
    """S3ベースの証跡ストレージ

    - 証跡ファイルの暗号化アップロード/ダウンロード
    - 署名付きURL生成
    - メタデータ管理
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self._evidence_bucket = settings.s3_bucket_evidence
        self._reports_bucket = settings.s3_bucket_reports
        self._encryption = EncryptionService()

    async def upload_evidence(
        self,
        file_data: bytes,
        file_name: str,
        tenant_id: str,
        metadata: dict[str, str] | None = None,
        encrypt: bool = True,
    ) -> dict[str, str]:
        """証跡ファイルをS3にアップロード"""
        s3_key = f"tenants/{tenant_id}/evidence/{file_name}"

        # ハッシュ計算
        file_hash = EncryptionService.compute_hash(file_data)

        # 暗号化
        upload_data = self._encryption.encrypt_bytes(file_data) if encrypt else file_data

        extra_args: dict[str, Any] = {
            "ServerSideEncryption": "aws:kms",
            "Metadata": {
                "tenant_id": tenant_id,
                "file_hash": file_hash,
                "encrypted": str(encrypt),
                **(metadata or {}),
            },
        }

        self._client.put_object(
            Bucket=self._evidence_bucket,
            Key=s3_key,
            Body=upload_data,
            **extra_args,
        )

        logger.info("証跡アップロード完了", s3_key=s3_key, file_hash=file_hash)

        return {
            "s3_path": f"s3://{self._evidence_bucket}/{s3_key}",
            "file_hash": file_hash,
            "encrypted": str(encrypt),
        }

    async def download_evidence(
        self,
        s3_key: str,
        decrypt: bool = True,
    ) -> bytes:
        """証跡ファイルをS3からダウンロード"""
        response = self._client.get_object(
            Bucket=self._evidence_bucket,
            Key=s3_key,
        )
        data = response["Body"].read()

        if decrypt:
            data = self._encryption.decrypt_bytes(data)

        return data  # type: ignore[no-any-return]

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
    ) -> str:
        """署名付きダウンロードURL生成"""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._evidence_bucket, "Key": s3_key},
            ExpiresIn=expiration,
        )
