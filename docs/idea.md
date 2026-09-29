# Autonomous Incident Triage Agent

## Overview
We need an autonomous agent to assist with incident triage. It should:
1. Have a knowledge base of runbooks (stored as embeddings).
2. Look at incoming incident tickets.
3. Check service health directly using tools.
4. Search the runbooks for past solutions or known mitigations.
5. If the incident requires manual intervention or is critical, pause and ask a human for approval to escalate it.
6. Provide an API and a simple UI for chatting with the agent and approving escalations.
7. Be deployable on free-tier services like Render.
