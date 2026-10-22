from __future__ import annotations

import os
from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create one cached Google embedding client for this backend process."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Chưa cấu hình GOOGLE_API_KEY. Hãy thêm API key Google AI Studio vào backend/.env."
        )

    return GoogleGenerativeAIEmbeddings(
        model=os.getenv("RAG_EMBEDDING_MODEL", "gemini-embedding-001"),
        google_api_key=api_key,
    )
