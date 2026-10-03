# Spec Delta

## Purpose

Defines requirements and operational constraints for hosting the incident triage service on cloud hosting providers.

## ADDED Requirements

### Requirement: Port Binding
The service SHALL bind to the port provided in the `$PORT` environment variable.

#### Scenario: Service starts on assigned port
- GIVEN the environment variable PORT is set
- WHEN the application server starts
- THEN it listens on the assigned port

### Requirement: Secret Isolation
Secrets SHALL come only from environment variables; `.env` SHALL NOT be committed.

#### Scenario: Git repo does not track secrets
- GIVEN the git repository status
- WHEN git tracks files
- THEN `.env` is ignored and absent from git index

### Requirement: Health Probe Isolation
The service SHALL expose `GET /healthz` returning 200 without calling Gemini or the database.

#### Scenario: Health probe succeeds without external calls
- GIVEN the application is running
- WHEN a GET request is made to /healthz
- THEN HTTP status 200 is returned immediately

### Requirement: Cold Start Resilience
A paused approval SHALL still be resumable after an application cold start or worker restart.

#### Scenario: Paused thread resumes after cold start
- GIVEN a thread awaiting approval before a process termination
- WHEN the service restarts in a fresh process
- THEN the approval endpoint can still resolve or reject the thread
