from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from app import app, app_state
from agent import create_agent_graph


@pytest.fixture
def client():
    return TestClient(app)


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_and_approval_flow(client):
    # Setup mock agent with memory checkpointer
    mock_responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "escalate_ticket",
                    "args": {"ticket_title": "Auth failure", "severity": "P1"},
                    "id": "call-api-1",
                }
            ],
        ),
        AIMessage(content="Ticket escalated and team paged."),
    ]
    call_idx = 0

    def mock_model(state):
        nonlocal call_idx
        resp = mock_responses[call_idx]
        call_idx += 1
        return {"messages": [resp]}

    workflow = create_agent_graph()
    workflow.nodes["agent"].runnable = mock_model
    checkpointer = MemorySaver()
    mock_agent = workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])
    app_state["agent"] = mock_agent

    # 1. POST /chat -> enters AWAITING_APPROVAL
    chat_resp = client.post("/chat", json={"thread_id": "test-api-1", "message": "Auth is down"})
    assert chat_resp.status_code == 200
    assert chat_resp.json()["status"] == "AWAITING_APPROVAL"
    assert "escalate_ticket" in chat_resp.json()["pending_actions"]

    # 2. POST /approve with approved=True -> RESOLVED
    appr_resp = client.post("/approve", json={"thread_id": "test-api-1", "approved": True})
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "RESOLVED"
    assert "Ticket escalated" in appr_resp.json()["response"]


def test_approve_nothing_pending_returns_400(client):
    workflow = create_agent_graph()
    workflow.nodes["agent"].runnable = lambda state: {"messages": [AIMessage(content="All good")]}
    checkpointer = MemorySaver()
    app_state["agent"] = workflow.compile(checkpointer=checkpointer, interrupt_before=["sensitive_tools"])

    resp = client.post("/approve", json={"thread_id": "thread-empty-1", "approved": True})
    assert resp.status_code == 400
    assert "Nothing pending" in resp.json()["detail"]
