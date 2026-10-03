# Design

## Context

See `proposal.md` for motivation.
The project operates under a zero-cost stack using Supabase Postgres (transaction pooler on port 6543) and Google Gemini (AI Studio). This change implements `agent.py` using LangGraph with only safe, read-only tools.

## Goals / Non-Goals

**Goals:**
- Implement the LangGraph agent cycle: `agent` -> `safe_tools` -> `agent`, ending at `END` when no tool calls remain.
- Provide safe read-only tools:
  - `query_service_health(service_name: str)`: checks mock service table (`auth`, `payments`, `database`, etc.) and returns structured health details. Unknown services return a friendly message without raising.
  - `search_remediation_runbooks(query: str, service: str = None)`: performs vector similarity search against `incident_docs` via RPC `match_incident_docs` using Gemini embeddings (768-dim, task_type `RETRIEVAL_QUERY`), returning up to 2 top matches or "No relevant runbooks found."
- Provide robust database connection pooling via `psycopg_pool.ConnectionPool` configured specifically for Supabase's transaction pooler: `max_size=10`, `autocommit=True`, `connect_timeout=15`, `prepare_threshold=None` (disables prepared statements to prevent pooler errors).
- Persist LangGraph state per `thread_id` using `PostgresSaver`.
- Implement `extract_text` helper to flatten list-structured or dict-structured model responses into plain strings.
- Provide unit tests with mocked LLM and DB pool.

**Non-Goals:**
- Escalation (`escalate_ticket`) and human-in-the-loop interrupts — reserved for Change 3.
- FastAPI endpoints and Gradio web interface — reserved for Change 4.

## Decisions

- **Decision 1: Explicit tool node for safe tools vs default ToolNode**
  - *Rationale*: Defining `safe_tools` node now keeps read-only operations clearly partitioned from future sensitive operations (`sensitive_tools` in Change 3).
  - *Alternatives considered*: Single monolithic `ToolNode` containing all tools. Rejected because Change 3 requires fine-grained interruption before sensitive tool execution.

- **Decision 2: Disable prepared statements on connection pool (`prepare_threshold=None`)**
  - *Rationale*: Supabase transaction pooler (pgbouncer on port 6543) rejects prepared statements across transaction boundaries.
  - *Alternatives considered*: Direct connection (port 5432). Rejected because free-tier direct connections are easily exhausted in serverless/containerized environments.

- **Decision 3: Gemini embedding model alignment**
  - *Rationale*: Align with `seed_rag.py` using `models/gemini-embedding-001` with 768 output dimensions and `RETRIEVAL_QUERY` task type.

## Risks / Trade-offs

- **[Risk: Free-tier Gemini rate limits]** → LangGraph loops could trigger rate limits if the model calls tools indefinitely. *Mitigation*: Graph terminates at `END` when tool calls cease; maximum iteration safeguards.
- **[Risk: Supabase pooler cold starts & connection drops]** → Stale pool connections causing transient drops. *Mitigation*: `connect_timeout=15`, `max_size=10`, and lightweight connection health verification.
