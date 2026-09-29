import os
import json
from dotenv import load_dotenv
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def query_service_health(service: str) -> str:
    """Check the health status of a service."""
    health_db = {
        "auth": "Degraded - 504 timeouts detected",
        "database": "Healthy",
        "payments": "Healthy"
    }
    return health_db.get(service.lower(), f"Service {service} not found.")

def search_remediation_runbooks(query: str, service: str = None) -> str:
    """Search for incident remediation runbooks based on a query."""
    embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-004", task_type="RETRIEVAL_QUERY")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url: return "Database not configured."
    
    query_vector = embeddings.embed_query(query)
    filter_json = json.dumps({"service": service}) if service else "{}"
    
    try:
        with psycopg.connect(db_url, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM match_incident_docs(%s::vector, 2, %s::jsonb)",
                    (query_vector, filter_json)
                )
                rows = cur.fetchall()
                if not rows:
                    return "No relevant runbooks found."
                return "\n---\n".join([r[0] for r in rows])
    except Exception as e:
        return f"Error searching runbooks: {e}"

def escalate_ticket(ticket_title: str, severity: str, details: str) -> str:
    """Escalate a critical incident to an engineer. ONLY call this if manual intervention is required."""
    return f"Ticket created: {ticket_title} (Severity: {severity})"

safe_tools = [query_service_health, search_remediation_runbooks]
sensitive_tools = [escalate_ticket]
all_tools = safe_tools + sensitive_tools

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0).bind_tools(all_tools)

def agent_node(state: AgentState):
    sys_msg = SystemMessage(
        content="You are an autonomous incident triage agent. "
        "First check service health. Then search runbooks. "
        "Escalate if manual intervention is needed or service stays degraded."
    )
    response = llm.invoke([sys_msg] + state["messages"])
    return {"messages": [response]}

def route_tools(state: AgentState) -> Literal["safe_tools", "sensitive_tools", "__end__"]:
    last_msg = state["messages"][-1]
    if not last_msg.tool_calls:
        return END
    
    # If ANY tool call is sensitive, route the whole batch to sensitive_tools (requires approval)
    for tc in last_msg.tool_calls:
        if tc["name"] in [t.__name__ for t in sensitive_tools]:
            return "sensitive_tools"
    
    return "safe_tools"

def execute_safe_tools(state: AgentState):
    last_msg = state["messages"][-1]
    results = []
    for tc in last_msg.tool_calls:
        if tc["name"] == "query_service_health":
            res = query_service_health(**tc["args"])
        elif tc["name"] == "search_remediation_runbooks":
            res = search_remediation_runbooks(**tc["args"])
        else:
            res = "Tool skipped."
        results.append(ToolMessage(content=str(res), tool_call_id=tc["id"], name=tc["name"]))
    return {"messages": results}

def execute_sensitive_tools(state: AgentState):
    last_msg = state["messages"][-1]
    results = []
    for tc in last_msg.tool_calls:
        if tc["name"] == "escalate_ticket":
            res = escalate_ticket(**tc["args"])
        else:
            res = "Tool skipped."
        results.append(ToolMessage(content=str(res), tool_call_id=tc["id"], name=tc["name"]))
    return {"messages": results}

def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("safe_tools", execute_safe_tools)
    builder.add_node("sensitive_tools", execute_sensitive_tools)
    
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_tools)
    builder.add_edge("safe_tools", "agent")
    builder.add_edge("sensitive_tools", "agent")
    
    return builder

def get_agent_app(pool=None):
    graph = build_graph()
    if pool:
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        return graph.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])
    return graph.compile(interrupt_before=["sensitive_tools"])
