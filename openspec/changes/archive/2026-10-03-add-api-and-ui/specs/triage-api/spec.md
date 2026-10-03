# Spec Delta

## Purpose

Provides REST API endpoints for automated triage triggering and approval management.

## ADDED Requirements

### Requirement: Triage Chat Endpoint
The API SHALL provide a `POST /chat` endpoint taking a thread ID and message, returning either a completed response or an awaiting approval state.

#### Scenario: Normal triage completes
- GIVEN a valid thread_id and message not triggering escalation
- WHEN POST /chat is called
- THEN status is "COMPLETED"
- AND a text response is returned

#### Scenario: Escalation awaits approval
- GIVEN an incident requiring escalation
- WHEN POST /chat is called
- THEN status is "AWAITING_APPROVAL"
- AND pending_actions lists the sensitive action

### Requirement: Escalation Approval Endpoint
The API SHALL provide a `POST /approve` endpoint to approve or reject pending sensitive actions.

#### Scenario: Successful approval
- GIVEN a thread awaiting approval
- WHEN POST /approve is called with approved=True
- THEN status is "RESOLVED"

#### Scenario: Successful rejection
- GIVEN a thread awaiting approval
- WHEN POST /approve is called with approved=False and a rejection reason
- THEN status is "REJECTED_AND_RESUMED"

#### Scenario: Non-pending approval rejected with 400
- GIVEN a thread that has no pending sensitive tools
- WHEN POST /approve is called
- THEN HTTP status code 400 is returned
