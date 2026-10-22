from __future__ import annotations

from pathlib import Path

import pandas as pd
from langchain_community.document_loaders import CSVLoader, Docx2txtLoader, PyPDFLoader
from langchain_core.documents import Document

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".csv", ".xlsx", ".xls", ".txt", ".md", ".py"}


def load_document(file_path: str | Path) -> list[Document]:
    """Load a supported file into LangChain Documents with source metadata."""
    path = Path(file_path)
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Định dạng {extension or '(không có phần mở rộng)'} chưa được hỗ trợ.")

    if extension == ".pdf":
        documents = PyPDFLoader(str(path)).load()
    elif extension == ".docx":
        documents = Docx2txtLoader(str(path)).load()
    elif extension == ".csv":
        documents = CSVLoader(str(path), autodetect_encoding=True).load()
    elif extension in {".xlsx", ".xls"}:
        workbook = pd.read_excel(path, sheet_name=None)
        documents = []
        for sheet_name, dataframe in workbook.items():
            if dataframe.empty and len(dataframe.columns) == 0:
                continue
            text = dataframe.fillna("").to_csv(index=False)
            if text.strip():
                documents.append(
                    Document(
                        page_content=f"Sheet: {sheet_name}\n{text}",
                        metadata={"source": path.name, "sheet": str(sheet_name)},
                    )
                )
    else:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        documents = [Document(page_content=text, metadata={"source": path.name})]

    # Normalize source metadata and discard pages/sheets with no extractable text.
    normalized: list[Document] = []
    for document in documents:
        if not document.page_content or not document.page_content.strip():
            continue
        metadata = dict(document.metadata or {})
        metadata["source"] = path.name
        normalized.append(Document(page_content=document.page_content, metadata=metadata))

    if not normalized:
        raise ValueError(
            "Không trích xuất được văn bản từ file. Nếu đây là PDF scan, cần OCR trước khi đưa vào RAG."
        )
    return normalized
