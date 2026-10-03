from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from agent import create_agent_graph


def test_hitl_escalation_pauses_before_sensitive_tools():
    """Verify that calling escalate_ticket causes the graph to pause before sensitive_tools."""
    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "escalate_ticket",
                "args": {"ticket_title": "Auth failure", "severity": "P1"},
                "id": "call-esc-1",
            }
        ],
    )

    workflow = create_agent_graph()
    workflow.nodes["agent"].runnable = lambda state: {"messages": [mock_response]}
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])

    config = {"configurable": {"thread_id": "hitl-pause-test"}}
    app.invoke({"messages": [HumanMessage(content="Critical failure, escalate now!")]}, config)

    state = app.get_state(config)
    # Graph execution must pause with sensitive_tools as the next task
    assert "sensitive_tools" in state.next
    # No ToolMessage or executed ticket should exist yet
    assert not any(isinstance(m, ToolMessage) for m in state.values["messages"])


def test_hitl_approval_executes_escalation():
    """Verify that approving (invoke(None)) runs escalate_ticket and finishes."""
    mock_responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "escalate_ticket",
                    "args": {"ticket_title": "Database down", "severity": "P0"},
                    "id": "call-esc-2",
                }
            ],
        ),
        AIMessage(content="Ticket escalated and team paged successfully."),
    ]

    call_count = 0

    def mock_model(state):
        nonlocal call_count
        resp = mock_responses[call_count]
        call_count += 1
        return {"messages": [resp]}

    workflow = create_agent_graph()
    workflow.nodes["agent"].runnable = mock_model
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])

    config = {"configurable": {"thread_id": "hitl-approve-test"}}
    # 1. Trigger triage -> pauses
    app.invoke({"messages": [HumanMessage(content="DB is down!")]}, config)
    assert "sensitive_tools" in app.get_state(config).next

    # 2. Engineer approves -> resumes execution
    res = app.invoke(None, config)
    assert "sensitive_tools" not in app.get_state(config).next
    # ToolMessage must exist from escalate_ticket
    tool_messages = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert "Ticket created" in tool_messages[0].content


def test_hitl_rejection_does_not_execute_escalation():
    """Verify that rejecting injects a ToolMessage rejection reason without executing escalate_ticket."""
    mock_responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "escalate_ticket",
                    "args": {"ticket_title": "False alarm", "severity": "P1"},
                    "id": "call-esc-3",
                }
            ],
        ),
        AIMessage(content="Understood. Continuing triage without escalation."),
    ]

    call_count = 0

    def mock_model(state):
        nonlocal call_count
        resp = mock_responses[call_count]
        call_count += 1
        return {"messages": [resp]}

    workflow = create_agent_graph()
    workflow.nodes["agent"].runnable = mock_model
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])

    config = {"configurable": {"thread_id": "hitl-reject-test"}}
    app.invoke({"messages": [HumanMessage(content="Escalate please")]}, config)
    assert "sensitive_tools" in app.get_state(config).next

    # Engineer rejects: inject rejection ToolMessage into state as sensitive_tools
    reject_msg = ToolMessage(
        content="Rejected by engineer: Known test event, do not page team.",
        tool_call_id="call-esc-3",
    )
    app.update_state(config, {"messages": [reject_msg]}, as_node="sensitive_tools")
    res = app.invoke(None, config)

    # Escalation tool did NOT run, only our rejection message was injected
    tool_messages = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert "Rejected by engineer" in tool_messages[0].content
    assert "Ticket created" not in tool_messages[0].content



def test_hitl_pause_survives_restart():
    """Verify paused state is preserved across new compiled instances over the same checkpointer."""
    checkpointer = MemorySaver()
    config = {"configurable": {"thread_id": "hitl-restart-test"}}

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "escalate_ticket",
                "args": {"ticket_title": "Network outage", "severity": "P1"},
                "id": "call-esc-4",
            }
        ],
    )

    # Instance 1: runs and pauses
    w1 = create_agent_graph()
    w1.nodes["agent"].runnable = lambda state: {"messages": [mock_response]}
    app1 = w1.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])
    app1.invoke({"messages": [HumanMessage(content="Outage")]}, config)

    # Instance 2 (simulating process restart)
    w2 = create_agent_graph()
    w2.nodes["agent"].runnable = lambda state: {"messages": [mock_response]}
    app2 = w2.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])

    state2 = app2.get_state(config)
    assert "sensitive_tools" in state2.next


def test_hitl_parallel_mixed_calls_pause():
    """Verify that a parallel message with BOTH safe and sensitive tools still pauses at sensitive_tools."""
    # Model emits two parallel tool calls: a safe one + escalate_ticket
    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "query_service_health",
                "args": {"service_name": "auth"},
                "id": "call-safe-1",
            },
            {
                "name": "escalate_ticket",
                "args": {"ticket_title": "Auth failure", "severity": "P1"},
                "id": "call-esc-5",
            },
        ],
    )

    workflow = create_agent_graph()
    workflow.nodes["agent"].runnable = lambda state: {"messages": [mock_response]}
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])

    config = {"configurable": {"thread_id": "hitl-parallel-test"}}
    app.invoke({"messages": [HumanMessage(content="Auth is down, escalate now!")]}, config)

    state = app.get_state(config)
    # Must pause before sensitive_tools even though one call is safe
    assert "sensitive_tools" in state.next
    # No ToolMessage should have been created yet
    assert not any(isinstance(m, ToolMessage) for m in state.values["messages"])

