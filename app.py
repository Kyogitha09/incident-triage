import os
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import gradio as gr
from psycopg_pool import ConnectionPool
from langchain_core.messages import HumanMessage, ToolMessage
from agent import get_agent_app, extract_text
from dotenv import load_dotenv

load_dotenv()

app_state = {}


def get_active_agent():
    """Retrieve or initialize the active agent app."""
    if "agent" not in app_state:
        app_state["agent"] = get_agent_app()
    return app_state["agent"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        pool = ConnectionPool(
            db_url,
            min_size=1,
            max_size=10,
            timeout=15,
            kwargs={"prepare_threshold": None, "autocommit": True},
        )
        agent_app = get_agent_app(pool)
        app_state["pool"] = pool
        app_state["agent"] = agent_app
    else:
        app_state["agent"] = get_agent_app()
    yield
    if "pool" in app_state:
        app_state["pool"].close()


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ApproveRequest(BaseModel):
    thread_id: str
    approved: bool
    rejection_reason: Optional[str] = None


# Shared Service Layer for both REST and Gradio UI
def service_chat(thread_id: str, message: str) -> dict:
    if not thread_id or not thread_id.strip():
        return {"status": "ERROR", "message": "Thread ID cannot be empty"}
    if not message or not message.strip():
        return {"status": "ERROR", "message": "Incident Description cannot be empty"}

    agent = get_active_agent()
    config = {"configurable": {"thread_id": thread_id}}

    agent.invoke({"messages": [HumanMessage(content=message)]}, config)
    graph_state = agent.get_state(config)

    if graph_state.next and "sensitive_tools" in graph_state.next:
        last_msg = graph_state.values["messages"][-1]
        pending = [tc["name"] for tc in getattr(last_msg, "tool_calls", [])]
        return {
            "status": "AWAITING_APPROVAL",
            "pending_actions": pending,
            "response": "Investigation paused: Escalation requires human approval.",
        }

    last_msg = graph_state.values["messages"][-1]
    return {"status": "COMPLETED", "response": extract_text(last_msg.content)}


def service_approve(thread_id: str, approved: bool, rejection_reason: Optional[str] = None) -> dict:
    if not thread_id or not thread_id.strip():
        return {"status": "ERROR", "message": "Thread ID cannot be empty"}

    agent = get_active_agent()
    config = {"configurable": {"thread_id": thread_id}}
    graph_state = agent.get_state(config)

    if not graph_state.next or "sensitive_tools" not in graph_state.next:
        return {"status": "NOT_PENDING", "message": "Nothing pending for this thread"}

    if approved:
        res = agent.invoke(None, config)
        last_msg = res["messages"][-1]
        return {"status": "RESOLVED", "response": extract_text(last_msg.content)}
    else:
        last_msg = graph_state.values["messages"][-1]
        results = []
        for tc in getattr(last_msg, "tool_calls", []):
            results.append(
                ToolMessage(
                    content=f"Rejected by engineer: {rejection_reason or 'No reason provided'}",
                    tool_call_id=tc["id"],
                    name=tc["name"],
                )
            )
        agent.update_state(config, {"messages": results}, as_node="sensitive_tools")
        res = agent.invoke(None, config)
        last_msg = res["messages"][-1]
        return {"status": "REJECTED_AND_RESUMED", "response": extract_text(last_msg.content)}


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    result = service_chat(req.thread_id, req.message)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.post("/approve")
def approve_endpoint(req: ApproveRequest):
    result = service_approve(req.thread_id, req.approved, req.rejection_reason)
    if result.get("status") == "NOT_PENDING":
        raise HTTPException(status_code=400, detail=result.get("message"))
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Gradio UI Event Callbacks
def ui_trigger(thread_id: str, message: str):
    res = service_chat(thread_id, message)
    if res.get("status") == "AWAITING_APPROVAL":
        return f"AWAITING_APPROVAL ({', '.join(res.get('pending_actions', []))})", res.get("response", "")
    elif res.get("status") == "COMPLETED":
        return "COMPLETED", res.get("response", "")
    return res.get("status", "ERROR"), res.get("message", "Unknown error")


def ui_approve(thread_id: str):
    res = service_approve(thread_id, approved=True)
    if res.get("status") == "RESOLVED":
        return "RESOLVED", res.get("response", "Escalation approved.")
    return res.get("status", "ERROR"), res.get("message", "Error")


def ui_reject(thread_id: str, reason: str):
    res = service_approve(thread_id, approved=False, rejection_reason=reason)
    if res.get("status") == "REJECTED_AND_RESUMED":
        return "REJECTED_AND_RESUMED", res.get("response", "Escalation rejected.")
    return res.get("status", "ERROR"), res.get("message", "Error")


# Gradio Interface
with gr.Blocks(title="Incident Triage Agent") as blocks:
    gr.Markdown("# Autonomous Incident Triage Agent")
    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", value="thread-1")
        message = gr.Textbox(
            label="Incident Description",
            value="Auth service is timing out... Escalate immediately.",
            lines=2,
        )

    with gr.Row():
        trigger_btn = gr.Button("Trigger Triage", variant="primary")
        approve_btn = gr.Button("Approve Escalation", variant="stop")

    with gr.Row():
        reject_reason = gr.Textbox(label="Rejection Reason (if rejecting)", placeholder="e.g. Known maintenance window")
        reject_btn = gr.Button("Reject Action", variant="secondary")

    status_label = gr.Label(label="Workflow State")
    log_area = gr.Markdown(label="Agent Log")

    trigger_btn.click(ui_trigger, inputs=[thread_id, message], outputs=[status_label, log_area])
    approve_btn.click(ui_approve, inputs=[thread_id], outputs=[status_label, log_area])
    reject_btn.click(ui_reject, inputs=[thread_id, reject_reason], outputs=[status_label, log_area])

app = gr.mount_gradio_app(app, blocks, path="/")

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 7860))
    print(f"Starting server on http://localhost:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
