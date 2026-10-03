import json
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from agent import (
    query_service_health,
    extract_text,
    execute_safe_tools,
    route_tools,
    create_agent_graph,
    get_agent_app,
)


def test_query_service_health_known():
    res = query_service_health.invoke({"service_name": "auth"})
    data = json.loads(res)
    assert data["service"] == "auth"
    assert data["status"] == "degraded"
    assert "error_rate" in data


def test_query_service_health_unknown():
    res = query_service_health.invoke({"service_name": "billing"})
    assert "not found" in res.lower()
    assert "billing" in res


def test_extract_text():
    assert extract_text("simple text") == "simple text"
    assert extract_text([{"text": "Hello"}, {"text": "World"}]) == "Hello World"
    assert extract_text(["one", "two"]) == "one two"


def test_route_tools():
    msg_with_tool = AIMessage(
        content="",
        tool_calls=[{"name": "query_service_health", "args": {"service_name": "auth"}, "id": "call-1"}],
    )
    assert route_tools({"messages": [msg_with_tool]}) == "safe_tools"

    msg_without_tool = AIMessage(content="All services look good.")
    assert route_tools({"messages": [msg_without_tool]}) == "__end__"


def test_execute_safe_tools():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "query_service_health", "args": {"service_name": "auth"}, "id": "call-1"}
                ],
            )
        ]
    }
    result = execute_safe_tools(state)
    assert len(result["messages"]) == 1
    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "call-1"
    assert "degraded" in tool_msg.content


def test_graph_flow_mock_llm():
    """Verify agent -> safe_tools -> agent loop and state termination."""
    mock_responses = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "query_service_health", "args": {"service_name": "auth"}, "id": "call-1"}
            ],
        ),
        AIMessage(content="Auth service is degraded. Checked Redis cache."),
    ]

    call_count = 0

    def mock_call_model(state):
        nonlocal call_count
        resp = mock_responses[call_count]
        call_count += 1
        return {"messages": [resp]}

    workflow = create_agent_graph()
    # Replace the agent node with our mock
    workflow.nodes["agent"].runnable = mock_call_model
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "test-thread-1"}}
    res = app.invoke({"messages": [HumanMessage(content="Auth is failing")]}, config)

    assert len(res["messages"]) == 4  # Human, AI tool call, Tool result, Final AI
    assert "degraded" in res["messages"][-1].content or "Redis" in res["messages"][-1].content


def test_state_persistence_survives_restart():
    """Simulate restart by compiling two graph instances over the same checkpointer."""
    checkpointer = MemorySaver()

    def mock_model(state):
        return {"messages": [AIMessage(content=f"History count: {len(state['messages'])}")]}

    # Process 1
    w1 = create_agent_graph()
    w1.nodes["agent"].runnable = mock_model
    app1 = w1.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "thread-persistent-1"}}
    app1.invoke({"messages": [HumanMessage(content="First message")]}, config)

    # Process 2 (new compiled instance with same checkpointer / thread_id)
    w2 = create_agent_graph()
    w2.nodes["agent"].runnable = mock_model
    app2 = w2.compile(checkpointer=checkpointer)

    res2 = app2.invoke({"messages": [HumanMessage(content="Second message")]}, config)
    # The message history should have: First Human, First AI, Second Human, Second AI
    assert len(res2["messages"]) == 4
