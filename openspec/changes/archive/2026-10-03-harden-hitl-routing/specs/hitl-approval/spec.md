# Spec Delta

## MODIFIED Requirements

### Requirement: Sensitive actions require human approval
The agent MUST pause before executing any message that contains at least one sensitive tool call. If ANY tool call in the message is `escalate_ticket`, the ENTIRE message MUST be routed to `sensitive_tools` and MUST NOT execute without explicit human approval. On rejection, the agent MUST receive a `ToolMessage` for EVERY pending tool call in the message so that graph state remains valid.

#### Scenario: Escalation pauses
- GIVEN an incident where the model decides to call escalate_ticket
- WHEN the graph runs
- THEN execution stops before the sensitive_tools node
- AND no ticket is created

#### Scenario: Approved escalation executes
- GIVEN a thread paused before sensitive_tools
- WHEN an engineer approves
- THEN escalate_ticket runs once and the agent produces a final response

#### Scenario: Rejected escalation is not executed
- GIVEN a thread paused before sensitive_tools
- WHEN an engineer rejects with a reason
- THEN escalate_ticket is never executed
- AND the agent receives the rejection reason and continues reasoning

#### Scenario: Pause survives restart
- GIVEN a thread paused before sensitive_tools
- WHEN the process restarts
- THEN the thread is still awaiting approval

#### Scenario: Mixed parallel tool calls pause on any sensitive call
- GIVEN the model emits parallel tool calls where at least one is escalate_ticket and others are safe (e.g. query_service_health)
- WHEN route_tools evaluates the message
- THEN the graph routes to sensitive_tools
- AND execution pauses for human approval before any tool in the message executes

#### Scenario: Rejection covers all pending tool calls
- GIVEN a thread paused before sensitive_tools with multiple tool calls in the message
- WHEN an engineer rejects
- THEN a ToolMessage is injected for EVERY pending tool call in the message
- AND the agent resumes without any tool having executed
