from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.rag.service import RAGService


def build_rag_tools(rag_service: RAGService) -> list:
    @tool
    async def search_knowledge_base(
        query: str,
        limit: int = 5,
        *,
        config: RunnableConfig,
    ) -> str:
        """Search uploaded documents for evidence relevant to the user's question.

        Use this tool for questions about uploaded PDFs, Word documents, spreadsheets,
        CSV files, text files, Markdown, or source-code files. Do not use it for live
        vehicle/order/route data; those questions must use the business MCP tools.
        """
        configurable = config.get("configurable") or {}
        user_id = configurable.get("user_id") or "default"
        results = await __import__("asyncio").to_thread(
            rag_service.search, query, user_id, limit
        )
        if not results:
            return "Không tìm thấy đoạn tài liệu phù hợp với câu hỏi này."

        blocks = []
        for item in results:
            source = item["filename"]
            if item.get("page"):
                source += f", trang {item['page']}"
            if item.get("sheet"):
                source += f", sheet {item['sheet']}"
            blocks.append(f"Nguồn: {source}\nNội dung:\n{item['content']}")
        return "\n\n---\n\n".join(blocks)

    return [search_knowledge_base]
