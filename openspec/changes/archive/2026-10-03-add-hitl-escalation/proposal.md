# Proposal

## Why

Automated triage is powerful, but modifying system state, paging on-call engineers, or opening high-severity incident tickets must require human oversight to prevent accidental spam or improper escalations. This change introduces Human-in-the-Loop (HITL) approval for sensitive actions.

## What Changes

- Add sensitive tool `escalate_ticket(ticket_title: str, severity: str)` to `agent.py`.
- Introduce a dedicated `sensitive_tools` node in LangGraph.
- Update `route_tools` to direct sensitive tool calls to `sensitive_tools`.
- Compile the graph with `interrupt_before=["sensitive_tools"]` so execution pauses safely before any sensitive action runs.
- Support resuming upon approval (invoking with `None`) or rejection (injecting a `ToolMessage` indicating engineer rejection via `update_state`).
- Update system prompt instructing the model to escalate if manual intervention is required or the service remains severely degraded.
- Add comprehensive unit tests covering pause, approval, and rejection paths.

## Capabilities

### New Capabilities
- `hitl-approval`: Safe Human-in-the-Loop approval gating for sensitive operations, supporting interruption, approval execution, and rejection handling.

### Modified Capabilities
- (None)

## Impact

- **Affected Code**: `agent.py`, `tests/test_agent.py`.
- **Rollback Note**: Revert changes in `agent.py` to restore purely read-only graph execution.
