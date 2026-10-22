from __future__ import annotations

import json
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])


class AgentChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Câu lệnh tự nhiên của người dùng",
    )
    thread_id: str | None = Field(
        default=None,
        description="ID phiên hội thoại; bỏ trống để tạo phiên mới",
    )
    user_id: str = Field(
        default="default",
        min_length=1,
        max_length=128,
        description="ID người dùng",
    )
    active_route_plan_id: int | None = Field(
        default=None,
        gt=0,
        description="ID kế hoạch tuyến đường đang được chọn; null nếu chưa chọn",
    )


class AgentChatResponse(BaseModel):
    success: bool
    thread_id: str
    reply: str
    requires_action: bool = False
    action_data: dict | None = None


def _extract_interrupt(state_or_result) -> dict | None:
    """Trích xuất payload của interrupt từ State hoặc kết quả invoke."""
    if hasattr(state_or_result, "tasks"):
        for task in state_or_result.tasks:
            for intr in getattr(task, "interrupts", []):
                val = getattr(intr, "value", None)
                if val:
                    return val
    elif isinstance(state_or_result, dict):
        interrupts = state_or_result.get("__interrupt__")
        if interrupts and len(interrupts) > 0:
            return getattr(interrupts[0], "value", None)
    return None


class AgentThreadSummary(BaseModel):
    thread_id: str
    title: str
    preview: str
    message_count: int
    updated_at: str | None = None


class AgentMessage(BaseModel):
    role: str
    text: str


class AgentThreadHistoryResponse(BaseModel):
    success: bool
    thread_id: str
    messages: list[AgentMessage]


TOOL_STATUS_MESSAGES = {
    "run_what_if": "Đang giả lập kịch bản What-if...",
    "optimize_routes_from_database": "Đang chạy giải thuật tối ưu lộ trình...",
    "list_database_records": "Đang kiểm tra dữ liệu kho, xe và đơn hàng...",
    "get_database_record": "Đang kiểm tra dữ liệu kho, xe và đơn hàng...",
    "save_optimized_route_plan": "Đang lưu kế hoạch lộ trình vào hệ thống...",
    "search_knowledge_base": "Đang tìm kiếm trong tài liệu đã tải lên...",
}


def _tool_status(tool_name: str) -> str:
    return TOOL_STATUS_MESSAGES.get(
        tool_name,
        f"Đang thực hiện tác vụ {tool_name}...",
    )


