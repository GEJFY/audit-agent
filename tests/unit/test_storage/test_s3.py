"""S3ストレージテスト"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestS3Storage:
    """S3Storageのテスト"""

    @pytest.fixture
    def storage(self) -> "S3Storage":  # noqa: F821
        """モック設定でストレージを作成"""
        with patch("src.storage.s3.get_settings") as mock_settings:
            settings = MagicMock()
            settings.aws_region = "ap-northeast-1"
            settings.aws_access_key_id = "test-key"
            settings.aws_secret_access_key = "test-secret"
            settings.s3_bucket_evidence = "test-evidence-bucket"
            settings.s3_bucket_reports = "test-reports-bucket"
            mock_settings.return_value = settings

            with (
                patch("src.storage.s3.boto3") as mock_boto3,
                patch("src.storage.s3.EncryptionService") as mock_enc_cls,
            ):
                mock_client = MagicMock()
                mock_boto3.client.return_value = mock_client

                mock_enc = MagicMock()
                mock_enc.encrypt_bytes.side_effect = lambda d: b"encrypted:" + d
                mock_enc.decrypt_bytes.side_effect = lambda d: d.replace(b"encrypted:", b"")
                mock_enc_cls.return_value = mock_enc
                mock_enc_cls.compute_hash.return_value = "abc123hash"

                from src.storage.s3 import S3Storage

                s = S3Storage()
                s._client = mock_client
                s._encryption = mock_enc
                return s

    async def test_upload_evidence(self, storage: "S3Storage") -> None:  # noqa: F821
        """証跡アップロード"""
        result = await storage.upload_evidence(
            file_data=b"test data",
            file_name="test.pdf",
            tenant_id="t-001",
        )
        assert "s3_path" in result
        assert "file_hash" in result
        assert "t-001" in result["s3_path"]
        assert "test.pdf" in result["s3_path"]
        storage._client.put_object.assert_called_once()

    async def test_upload_evidence_no_encrypt(self, storage: "S3Storage") -> None:  # noqa: F821
        """暗号化なしアップロード"""
        await storage.upload_evidence(
            file_data=b"plain data",
            file_name="doc.txt",
            tenant_id="t-002",
            encrypt=False,
        )
        # encrypt=Falseなので暗号化サービスは呼ばれない
        storage._encryption.encrypt_bytes.assert_not_called()

    async def test_upload_evidence_with_metadata(self, storage: "S3Storage") -> None:  # noqa: F821
        """メタデータ付きアップロード"""
        result = await storage.upload_evidence(
            file_data=b"data",
            file_name="doc.pdf",
            tenant_id="t-001",
            metadata={"department": "finance"},
        )
        assert result["s3_path"].startswith("s3://")

    async def test_download_evidence(self, storage: "S3Storage") -> None:  # noqa: F821
        """証跡ダウンロード"""
        mock_body = MagicMock()
        mock_body.read.return_value = b"encrypted:file content"
        storage._client.get_object.return_value = {"Body": mock_body}

        data = await storage.download_evidence("tenants/t-001/evidence/test.pdf")
        assert data == b"file content"

    async def test_download_evidence_no_decrypt(self, storage: "S3Storage") -> None:  # noqa: F821
        """復号なしダウンロード"""
        mock_body = MagicMock()
        mock_body.read.return_value = b"raw data"
        storage._client.get_object.return_value = {"Body": mock_body}

        data = await storage.download_evidence("key", decrypt=False)
        assert data == b"raw data"
        storage._encryption.decrypt_bytes.assert_not_called()

    def test_generate_presigned_url(self, storage: "S3Storage") -> None:  # noqa: F821
        """署名付きURL生成"""
        storage._client.generate_presigned_url.return_value = "https://presigned-url"
        url = storage.generate_presigned_url("tenants/t-001/evidence/test.pdf")
        assert url == "https://presigned-url"
        storage._client.generate_presigned_url.assert_called_once()

    def test_generate_presigned_url_custom_expiry(self, storage: "S3Storage") -> None:  # noqa: F821
        """カスタム有効期限の署名付きURL"""
        storage._client.generate_presigned_url.return_value = "https://url"
        storage.generate_presigned_url("key", expiration=7200)
        call_kwargs = storage._client.generate_presigned_url.call_args
        assert call_kwargs.kwargs["ExpiresIn"] == 7200
