# Design: Harden HITL Routing

## Context

See `proposal.md - Why` for motivation. The current `route_tools` in `agent.py` only inspects `tool_calls[0]`, so parallel tool calls containing a mix of safe and sensitive tools could bypass the HITL gate.

## Goals / Non-Goals

**Goals**:
- Any message with at least one `escalate_ticket` call routes to `sensitive_tools`.
- Rejection injects a `ToolMessage` for every pending call, keeping graph state valid.

**Non-Goals**:
- Changing the approval flow itself (invoke(None) / update_state pattern stays).
- Adding new tools or changing the LLM prompt.

## Decisions

### 1. Check ALL tool_calls in route_tools (not just index 0)

**Decision**: iterate over all tool calls and return `"sensitive_tools"` if any has `name == "escalate_ticket"`.

**Rationale**: a single-index check is fragile by design — if the model emits parallel calls, the sensitive one can appear at any position. Iterating all calls is O(n) where n is never more than a handful of calls, so there's no meaningful performance cost.

**Alternative considered**: keep index-0 check but enforce single-call output via prompt. Rejected — prompt-level enforcement is non-deterministic and hard to test reliably.

### 2. Inject a ToolMessage for every pending tool call on rejection

**Decision**: in `app.py`'s `service_approve` rejection branch, iterate `last_msg.tool_calls` and create one `ToolMessage` per call (matching its `tool_call_id`), then `update_state` once.

**Rationale**: LangGraph validates that every `tool_call_id` referenced in an `AIMessage` has a corresponding `ToolMessage` before the agent node can run again. Injecting only one message for a multi-call AIMessage would leave the state corrupt and the graph would error.

## Risks / Trade-offs

- [Risk] Parallel tool calls with mixed safe + sensitive semantics currently uncommon with Gemini models, but this change future-proofs the graph. → No mitigation needed; hardening is cheap.

## Migration Plan

1. Update `route_tools` in `agent.py`.
2. Update rejection handler in `app.py`.
3. Add regression test in `tests/test_hitl.py`.
4. Run `pytest tests/test_hitl.py -v` to confirm all 5 tests pass.
5. Rollback: revert `route_tools` to single-index check (safe because escalate_ticket is always called alone in practice).
