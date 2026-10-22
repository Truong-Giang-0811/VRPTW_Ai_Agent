from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.rag.loaders import SUPPORTED_EXTENSIONS
from app.rag.service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG - Knowledge Base"])


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    user_id: str = Field(default="default", min_length=1, max_length=128)
    limit: int = Field(default=5, ge=1, le=10)


def _service(request: Request) -> RAGService:
    service = getattr(request.app.state, "rag_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="RAG service chưa sẵn sàng.")
    return service


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(default="default"),
):
    service = _service(request)
    filename = Path(file.filename or "document").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Định dạng không hỗ trợ. Các định dạng: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    data_dir = Path(__file__).resolve().parents[2] / "data" / "rag_tmp"
    data_dir.mkdir(parents=True, exist_ok=True)
    temp_path = data_dir / f"{uuid4().hex}{extension}"
    total = 0
    try:
        with temp_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > service.MAX_FILE_BYTES:
                    raise HTTPException(status_code=413, detail="File vượt quá giới hạn 20 MB.")
                output.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="File tải lên đang trống.")

        try:
            item = await run_in_threadpool(service.ingest_file, temp_path, filename, user_id)
        except (ValueError, RuntimeError) as exc:
            logger.warning("RAG ingest rejected for %s: %s", filename, exc)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("RAG ingestion failed for %s", filename)
            message = str(exc)
            if "GOOGLE_API_KEY" in message:
                raise HTTPException(status_code=503, detail=message) from exc
            raise HTTPException(status_code=500, detail="Không thể lập chỉ mục tài liệu. Kiểm tra log backend.") from exc
        return {"success": True, "document": item}
    finally:
        temp_path.unlink(missing_ok=True)
        await file.close()


@router.get("/documents")
async def list_documents(request: Request, user_id: str = "default"):
    return {"success": True, "documents": await run_in_threadpool(_service(request).list_documents, user_id)}


@router.post("/search")
async def search_documents(payload: RAGSearchRequest, request: Request):
    try:
        results = await run_in_threadpool(
            _service(request).search, payload.query, payload.user_id, payload.limit
        )
        return {"success": True, "results": results}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("RAG search failed")
        message = str(exc)
        if "GOOGLE_API_KEY" in message:
            raise HTTPException(status_code=503, detail=message) from exc
        raise HTTPException(status_code=500, detail="Tìm kiếm tài liệu thất bại. Kiểm tra log backend.") from exc


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, request: Request, user_id: str = "default"):
    deleted = await run_in_threadpool(_service(request).delete_document, document_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu hoặc tài liệu không thuộc người dùng này.")
    return {"success": True, "document_id": document_id}
