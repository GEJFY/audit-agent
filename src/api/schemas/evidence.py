"""証跡スキーマ"""

from typing import Any

from pydantic import BaseModel


class EvidenceUploadResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    s3_path: str
    status: str


class EvidenceResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    s3_path: str
    source_system: str | None = None
    source_path: str | None = None
    tags: list[str] | None = None
    is_encrypted: bool = True
    virus_scanned: bool = False
    virus_scan_result: str | None = None
    uploaded_by: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceResponse]
    total: int


class EvidenceDownloadResponse(BaseModel):
    id: str
    file_name: str
    download_url: str
    expires_in: int = 3600
