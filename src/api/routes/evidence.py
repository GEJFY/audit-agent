"""証跡管理エンドポイント — S3 + DB連携"""

import hashlib
import mimetypes

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.middleware.auth import require_permission
from src.api.schemas.evidence import (
    EvidenceDownloadResponse,
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceUploadResponse,
)
from src.db.models.auditee import EvidenceRegistry
from src.security.auth import TokenPayload
from src.storage.s3 import S3Storage

router = APIRouter()


def _evidence_to_response(e: EvidenceRegistry) -> EvidenceResponse:
    return EvidenceResponse(
        id=e.id,
        file_name=e.file_name,
        file_type=e.file_type,
        file_size_bytes=e.file_size_bytes,
        file_hash=e.file_hash,
        s3_path=e.s3_path,
        source_system=e.source_system,
        source_path=e.source_path,
        tags=e.tags,
        is_encrypted=e.is_encrypted,
        virus_scanned=e.virus_scanned,
        virus_scan_result=e.virus_scan_result,
        uploaded_by=e.uploaded_by,
        metadata=e.metadata_,
        created_at=e.created_at if hasattr(e, "created_at") else None,
    )


@router.get("/", response_model=EvidenceListResponse)
async def list_evidence(
    user: TokenPayload = Depends(require_permission("evidence:read")),
    session: AsyncSession = Depends(get_db_session),
    source_system: str | None = None,
    file_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> EvidenceListResponse:
    """証跡一覧"""
    query = select(EvidenceRegistry).where(EvidenceRegistry.tenant_id == user.tenant_id)

    if source_system:
        query = query.where(EvidenceRegistry.source_system == source_system)
    if file_type:
        query = query.where(EvidenceRegistry.file_type == file_type)

    count_q = select(func.count()).select_from(query.subquery())  # type: ignore[attr-defined]
    total = (await session.execute(count_q)).scalar_one()

    query = query.order_by(EvidenceRegistry.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    evidence_list = result.scalars().all()

    return EvidenceListResponse(
        evidence=[_evidence_to_response(e) for e in evidence_list],
        total=total,
    )


@router.post("/upload", response_model=EvidenceUploadResponse, status_code=201)
async def upload_evidence(
    file: UploadFile = File(...),
    source_system: str = Form(default="manual"),
    tags: str = Form(default=""),
    user: TokenPayload = Depends(require_permission("evidence:upload")),
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceUploadResponse:
    """証跡アップロード — S3暗号化保存 + メタデータDB記録"""
    file_data = await file.read()
    file_name = file.filename or "unknown"
    file_size = len(file_data)

    # ファイルタイプ判定
    _mime_type, _ = mimetypes.guess_type(file_name)
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown"
    file_type_map = {
        "pdf": "pdf",
        "xlsx": "xlsx",
        "xls": "xlsx",
        "csv": "csv",
        "jpg": "image",
        "jpeg": "image",
        "png": "image",
        "eml": "email",
        "msg": "email",
    }
    file_type = file_type_map.get(ext, ext)

    # SHA-256ハッシュ
    file_hash = hashlib.sha256(file_data).hexdigest()

    # S3アップロード
    try:
        s3 = S3Storage()
        upload_result = await s3.upload_evidence(
            file_data=file_data,
            file_name=file_name,
            tenant_id=user.tenant_id,
            metadata={"source_system": source_system, "uploaded_by": user.sub},
        )
        s3_path = upload_result["s3_path"]
    except Exception as e:
        logger.warning("S3アップロードスキップ（ローカル環境）: {}", str(e))
        s3_path = f"local://evidence/{user.tenant_id}/{file_name}"

    # タグ解析
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    # DBメタデータ記録
    evidence = EvidenceRegistry(
        tenant_id=user.tenant_id,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size,
        s3_path=s3_path,
        file_hash=file_hash,
        source_system=source_system,
        tags=tag_list,
        is_encrypted=True,
        virus_scanned=False,
        uploaded_by=user.sub,
    )
    session.add(evidence)
    await session.commit()
    await session.refresh(evidence)

    logger.info(
        "証跡アップロード完了",
        evidence_id=evidence.id,
        file_name=file_name,
        file_hash=file_hash,
    )

    return EvidenceUploadResponse(
        id=evidence.id,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size,
        file_hash=file_hash,
        s3_path=s3_path,
        status="uploaded",
    )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    user: TokenPayload = Depends(require_permission("evidence:read")),
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceResponse:
    """証跡詳細"""
    result = await session.execute(
        select(EvidenceRegistry).where(  # type: ignore[call-arg]
            EvidenceRegistry.id == evidence_id,
            EvidenceRegistry.tenant_id == user.tenant_id,
        )
    )
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=404, detail="証跡が見つかりません")

    return _evidence_to_response(evidence)


@router.get("/{evidence_id}/download", response_model=EvidenceDownloadResponse)
async def download_evidence(
    evidence_id: str,
    user: TokenPayload = Depends(require_permission("evidence:download")),
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceDownloadResponse:
    """証跡ダウンロード — 署名付きURL生成"""
    result = await session.execute(
        select(EvidenceRegistry).where(  # type: ignore[call-arg]
            EvidenceRegistry.id == evidence_id,
            EvidenceRegistry.tenant_id == user.tenant_id,
        )
    )
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=404, detail="証跡が見つかりません")

    # S3署名付きURL生成
    try:
        s3 = S3Storage()
        s3_key = evidence.s3_path.replace(f"s3://{s3._evidence_bucket}/", "")
        download_url = s3.generate_presigned_url(s3_key, expiration=3600)
    except Exception:
        download_url = f"/api/v1/evidence/{evidence_id}/direct-download"

    return EvidenceDownloadResponse(
        id=evidence.id,
        file_name=evidence.file_name,
        download_url=download_url,
        expires_in=3600,
    )


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: str,
    user: TokenPayload = Depends(require_permission("evidence:upload")),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """証跡削除"""
    result = await session.execute(
        select(EvidenceRegistry).where(  # type: ignore[call-arg]
            EvidenceRegistry.id == evidence_id,
            EvidenceRegistry.tenant_id == user.tenant_id,
        )
    )
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=404, detail="証跡が見つかりません")

    await session.delete(evidence)
    await session.commit()
