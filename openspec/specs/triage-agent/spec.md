# triage-agent Specification

## Purpose

Enables automated incident triage by orchestrating service health inspections, runbook retrieval, and persistent conversational state.

## Requirements

### Requirement: Health-first investigation
The agent SHALL check service health before searching runbooks when investigating an incident report.

#### Scenario: Service health check precedes runbook search
- GIVEN an incident report identifying an impacted service
- WHEN the agent decides its tool calling sequence
- THEN `query_service_health` is executed before `search_remediation_runbooks`

### Requirement: Runbook retrieval
The system SHALL retrieve at most two relevant runbooks using vector similarity search, or return a clear fallback message if no matches exist.

#### Scenario: Top matches returned
- GIVEN relevant runbooks exist in the knowledge base
- WHEN `search_remediation_runbooks` is called with a query
- THEN up to 2 top matching runbooks are returned

#### Scenario: No matches found
- GIVEN no runbooks match the query above similarity threshold
- WHEN `search_remediation_runbooks` is called
- THEN the tool returns "No relevant runbooks found."

### Requirement: Unknown service handling
The health query tool SHALL return a graceful not-found message rather than raising an exception when queried with an unrecognized service name.

#### Scenario: Unknown service queried
- GIVEN the service health catalog contains known services
- WHEN `query_service_health` is called with an unknown service such as "billing"
- THEN the tool returns a message indicating the service was not found without raising an error

### Requirement: State persistence
The system SHALL persist conversation state across separate processes using a thread identifier.

#### Scenario: Conversation survives process restart
- GIVEN a conversation thread with history saved under a specific thread_id
- WHEN a new agent process instance loads the same thread_id
- THEN the previous conversation state and message history are fully restored

### Requirement: Content normalisation
The system SHALL normalise complex list-structured model output blocks into a single plain text string.

#### Scenario: List structured content flattened
- GIVEN a model response containing content as a list of text blocks or dictionaries
- WHEN `extract_text` processes the content
- THEN a single unified string is returned
