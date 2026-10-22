import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.agent.memory import SQLiteMemoryManager
from app.agent.nodes import build_agent_node, build_approval_node, build_tool_node
from app.agent.state import AgentState
from app.rag.service import RAGService
from app.rag.tools import build_rag_tools

# Load the backend .env explicitly, regardless of the working directory.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


SYSTEM_PROMPT = """\
You are a logistics assistant for delivery management and VRPTW \
(Vehicle Routing Problem with Time Windows) optimization.

# Language and format (highest priority)
- Reply in the user's language. If the user writes Vietnamese, the ENTIRE reply \
must be in Vietnamese. Never insert Chinese characters or words from any other \
language. Technical terms (VRPTW, GA, ACO, PSO, depot, time window) may stay in English.
- Output plain text only. Do not use Markdown: no **bold**, no # headings, \
no tables, no code blocks, no emoji.
- For lists, put one item per line starting with "- ". For multi-route results, \
write one short line per route.

# Capabilities
- Business tools (MCP): query and manage orders, vehicles and depots; run route \
optimization; compare optimization algorithms; save and retrieve route plans; run \
read-only What-if scenarios for a selected saved route plan.
- Long-term memory tools: `save_long_term_memory` and `search_long_term_memory`.
- Knowledge base tool: `search_knowledge_base` for user-uploaded documents.
- For questions that depend on uploaded documents, call `search_knowledge_base`; ground the answer in retrieved passages, cite source/page when available, and state when no relevant evidence was found. Use MCP tools for live business data instead of RAG. \

# Core rules
1. Ground every business answer in tool output. Never invent orders, vehicles, \
distances, costs, or optimization results. If a tool fails or returns nothing, \
say so plainly and report the error.
2. Call tools when the answer depends on live data. Answer directly, without \
tools, for general explanations (e.g. how VRPTW works).
3. If required parameters are missing or ambiguous, ask one short clarifying \
question instead of guessing. Do not ask for information you can look up with a tool.
4. Before any action that modifies or deletes data, state what will change and \
get the user's confirmation, unless they already gave an explicit instruction.
5. When presenting optimization results, include the key figures returned by \
the tool (e.g. total distance, number of vehicles used, time-window violations) \
and name the algorithm used. When comparing algorithms, compare them on the same input.

6. For a What-if request, call `run_what_if` using the current selected route plan ID \
provided in the system context. Express changes using the documented schema. The tool \
only creates an in-memory scenario and never saves it. Do not call save tools unless \
the user explicitly asks to apply/save a result. If no selected plan ID is provided, ask \
the user to select a saved plan before running What-if.
7. Supported What-if changes: `vehicle_count`; `vehicle_capacity_kg` for all selected \
vehicles; `vehicle_capacity_changes` for a specific vehicle by `vehicle_number` (1-based \
position in the selected plan) or `vehicle_id`; `add_order_ids` for pending orders on the \
same delivery date; `exclude_order_ids` for orders in the selected plan; and `order_overrides` \
for demand, coordinates, service duration, or opening/closing time. Do not claim a scenario \
was run unless the tool returned a result.

# Long-term memory
- Memory holds durable user context only: preferences, standing rules, recurring \
constraints, and the user's own stated facts.
- Save only when the information is likely to be useful in future conversations, \
or when the user asks you to remember it. Use a short, stable, descriptive \
`memory_key` (e.g. `preferred_algorithm`) and a category such as `preference` or `rule`. \
Reusing a key overwrites the old value, so reuse it when updating.
- Do not save one-off requests, temporary results, or anything the business tools \
can return again.
- Never treat memory as the source of truth for business data. Orders, vehicles, \
and routes must always come from the business tools, because memory may be outdated. \
If memory conflicts with tool output, trust the tool.
- Search memory when the user refers to past preferences or rules, or when a \
saved setting could change your answer.

# Style
- Be concise and direct. Lead with the result, then give details only if useful.
- When asked what you can do, answer in at most 4 short sentences and ask what \
the user needs. Do not list every tool.
- Before sending, check that the reply follows the language and format rules above.
"""

DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _get_user_id(config: RunnableConfig) -> str:
    """Read user_id from config["configurable"]; fall back to 'default'."""
    return (config.get("configurable") or {}).get("user_id") or "default"


def build_memory_tools(memory_manager: SQLiteMemoryManager) -> list:
    """Create the long-term memory tools, scoped per user via config."""

    @tool
    async def save_long_term_memory(
        memory_key: str,
        content: str,
        category: str = "general",
        *,
        config: RunnableConfig,
    ) -> str:
        """Save durable information for use in future conversations.

        Args:
            memory_key: Short, stable identifier. Reusing a key overwrites the old value.
            content: The information to remember.
            category: Group label, e.g. "preference" or "rule".
        """
        await memory_manager.save_memory(
            memory_key=memory_key,
            content=content,
            category=category,
            user_id=_get_user_id(config),
        )
        return f"Saved memory with key '{memory_key}'."

    @tool
    async def search_long_term_memory(
        keyword: str,
        limit: int = 10,
        *,
        config: RunnableConfig,
    ) -> str:
        """Search previously saved long-term memories.

        Args:
            keyword: Search term matched against memory keys and content.
            limit: Maximum number of results.
        """
        memories = await memory_manager.search_memories(
            keyword=keyword,
            limit=limit,
            user_id=_get_user_id(config),
        )

        if not memories:
            return "No matching memories found."

        return "\n".join(
            f"- [{item['category']}] {item['memory_key']}: {item['content']}"
            for item in memories
        )

    return [save_long_term_memory, search_long_term_memory]


def build_agent_graph(
    agent_tools: list,
    checkpointer,
    memory_manager: SQLiteMemoryManager,
    rag_service: RAGService | None = None,
):
    """
    Build the ReAct graph for the VRPTW agent.

    Flow:
        START -> agent -> tools -> agent -> ... -> END
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    model = ChatOpenAI(
        model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
        temperature=0.2,
        openai_api_base=OPENROUTER_BASE_URL,
        openai_api_key=api_key,
        streaming=True,
    )

    # Combine MCP tools, long-term memory tools, and document retrieval.
    all_tools = [*agent_tools, *build_memory_tools(memory_manager)]
    if rag_service is not None:
        all_tools.extend(build_rag_tools(rag_service))

    agent_node = build_agent_node(
        model=model,
        tools=all_tools,
        system_prompt=SYSTEM_PROMPT,
    )
    approval_node = build_approval_node()
    tool_node = build_tool_node(all_tools)

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")

    # Nếu LLM yêu cầu gọi tool, chuyển qua approval node để kiểm tra quyền
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "approval", END: END},
    )

    # Sau approval: nếu bị hủy (có ToolMessage từ chối) -> quay về agent để phản hồi
    # nếu được duyệt -> đi tiếp vào tools node
    def route_after_approval(state: AgentState) -> str:
        messages = state.get("messages", [])
        if messages and getattr(messages[-1], "type", None) == "tool":
            return "agent"
        return "tools"

    workflow.add_conditional_edges(
        "approval",
        route_after_approval,
        {"tools": "tools", "agent": "agent"},
    )

    # Sau khi chạy tool xong, quay lại agent để tổng hợp câu trả lời
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=checkpointer)

# if __name__ == "__main__":
#     app = build_agent_graph([], None, None)
#     app.get_graph().print_ascii()
