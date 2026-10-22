from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Nạp .env ngay lập tức trước khi import bất kỳ thư viện LangChain nào
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")

# Đảm bảo tính tương thích 2 chiều giữa LANGSMITH_* và LANGCHAIN_*
_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
if _api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", _api_key)
    os.environ.setdefault("LANGSMITH_API_KEY", _api_key)

_tracing = os.getenv("LANGCHAIN_TRACING_V2") or os.getenv("LANGSMITH_TRACING")
if _tracing and _tracing.lower() in {"true", "1", "yes"}:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"

_project = os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT") or "agent-vrptw"
os.environ.setdefault("LANGCHAIN_PROJECT", _project)
os.environ.setdefault("LANGSMITH_PROJECT", _project)

_endpoint = os.getenv("LANGCHAIN_ENDPOINT") or os.getenv("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com"
os.environ.setdefault("LANGCHAIN_ENDPOINT", _endpoint)
os.environ.setdefault("LANGSMITH_ENDPOINT", _endpoint)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.agent.graph import build_agent_graph
from app.agent.memory import SQLiteMemoryManager
from app.api.router_api import api_router
from app.database.connect_db import dispose_engines
from app.rag.service import RAGService

logger = logging.getLogger(__name__)

DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Khởi tạo MCP, SQLite memory/checkpointer và LangGraph khi startup.
    Đóng các tài nguyên khi FastAPI shutdown.
    """
    backend_dir = Path(__file__).resolve().parent
    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Nạp biến môi trường trước khi khởi tạo LLM và tiến trình MCP con.
    load_dotenv(backend_dir / ".env")

    # Trạng thái mặc định, để health check không đọc nhầm tài nguyên cũ.
    app.state.mcp_client = None
    app.state.agent_tools = []
    app.state.mcp_tools = []
    app.state.memory_manager = None
    app.state.agent = None
    app.state.rag_service = None

    memory_manager: SQLiteMemoryManager | None = None
    rag_service: RAGService | None = None

    # Đảm bảo tiến trình MCP con dùng đúng Python/virtualenv và import được app.*.
    child_env = os.environ.copy()
    existing_pythonpath = child_env.get("PYTHONPATH")
    child_env["PYTHONPATH"] = (
        str(backend_dir)
        if not existing_pythonpath
        else str(backend_dir) + os.pathsep + existing_pythonpath
    )

    mcp_client = MultiServerMCPClient(
        {
            "vrptw": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "app.agent.mcp_server"],
                "cwd": str(backend_dir),
                "env": child_env,
            }
        }
    )

    try:
        # 1. Mở SQLite: checkpoint ngắn hạn và bảng memory dài hạn.
        memory_manager = SQLiteMemoryManager(
            data_dir / "agent_memory.sqlite3"
        )
        await memory_manager.open()

        # 2. Khởi tạo RAG service; Google API key chỉ cần khi upload/search.
        rag_service = RAGService(data_dir)

        # 3. Khám phá MCP tools.
        agent_tools = await mcp_client.get_tools()

        # 4. Compile LangGraph với MCP tools, memory tools, RAG và checkpointer.
        agent = build_agent_graph(
            agent_tools=agent_tools,
            checkpointer=memory_manager.checkpointer,
            memory_manager=memory_manager,
            rag_service=rag_service,
        )

        # 5. Đăng ký runtime để các API có thể sử dụng.
        app.state.mcp_client = mcp_client
        app.state.agent_tools = agent_tools
        app.state.mcp_tools = agent_tools
        app.state.memory_manager = memory_manager
        app.state.agent = agent
        app.state.rag_service = rag_service

        logger.info(
            "Agent runtime ready: %d MCP tools (%s); SQLite=%s",
            len(agent_tools),
            ", ".join(tool.name for tool in agent_tools),
            data_dir / "agent_memory.sqlite3",
        )
        logger.info("RAG runtime ready: Qdrant local store=%s", data_dir / "qdrant")

        yield

    except Exception:
        logger.exception(
            "Không thể khởi tạo AI Agent runtime; FastAPI không thể startup."
        )
        raise

    finally:
        # Ngăn request mới sử dụng runtime khi ứng dụng đang shutdown.
        app.state.agent = None
        app.state.rag_service = None
        app.state.memory_manager = None
        app.state.mcp_client = None
        app.state.agent_tools = []
        app.state.mcp_tools = []

        # Đảm bảo SQLAlchemy engines vẫn được dispose kể cả khi close SQLite lỗi.
        try:
            if memory_manager is not None:
                await memory_manager.close()
        finally:
            try:
                if rag_service is not None:
                    rag_service.close()
            finally:
                await dispose_engines()


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="AI Agent VRPTW API",
        description=(
            "API quản lý phương tiện, kho, đơn giao hàng và tối ưu tuyến đường; "
            "MCP tools, SQLite memory và LangGraph được khởi tạo trong lifespan."
        ),
        version="1.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/", tags=["Health"])
    def root():
        return {
            "message": "AI Agent VRPTW API is running",
            "docs": "/docs",
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        tools = getattr(app.state, "mcp_tools", [])
        agent = getattr(app.state, "agent", None)
        memory_manager = getattr(app.state, "memory_manager", None)

        return {
            "status": "ok",
            "mcp": "ready" if tools else "not_ready",
            "mcp_tool_count": len(tools),
            "agent_runtime": (
                "configured" if agent is not None else "not_configured"
            ),
            "rag": (
                "ready" if getattr(app.state, "rag_service", None) is not None else "not_ready"
            ),
            "sqlite_memory": (
                "ready" if memory_manager is not None else "not_ready"
            ),
            "langsmith_tracing": (
                "enabled"
                if os.getenv("LANGSMITH_TRACING", "").strip().lower() in {"true", "1", "yes"}
                and bool(os.getenv("LANGSMITH_API_KEY", "").strip())
                else "disabled_or_not_configured"
            ),
            "langsmith_project": os.getenv("LANGSMITH_PROJECT", "").strip() or None,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    # Không bật reload để tránh khởi tạo nhiều tiến trình MCP khi phát triển.
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
