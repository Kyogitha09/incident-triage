# Proposal

## Why

Engineers need an accessible web interface and programmatic REST API to interact with the incident triage agent, submit incident descriptions, and approve or reject sensitive escalations.

## What Changes

- Implement `app.py`:
  - FastAPI application hosting endpoints:
    - `POST /chat`: Accepts `{thread_id, message}`, returns `COMPLETED` or `AWAITING_APPROVAL` with `pending_actions`.
    - `POST /approve`: Accepts `{thread_id, approved, rejection_reason?}`, returns `RESOLVED` or `REJECTED_AND_RESUMED`, or HTTP 400 if nothing is pending.
    - `GET /healthz`: Health check endpoint.
  - Gradio Blocks UI mounted at root `"/"`:
    - Inputs for Thread ID and Incident Description.
    - Actions: "Trigger Triage", "Approve Escalation", "Reject Action".
    - Outputs for Workflow State label and Agent Log markdown.
  - Combined ASGI application `app = gr.mount_gradio_app(app, blocks, path="/")`.
  - Local server startup using `uvicorn.run()` when executed directly with `PORT` environment variable support (fallback 7860).
  - Unified service layer logic shared between REST endpoints and Gradio callbacks.
- Add API tests using FastAPI `TestClient` in `tests/test_api.py`.

## Capabilities

### New Capabilities
- `triage-api`: REST endpoints for chat interaction and human-in-the-loop approval.
- `triage-ui`: Gradio web interface for triage workflow interaction.

### Modified Capabilities
- (None)

## Impact

- **Affected Code**: `app.py`, `tests/test_api.py`.
- **Dependencies**: `fastapi`, `gradio`, `uvicorn`, `requests`.
- **Rollback Note**: Revert `app.py` and `tests/test_api.py`.
