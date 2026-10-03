# Design

## Context

See `proposal.md` for motivation. Builds on Change 2 (`add-triage-agent-core`).
Incident investigation must remain autonomous for diagnostics, but destructive or external actions like escalating tickets must pause for human confirmation.

## Goals / Non-Goals

**Goals:**
- Add `escalate_ticket(ticket_title: str, severity: str)` tool to `agent.py` marked as sensitive.
- Isolate sensitive tools in a separate `sensitive_tools` node.
- Route tool calls: `route_tools` routes to `sensitive_tools` if `escalate_ticket` is called, else `safe_tools`.
- Compile graph with `interrupt_before=["sensitive_tools"]`.
- Support resumption:
  - Approval: `app.invoke(None, config)` resumes through `sensitive_tools`.
  - Rejection: inject a `ToolMessage` with content `"Rejected by engineer: <reason>"` via `app.update_state(config, {"messages": [...]}, as_node="sensitive_tools")` then `app.invoke(None, config)`.
- Update system prompt: escalate if manual intervention is needed or service stays degraded.

**Non-Goals:**
- REST API and Gradio UI (Change 4).

## Decisions

- **Decision 1: Use LangGraph `interrupt_before` over in-node prompt pauses**
  - *Rationale*: Native `interrupt_before` persists the entire execution state into `PostgresSaver` before node execution, allowing safe resumption across worker restarts.
  - *Alternatives considered*: In-tool approval callbacks (blocks worker thread and fails on process restart).

## Risks / Trade-offs

- **[Risk: Single-call inspection in route_tools]** → If model emits parallel tool calls, inspecting only the first call could route improperly. *Mitigation*: Flagged for Change 6 (`harden-hitl-routing`).
