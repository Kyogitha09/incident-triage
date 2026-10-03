# Proposal

## Why

In `agent.py`, the routing logic originally inspected only the first tool call (`last_message.tool_calls[0]`). If the model emits parallel tool calls (such as `[query_service_health, escalate_ticket]`), a sensitive action could execute unapproved or fail unexpectedly. This change hardens routing so that if ANY tool call is sensitive, the entire message pauses for human approval.

## What Changes

- Update `route_tools` in `agent.py`: inspect ALL tool calls in the message, routing to `sensitive_tools` if ANY call is sensitive (`escalate_ticket`).
- Update rejection handler to inject a `ToolMessage` for EVERY pending tool call so the agent graph state remains valid.
- Add regression tests covering mixed safe + sensitive parallel tool calls.

## Capabilities

### New Capabilities
- (None)

### Modified Capabilities
- `hitl-approval`: Route ANY message containing at least one sensitive tool call through approval, and answer all tool calls on rejection.

## Impact

- **Affected Code**: `agent.py`, `app.py`, `tests/test_hitl.py`.
- **Rollback Note**: Revert routing logic in `agent.py`.
