import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import gradio as gr
from psycopg_pool import ConnectionPool
from langchain_core.messages import HumanMessage, ToolMessage
from agent import get_agent_app
from dotenv import load_dotenv

load_dotenv()

app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        pool = ConnectionPool(db_url, max_size=10, kwargs={"prepare_threshold": None})
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
    rejection_reason: str = None

@app.post("/chat")
def chat(req: ChatRequest):
    agent = app_state["agent"]
    config = {"configurable": {"thread_id": req.thread_id}}
    
    agent.invoke({"messages": [HumanMessage(content=req.message)]}, config)
    
    graph_state = agent.get_state(config)
    if graph_state.next and "sensitive_tools" in graph_state.next:
        last_msg = graph_state.values["messages"][-1]
        pending = [tc["name"] for tc in last_msg.tool_calls]
        return {"status": "AWAITING_APPROVAL", "pending_actions": pending}
    
    return {"status": "COMPLETED", "response": graph_state.values["messages"][-1].content}

@app.post("/approve")
def approve(req: ApproveRequest):
    agent = app_state["agent"]
    config = {"configurable": {"thread_id": req.thread_id}}
    graph_state = agent.get_state(config)
    
    if not graph_state.next or "sensitive_tools" not in graph_state.next:
        raise HTTPException(status_code=400, detail="Nothing pending for this thread")
    
    if req.approved:
        agent.invoke(None, config)
        return {"status": "RESOLVED"}
    else:
        last_msg = graph_state.values["messages"][-1]
        results = []
        for tc in last_msg.tool_calls:
            results.append(ToolMessage(
                content=f"Rejected by engineer: {req.rejection_reason or 'No reason provided'}", 
                tool_call_id=tc["id"], 
                name=tc["name"]
            ))
        agent.update_state(config, {"messages": results}, as_node="sensitive_tools")
        agent.invoke(None, config)
        return {"status": "REJECTED_AND_RESUMED"}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Gradio UI
def ui_trigger(thread_id, message):
    if not thread_id or not message:
        return "Please provide thread_id and message", ""
    import requests
    try:
        resp = requests.post(f"http://127.0.0.1:{os.environ.get('PORT', '7860')}/chat", json={"thread_id": thread_id, "message": message}).json()
        if resp.get("status") == "AWAITING_APPROVAL":
            return f"AWAITING_APPROVAL for {resp.get('pending_actions')}", "Waiting for approval..."
        return "COMPLETED", resp.get("response", "Error")
    except Exception as e:
        return "ERROR", str(e)

def ui_approve(thread_id):
    import requests
    try:
        resp = requests.post(f"http://127.0.0.1:{os.environ.get('PORT', '7860')}/approve", json={"thread_id": thread_id, "approved": True}).json()
        return resp.get("status", "ERROR")
    except Exception as e:
        return str(e)

def ui_reject(thread_id, reason):
    import requests
    try:
        resp = requests.post(f"http://127.0.0.1:{os.environ.get('PORT', '7860')}/approve", json={"thread_id": thread_id, "approved": False, "rejection_reason": reason}).json()
        return resp.get("status", "ERROR")
    except Exception as e:
        return str(e)

with gr.Blocks() as blocks:
    gr.Markdown("# Incident Triage Agent")
    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", value="thread-1")
        message = gr.Textbox(label="Incident Description", value="Auth service is timing out... Escalate immediately.")
    
    with gr.Row():
        trigger_btn = gr.Button("Trigger Triage")
        approve_btn = gr.Button("Approve Escalation")
    
    with gr.Row():
        reject_reason = gr.Textbox(label="Rejection Reason")
        reject_btn = gr.Button("Reject Action")
    
    status_label = gr.Label(label="Workflow State")
    log_area = gr.Markdown(label="Agent Log")
    
    trigger_btn.click(ui_trigger, inputs=[thread_id, message], outputs=[status_label, log_area])
    approve_btn.click(ui_approve, inputs=[thread_id], outputs=[status_label])
    reject_btn.click(ui_reject, inputs=[thread_id, reject_reason], outputs=[status_label])

app = gr.mount_gradio_app(app, blocks, path="/")
