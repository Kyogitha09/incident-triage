# Tasks

## 1. Harden route_tools in agent.py

- [x] 1.1 Update `route_tools` in `agent.py` to iterate ALL tool_calls in the last message and return `"sensitive_tools"` if ANY call has `name == "escalate_ticket"`; verify by running `pytest tests/test_hitl.py::test_hitl_parallel_mixed_calls_pause -v` and confirming it passes.

## 2. Fix rejection handler in app.py

- [x] 2.1 Update the rejection branch in `service_approve` in `app.py` to inject a `ToolMessage` for EVERY tool call in `last_msg.tool_calls`, not just the first; verify by running `pytest tests/test_hitl.py -v` and confirming all 5 tests pass.

## 3. Add regression test for parallel mixed tool calls

- [x] 3.1 Add `test_hitl_parallel_mixed_calls_pause` to `tests/test_hitl.py`: mock an `AIMessage` with both `query_service_health` and `escalate_ticket` in `tool_calls`, run the graph, and assert it pauses at `sensitive_tools`; verify by running `pytest tests/test_hitl.py -v`.
