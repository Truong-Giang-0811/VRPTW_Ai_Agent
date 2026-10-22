from __future__ import annotations

import os
from pathlib import Path
from threading import RLock

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from app.rag.embeddings import get_embeddings


class RAGVectorStore:
    """Persistent local Qdrant store with per-user and per-document filters."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = os.getenv("QDRANT_COLLECTION", "vrptw_documents")
        self.client = QdrantClient(path=str(self.data_dir))
        self._store: QdrantVectorStore | None = None
        self._lock = RLock()

    def _ensure_store(self) -> QdrantVectorStore:
        with self._lock:
            if self._store is not None:
                return self._store

            embeddings = get_embeddings()
            if not self.client.collection_exists(self.collection_name):
                # Gemini embedding dimensionality is determined from the active model,
                # rather than hard-coded, so a future model change is explicit/safe.
                vector = embeddings.embed_query("RAG collection dimension initialization")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=len(vector), distance=models.Distance.COSINE
                    ),
                )

            self._store = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embedding=embeddings,
                content_payload_key="page_content",
                metadata_payload_key="metadata",
            )
            return self._store

    @staticmethod
    def _user_filter(user_id: str, document_id: str | None = None) -> models.Filter:
        conditions = [
            models.FieldCondition(
                key="metadata.user_id", match=models.MatchValue(value=user_id)
            )
        ]
        if document_id:
            conditions.append(
                models.FieldCondition(
                    key="metadata.document_id", match=models.MatchValue(value=document_id)
                )
            )
        return models.Filter(must=conditions)

    def add_documents(self, documents: list[Document]) -> list[str]:
        with self._lock:
            return self._ensure_store().add_documents(documents)

    def search(self, query: str, user_id: str, limit: int = 5) -> list[Document]:
        with self._lock:
            store = self._ensure_store()
            return store.similarity_search(
                query,
                k=max(1, min(limit, 10)),
                filter=self._user_filter(user_id),
            )

    def delete_document(self, user_id: str, document_id: str) -> None:
        if not self.client.collection_exists(self.collection_name):
            return
        with self._lock:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=self._user_filter(user_id, document_id)
                ),
                wait=True,
            )

    def close(self) -> None:
        self.client.close()
