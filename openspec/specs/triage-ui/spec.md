# triage-ui Specification

## Purpose

Provides a clean browser user interface for initiating incidents and performing one-click approvals.

## Requirements

### Requirement: Triage Interface Controls
The web interface SHALL present input controls for thread identifier, incident description, and workflow actions.

#### Scenario: Missing Thread ID validation
- GIVEN an empty Thread ID field
- WHEN the user clicks Trigger Triage, Approve, or Reject
- THEN the system prompts for a valid Thread ID without calling backend logic

#### Scenario: Triage submission triggers workflow
- GIVEN valid thread and description inputs
- WHEN the user clicks "Trigger Triage"
- THEN the current workflow state is updated in the UI