def _extract_text(content) -> str:
    """Chuẩn hóa content của AIMessage về text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)

    return ""


def _build_run_config(payload: AgentChatRequest, thread_id: str) -> dict:
    """Tạo config dùng chung cho synchronous và streaming chat."""
    run_config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": payload.user_id,
            "active_route_plan_id": payload.active_route_plan_id,
        },
        "run_name": "vrptw_agent_chat",
        "tags": ["vrptw-agent", "chat"],
        "metadata": {
            "thread_id": thread_id,
            "user_id": payload.user_id,
            "agent_type": "vrptw_logistics_agent",
            "active_route_plan_id": payload.active_route_plan_id,
        },
    }

    tracing_enabled = (
        os.getenv("LANGCHAIN_TRACING_V2", "").lower() in {"true", "1", "yes"}
        or os.getenv("LANGSMITH_TRACING", "").lower() in {"true", "1", "yes"}
    )
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if tracing_enabled and api_key:
        try:
            from langchain_core.tracers.langchain import LangChainTracer

            project_name = (
                os.getenv("LANGCHAIN_PROJECT")
                or os.getenv("LANGSMITH_PROJECT")
                or "agent-vrptw"
            )
            run_config["callbacks"] = [LangChainTracer(project_name=project_name)]
        except Exception as tracer_err:
            logger.warning("Không thể nạp LangChainTracer: %s", tracer_err)

    return run_config


def _sse_event(event_name: str, payload: dict) -> str:
    """Đóng gói một event SSE chuẩn."""
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event_name}\ndata: {data}\n\n"


@router.get(
    "/threads",
    response_model=list[AgentThreadSummary],
)
async def list_agent_threads(
    request: Request,
    user_id: str = "default",
    limit: int = 50,
):
    """Liệt kê các cuộc trò chuyện đã được LangGraph checkpoint lưu."""
    memory_manager = getattr(request.app.state, "memory_manager", None)
    if memory_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bộ nhớ Agent chưa sẵn sàng.",
        )

    try:
        return await memory_manager.list_threads(user_id=user_id, limit=limit)
    except Exception:
        logger.exception("Không thể lấy danh sách thread")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải lịch sử hội thoại.",
        ) from None


@router.get(
    "/threads/{thread_id}",
    response_model=AgentThreadHistoryResponse,
)
async def get_agent_thread_history(
    thread_id: str,
    request: Request,
    user_id: str = "default",
):
    """Lấy toàn bộ message của một cuộc trò chuyện từ checkpoint cuối."""
    memory_manager = getattr(request.app.state, "memory_manager", None)
    if memory_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bộ nhớ Agent chưa sẵn sàng.",
        )

    try:
        messages = await memory_manager.get_thread_messages(
            thread_id=thread_id,
            user_id=user_id,
        )
    except Exception:
        logger.exception("Không thể lấy lịch sử thread=%s", thread_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải lịch sử hội thoại.",
        ) from None

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc trò chuyện hoặc cuộc trò chuyện không thuộc người dùng này.",
        )

    return AgentThreadHistoryResponse(
        success=True,
        thread_id=thread_id,
        messages=messages,
    )


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_with_agent(
    payload: AgentChatRequest,
    request: Request,
) -> AgentChatResponse:
    """Endpoint đồng bộ cũ, giữ nguyên để tương thích ngược."""
    agent = getattr(request.app.state, "agent", None)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent chưa sẵn sàng. Vui lòng thử lại sau.",
        )

    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nội dung tin nhắn không được để trống.",
        )

    thread_id = payload.thread_id or str(uuid4())
    run_config = _build_run_config(payload, thread_id)

    try:
        result = await agent.ainvoke(
            {
                "messages": [{"role": "user", "content": message}],
                "active_route_plan_id": payload.active_route_plan_id,
            },
            config=run_config,
        )

        reply = ""
        for item in reversed(result.get("messages", [])):
            if getattr(item, "type", None) == "ai":
                reply = _extract_text(getattr(item, "content", ""))
                if reply.strip():
                    break

        interrupt_data = _extract_interrupt(result)
        if interrupt_data:
            if not reply.strip():
                reply = "Thao tác này cần bạn xác nhận trước khi thực hiện."
            return AgentChatResponse(
                success=True,
                thread_id=thread_id,
                reply=reply,
                requires_action=True,
                action_data=interrupt_data,
            )

        if not reply.strip():
            reply = "Agent đã xử lý yêu cầu nhưng chưa tạo được câu trả lời."

        return AgentChatResponse(success=True, thread_id=thread_id, reply=reply)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Agent xử lý yêu cầu thất bại. thread_id=%s", thread_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent gặp lỗi khi xử lý yêu cầu. Vui lòng thử lại.",
        ) from None


@router.post("/chat/stream")
async def stream_chat_with_agent(
    payload: AgentChatRequest,
    request: Request,
):
    """Stream trạng thái tool và token trả lời của LangGraph qua SSE."""
    agent = getattr(request.app.state, "agent", None)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent chưa sẵn sàng. Vui lòng thử lại sau.",
        )

    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nội dung tin nhắn không được để trống.",
        )

    thread_id = payload.thread_id or str(uuid4())
    run_config = _build_run_config(payload, thread_id)

    async def event_generator():
        full_reply = ""
        emitted_text = False
        done_sent = False

        try:
            async for event in agent.astream_events(
                {
                    "messages": [{"role": "user", "content": message}],
                    "active_route_plan_id": payload.active_route_plan_id,
                },
                config=run_config,
                version="v2",
            ):
                if await request.is_disconnected():
                    logger.info("SSE client disconnected. thread_id=%s", thread_id)
                    return

                event_type = event.get("event")
                event_name = event.get("name", "")
                event_data = event.get("data") or {}

                if event_type == "on_tool_start":
                    yield _sse_event(
                        "status",
                        {"message": _tool_status(event_name)},
                    )
                    continue

                if event_type == "on_tool_end":
                    yield _sse_event(
                        "status",
                        {"message": "Đã hoàn tất tính toán, đang tổng hợp kết quả..."},
                    )
                    continue

                if event_type == "on_chat_model_stream":
                    chunk = event_data.get("chunk")
                    content = _extract_text(getattr(chunk, "content", ""))
                    if not content:
                        continue

                    full_reply += content
                    emitted_text = True
                    yield _sse_event("token", {"delta": content})
                    continue

                # Fallback cho trường hợp provider không phát token stream
                # nhưng vẫn trả output ở on_chat_model_end.
                if event_type == "on_chat_model_end" and not emitted_text:
                    output = event_data.get("output")
                    content = _extract_text(getattr(output, "content", ""))
                    if content:
                        full_reply += content
                        emitted_text = True
                        yield _sse_event("token", {"delta": content})

            # Kiểm tra xem có interrupt cần duyệt không
            state = await agent.aget_state(run_config)
            interrupt_data = _extract_interrupt(state)

            if interrupt_data:
                action_reply = full_reply or "Thao tác này cần bạn xác nhận trước khi thực hiện."
                yield _sse_event(
                    "action_required",
                    {
                        "thread_id": thread_id,
                        "action_data": interrupt_data,
                        "message": action_reply,
                    },
                )
                yield _sse_event(
                    "done",
                    {
                        "success": True,
                        "thread_id": thread_id,
                        "reply": action_reply,
                        "requires_action": True,
                        "action_data": interrupt_data,
                        "routeResult": None,
                    },
                )
                done_sent = True
                return

            if not full_reply.strip():
                full_reply = "Agent đã xử lý yêu cầu nhưng chưa tạo được câu trả lời."

            yield _sse_event(
                "done",
                {
                    "success": True,
                    "thread_id": thread_id,
                    "reply": full_reply,
                    "requires_action": False,
                    "action_data": None,
                    "routeResult": None,
                },
            )
            done_sent = True

        except Exception as exc:
            logger.exception("SSE Agent xử lý thất bại. thread_id=%s", thread_id)
            if not done_sent:
                yield _sse_event(
                    "error",
                    {
                        "message": "Agent gặp lỗi khi xử lý yêu cầu. Vui lòng thử lại.",
                        "thread_id": thread_id,
                        "detail": str(exc),
                    },
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class AgentResumeRequest(BaseModel):
    thread_id: str
    approved: bool
    reason: str | None = None
    user_id: str = "default"
    active_route_plan_id: int | None = None


@router.post(
    "/resume",
    response_model=AgentChatResponse,
    status_code=status.HTTP_200_OK,
)
async def resume_agent_action(
    payload: AgentResumeRequest,
    request: Request,
) -> AgentChatResponse:
    """
    Tiếp tục luồng LangGraph sau khi người dùng phê duyệt hoặc từ chối hành động.
    """
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent chưa sẵn sàng. Vui lòng thử lại sau.",
        )

    run_config = {
        "configurable": {
            "thread_id": payload.thread_id,
            "user_id": payload.user_id,
            "active_route_plan_id": payload.active_route_plan_id,
        },
        "run_name": "vrptw_agent_resume",
        "tags": ["vrptw-agent", "resume"],
        "metadata": {
            "thread_id": payload.thread_id,
            "user_id": payload.user_id,
            "agent_type": "vrptw_logistics_agent",
            "active_route_plan_id": payload.active_route_plan_id,
        },
    }

    try:
        from langgraph.types import Command

        feedback = {
            "approved": payload.approved,
            "reason": payload.reason or ("Đã chấp thuận." if payload.approved else "Người dùng đã từ chối thao tác này."),
        }

        result = await agent.ainvoke(Command(resume=feedback), config=run_config)

        messages = result.get("messages", []) if isinstance(result, dict) else []
        reply = ""
        for item in reversed(messages):
            if getattr(item, "type", None) == "ai":
                reply = _extract_text(getattr(item, "content", ""))
                if reply.strip():
                    break

        interrupt_data = _extract_interrupt(result)

        if not reply.strip():
            reply = "Đã thực hiện xong thao tác." if payload.approved else "Đã hủy bỏ thao tác theo yêu cầu của bạn."

        return AgentChatResponse(
            success=True,
            thread_id=payload.thread_id,
            reply=reply,
            requires_action=bool(interrupt_data),
            action_data=interrupt_data,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Agent resume thất bại. thread_id=%s", payload.thread_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tiếp tục xử lý yêu cầu. Vui lòng thử lại.",
        ) from None
