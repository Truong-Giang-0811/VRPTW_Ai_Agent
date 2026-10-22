
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState


def build_agent_node(
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
):
    """
    Tạo Agent node.

    Nhiệm vụ:
    - Nhận lịch sử hội thoại từ AgentState.
    - Thêm system prompt vào ngữ cảnh LLM.
    - Cho phép LLM gọi MCP tools và memory tools.
    - Trả message mới về State.
    """

    # Cho phép LLM sử dụng các tool được cung cấp.
    model_with_tools = model.bind_tools(list(tools))

    async def agent_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
        messages = state["messages"]

        # Đưa system prompt vào đầu ngữ cảnh.
        # Không ghi system prompt vào State để tránh
        # lặp lại mỗi lần graph quay về Agent node.
        active_plan_id = state.get("active_route_plan_id")
        if active_plan_id is None:
            plan_context = (
                "Current selected route plan: NONE. If the user asks for a What-if "
                "scenario, ask them to select a saved route plan first. Do not guess a plan ID."
            )
        else:
            plan_context = (
                f"Current selected route plan ID: {active_plan_id}. For What-if requests, "
                "use this exact plan ID unless the user explicitly selects another plan. "
                "Never invent or substitute a plan ID."
            )

        input_messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=plan_context),
            *messages,
        ]

        # Gọi LLM theo cơ chế bất đồng bộ, truyền config để LangSmith trace đầy đủ.
        response = await model_with_tools.ainvoke(input_messages, config=config)

        # Reducer add_messages trong AgentState sẽ hợp nhất
        # message này vào lịch sử hiện tại.
        return {
            "messages": [response],
        }

    return agent_node


def build_tool_node(tools: Sequence[BaseTool]) -> ToolNode:
    """
    Tạo Tool node để thực thi MCP tools và memory tools.

    Việc quyết định có gọi tool hay không do graph.py
    điều hướng thông qua tools_condition.
    """
    return ToolNode(list(tools))


SENSITIVE_TOOLS = {
    "delete_database_record": "Xóa vĩnh viễn bản ghi khỏi cơ sở dữ liệu",
    "save_optimized_route_plan": "Lưu và áp dụng kế hoạch lộ trình chính thức vào cơ sở dữ liệu",
    "create_database_record": "Tạo bản ghi mới trong cơ sở dữ liệu",
    "update_database_record": "Cập nhật bản ghi trong cơ sở dữ liệu",
}


def build_approval_node():
    """
    Tạo Approval node cho cơ chế Human-in-the-loop (LangGraph Interrupt).

    Trước khi ToolNode chạy, node này kiểm tra nếu có tool thuộc SENSITIVE_TOOLS
    thì gọi hàm interrupt() để đóng băng graph và gửi thông tin lên giao diện
    chờ người dùng bấm duyệt (Approve) hoặc từ chối (Reject).
    """
    from langchain_core.messages import ToolMessage
    from langgraph.types import interrupt

    def approval_node(state: AgentState) -> dict:
        messages = state.get("messages", [])
        if not messages:
            return {}

        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        if not tool_calls:
            return {}

        rejected_tool_messages = []
        any_rejected = False

        for call in tool_calls:
            tool_name = call.get("name")
            if tool_name in SENSITIVE_TOOLS:
                desc = SENSITIVE_TOOLS[tool_name]
                # Kích hoạt điểm dừng interrupt của LangGraph
                feedback = interrupt({
                    "action": "human_approval_required",
                    "tool_name": tool_name,
                    "tool_call_id": call.get("id"),
                    "args": call.get("args", {}),
                    "description": desc,
                })

                is_approved = False
                reason = "Người dùng đã từ chối thao tác này."
                if isinstance(feedback, dict):
                    is_approved = bool(feedback.get("approved"))
                    if feedback.get("reason"):
                        reason = str(feedback["reason"])
                elif isinstance(feedback, bool):
                    is_approved = feedback

                if not is_approved:
                    any_rejected = True
                    rejected_tool_messages.append(
                        ToolMessage(
                            tool_call_id=call["id"],
                            content=f"Thao tác '{tool_name}' đã bị người dùng TỪ CHỐI hủy bỏ: {reason}",
                            name=tool_name,
                        )
                    )

        # Nếu có tool bị từ chối, đảm bảo tất cả tool_calls trong lượt này đều có ToolMessage tương ứng
        if any_rejected:
            handled_ids = {m.tool_call_id for m in rejected_tool_messages}
            for call in tool_calls:
                call_id = call.get("id")
                if call_id not in handled_ids:
                    rejected_tool_messages.append(
                        ToolMessage(
                            tool_call_id=call_id,
                            content="Hủy do thao tác liên quan trong cùng phiên bị từ chối.",
                            name=call.get("name"),
                        )
                    )
            return {"messages": rejected_tool_messages}

        return {}

    return approval_node
