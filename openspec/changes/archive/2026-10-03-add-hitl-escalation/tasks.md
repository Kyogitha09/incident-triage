# Tasks

## 1. Sensitive Tool & Graph Updates

- [x] 1.1 Implement `escalate_ticket(ticket_title: str, severity: str)` tool in `agent.py` and register in `SENSITIVE_TOOLS`
- [x] 1.2 Add `sensitive_tools` node and update `route_tools` to route escalation calls to `sensitive_tools`
- [x] 1.3 Update `create_agent_graph()` and `get_agent_app()` to compile with `interrupt_before=["sensitive_tools"]`
- [x] 1.4 Update `SYSTEM_PROMPT` in `agent.py` to instruct escalating when manual intervention is needed or service stays degraded

## 2. Unit Testing & Verification

- [x] 2.1 Add unit tests in `tests/test_hitl.py` verifying escalation pauses before `sensitive_tools` without running the tool
- [x] 2.2 Add unit test verifying that approving a paused thread executes `escalate_ticket` and completes the graph
- [x] 2.3 Add unit test verifying that rejecting a paused thread injects `ToolMessage` and continues reasoning without executing the tool
- [x] 2.4 Add unit test verifying pause survives across distinct graph instances for the same `thread_id`
- [x] 2.5 Run `pytest -q` to verify all tests pass
