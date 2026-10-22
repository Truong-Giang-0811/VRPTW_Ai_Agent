
from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.loaders import load_document
from app.rag.vector_store import RAGVectorStore


class RAGService:
    MAX_FILE_BYTES = 20 * 1024 * 1024

    def __init__(self, data_dir: str | Path):
        root = Path(data_dir).resolve()
        self.upload_dir = root / "uploads"
        self.manifest_dir = root / "rag_manifests"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = RAGVectorStore(root / "qdrant")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(__import__("os").getenv("RAG_CHUNK_SIZE", "1000")),
            chunk_overlap=int(__import__("os").getenv("RAG_CHUNK_OVERLAP", "150")),
            add_start_index=True,
        )

    @staticmethod
    def _safe_user_id(user_id: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", (user_id or "default").strip())[:100]
        return safe or "default"

    def _user_dir(self, user_id: str) -> Path:
        directory = self.upload_dir / self._safe_user_id(user_id)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _manifest_path(self, user_id: str) -> Path:
        return self.manifest_dir / f"{self._safe_user_id(user_id)}.json"

    def _read_manifest(self, user_id: str) -> list[dict[str, Any]]:
        path = self._manifest_path(user_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write_manifest(self, user_id: str, items: list[dict[str, Any]]) -> None:
        self._manifest_path(user_id).write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def ingest_file(self, file_path: str | Path, filename: str, user_id: str) -> dict[str, Any]:
        path = Path(file_path)
        document_id = str(uuid.uuid4())
        raw_documents = load_document(path)
        chunks = self.splitter.split_documents(raw_documents)
        if not chunks:
            raise ValueError("Không tạo được chunk từ tài liệu.")

        for index, chunk in enumerate(chunks):
            original_page = chunk.metadata.get("page")
            metadata = dict(chunk.metadata)
            metadata.update(
                {
                    "user_id": self._safe_user_id(user_id),
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": index,
                }
            )
            # PyPDFLoader stores page numbers from zero; keep that value internally.
            if original_page is not None:
                metadata["page"] = int(original_page)
            chunk.metadata = metadata

       
# Lấy kích thước file trước khi di chuyển.
        file_size = path.stat().st_size

        # Lưu các chunks và embeddings vào vector database.
        self.vector_store.add_documents(chunks)

        # Di chuyển file gốc vào thư mục lưu trữ.
        stored_path = (
            self._user_dir(user_id)
            / f"{document_id}{path.suffix.lower()}"
        )

        if path.resolve() != stored_path.resolve():
            shutil.move(str(path), str(stored_path))

        # Tạo metadata cho danh sách tài liệu.
        item = {
            "document_id": document_id,
            "filename": filename,
            "file_type": path.suffix.lower().lstrip("."),
            "file_size": file_size,
            "chunk_count": len(chunks),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "indexed",
        }

        manifest = self._read_manifest(user_id)
        manifest.insert(0, item)
        self._write_manifest(user_id, manifest)
        return item

    def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        return self._read_manifest(user_id)

    def search(self, query: str, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("Query không được để trống.")
        docs = self.vector_store.search(query.strip(), self._safe_user_id(user_id), limit)
        results = []
        for doc in docs:
            metadata = doc.metadata or {}
            page = metadata.get("page")
            results.append(
                {
                    "content": doc.page_content,
                    "filename": metadata.get("filename") or metadata.get("source", "Không rõ nguồn"),
                    "document_id": metadata.get("document_id"),
                    "page": int(page) + 1 if isinstance(page, int) else None,
                    "sheet": metadata.get("sheet"),
                    "chunk_index": metadata.get("chunk_index"),
                }
            )
        return results

    def delete_document(self, document_id: str, user_id: str) -> bool:
        manifest = self._read_manifest(user_id)
        target = next((item for item in manifest if item["document_id"] == document_id), None)
        if target is None:
            return False

        self.vector_store.delete_document(self._safe_user_id(user_id), document_id)
        filename = target.get("filename", "")
        # Stored file names include a document UUID, so same-name uploads do not collide.
        stored_path = self._user_dir(user_id) / f"{document_id}{Path(filename).suffix.lower()}"
        stored_path.unlink(missing_ok=True)
        self._write_manifest(
            user_id, [item for item in manifest if item["document_id"] != document_id]
        )
        return True

    def close(self) -> None:
        self.vector_store.close()
