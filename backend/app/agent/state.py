
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State dùng chung trong quá trình LangGraph thực thi.

    messages:
        Lịch sử hội thoại, bao gồm tin nhắn người dùng,
        phản hồi của LLM và kết quả MCP tools.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    # Context from the currently selected plan in the frontend. This is
    # overwritten by each chat request and is not business data itself.
    active_route_plan_id: int | None
