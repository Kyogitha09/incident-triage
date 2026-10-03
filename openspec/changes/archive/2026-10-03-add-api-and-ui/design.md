# Design

## Context

See `proposal.md` for motivation. Builds on Changes 2 & 3 (`add-triage-agent-core` and `add-hitl-escalation`).

## Goals / Non-Goals

**Goals:**
- Provide FastAPI routes `/chat`, `/approve`, `/healthz`.
- Mount Gradio Blocks UI onto the FastAPI app under root `"/"`.
- Provide a single unified service function layer used by both REST endpoints and Gradio callbacks to prevent code duplication.
- Include executable entrypoint `if __name__ == "__main__": uvicorn.run(...)` respecting `$PORT` with fallback to `7860`.

**Non-Goals:**
- Render deployment setup (Change 5).

## Decisions

- **Decision 1: Shared service layer for FastAPI & Gradio**
  - *Rationale*: Avoid redundant state checking and LangGraph invoke calls in both UI callback and REST handlers.
  - *Alternatives considered*: Calling REST API via `requests` inside Gradio callbacks. Rejected due to port binding synchronization and extra network overhead.

## Risks / Trade-offs

- **[Risk: Port collision on local development]** → Allow configurable `$PORT` with fallback to `7860`.
