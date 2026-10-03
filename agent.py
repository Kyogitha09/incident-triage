import os
import json
from typing import Annotated, Sequence, TypedDict, Any
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool
from google import genai
from google.genai import types

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

# Global connection pool cache
_db_pool: ConnectionPool | None = None


def get_db_pool() -> ConnectionPool:
    """Return a psycopg_pool ConnectionPool tuned for Supabase transaction pooler."""
    global _db_pool
    if _db_pool is None:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        _db_pool = ConnectionPool(
            db_url,
            min_size=1,
            max_size=10,
            timeout=15,
            kwargs={
                "autocommit": True,
                "prepare_threshold": None,
            },
        )
    return _db_pool


# Mock catalog for service health
MOCK_SERVICE_CATALOG = {
    "auth": {
        "status": "degraded",
        "error_rate": "18.4%",
        "latency_p99": "2400ms",
        "details": "Redis token cache connection timeout. Token refresh requests failing with 504.",
    },
    "database": {
        "status": "degraded",
        "error_rate": "4.2%",
        "latency_p99": "4800ms",
        "details": "High connection count nearing pool limit. Multiple long-running analytical queries.",
    },
    "payments": {
        "status": "healthy",
        "error_rate": "0.01%",
        "latency_p99": "180ms",
        "details": "All payment gateway webhooks and processing normal.",
    },
}


@tool
def query_service_health(service_name: str) -> str:
    """Check the operational health and metrics of a backend service."""
    service_key = service_name.strip().lower()
    if service_key in MOCK_SERVICE_CATALOG:
        data = MOCK_SERVICE_CATALOG[service_key]
        return json.dumps({"service": service_key, **data})
    return f"Service '{service_name}' not found in service health catalog. Known services: {list(MOCK_SERVICE_CATALOG.keys())}"


@tool
def search_remediation_runbooks(query: str, service: str | None = None) -> str:
    """Search internal remediation runbooks by semantic similarity."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY is not configured."

    try:
        client = genai.Client(api_key=api_key)
        embed_result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )
        query_embedding = embed_result.embeddings[0].values
    except Exception as e:
        return f"Failed to compute embedding for query: {e}"

    filter_json = json.dumps({"service": service.lower()}) if service else "{}"
    pool = get_db_pool()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, metadata, similarity
                FROM match_incident_docs(%s::vector, %s::int, %s::jsonb);
                """,
                (query_embedding, 2, filter_json),
            )
            rows = cur.fetchall()

    if not rows:
        return "No relevant runbooks found."

    results = []
    for row in rows:
        content, metadata, similarity = row
        results.append(f"Runbook ({metadata.get('service', 'general')}): {content}")

    return "\n\n".join(results)


def extract_text(content: Any) -> str:
    """Normalise message content (which could be string, list of dicts/blocks) to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    parts.append(item["text"])
                elif "content" in item:
                    parts.append(str(item["content"]))
                else:
                    parts.append(json.dumps(item))
            else:
                parts.append(str(item))
        return " ".join(parts).strip()
    return str(content)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def escalate_ticket(ticket_title: str, severity: str) -> str:
    """Escalate incident by creating an urgent on-call ticket. (CRITICAL: Requires Human Approval)."""
    return f"Ticket created: '{ticket_title}' [Severity: {severity.upper()}]. On-call team paged."


SYSTEM_PROMPT = (
    "You are an Autonomous Incident Triage Agent. "
    "When investigating an incident report:\n"
    "1. FIRST ALWAYS inspect service health using `query_service_health` for any service mentioned or suspected.\n"
    "2. THEN search remediation runbooks using `search_remediation_runbooks` for relevant recovery steps.\n"
    "3. Explain the findings, current operational health, and recommended remediation steps.\n"
    "4. If manual intervention is needed or the service remains degraded, call `escalate_ticket` to page on-call engineers.\n"
    "Be concise, analytical, and prioritize incident resolution."
)

SAFE_TOOLS = [query_service_health, search_remediation_runbooks]
SAFE_TOOLS_BY_NAME = {t.name: t for t in SAFE_TOOLS}

SENSITIVE_TOOLS = [escalate_ticket]
SENSITIVE_TOOLS_BY_NAME = {t.name: t for t in SENSITIVE_TOOLS}

ALL_TOOLS = SAFE_TOOLS + SENSITIVE_TOOLS


def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Invoke LLM with bound tools."""
    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.0)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    messages = list(state["messages"])
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def execute_safe_tools(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Execute safe tool calls requested by the model."""
    last_message = state["messages"][-1]
    tool_messages = []
    for tool_call in getattr(last_message, "tool_calls", []):
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        call_id = tool_call["id"]
        target_tool = SAFE_TOOLS_BY_NAME.get(tool_name)
        if target_tool:
            result = target_tool.invoke(tool_args)
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=call_id))
    return {"messages": tool_messages}


def execute_sensitive_tools(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Execute sensitive tool calls (runs only after human approval)."""
    last_message = state["messages"][-1]
    tool_messages = []
    for tool_call in getattr(last_message, "tool_calls", []):
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        call_id = tool_call["id"]
        target_tool = SENSITIVE_TOOLS_BY_NAME.get(tool_name)
        if target_tool:
            result = target_tool.invoke(tool_args)
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=call_id))
    return {"messages": tool_messages}


def route_tools(state: AgentState) -> str:
    """Route tool calls: sensitive_tools if ANY call is escalate_ticket, else safe_tools, else END."""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    if not tool_calls:
        return END

    # If ANY tool call is sensitive, pause for human approval
    if any(tc["name"] == "escalate_ticket" for tc in tool_calls):
        return "sensitive_tools"
    return "safe_tools"


def create_agent_graph():
    """Build the LangGraph state graph with separate safe and sensitive tool nodes."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("safe_tools", execute_safe_tools)
    workflow.add_node("sensitive_tools", execute_sensitive_tools)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        route_tools,
        {
            "safe_tools": "safe_tools",
            "sensitive_tools": "sensitive_tools",
            END: END,
        },
    )
    workflow.add_edge("safe_tools", "agent")
    workflow.add_edge("sensitive_tools", "agent")

    return workflow


def get_agent_app(pool: ConnectionPool | None = None):
    """Return the compiled agent graph with Postgres checkpointer and HITL interrupt."""
    active_pool = pool or get_db_pool()
    checkpointer = PostgresSaver(active_pool)
    checkpointer.setup()
    workflow = create_agent_graph()
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["sensitive_tools"],
    )

