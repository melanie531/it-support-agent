---
alwaysApply: true
---

# Spec Compliance Rule — IT Support Agent

## Rule
All implementation code MUST trace back to requirements in `spec.md`.

## Enforcement
- Before implementing a feature, find its acceptance criteria in `spec.md` Section 10
- Use the exact function signatures defined in `CLAUDE.md` Architecture Patterns section
- Use the exact project structure defined in `spec.md` Section 6
- Use the exact tech stack defined in `CLAUDE.md` — do not substitute libraries
- Use the system prompt from `spec.md` Section 8 verbatim
- Configuration values must match `spec.md` Section 7

## Response Schema
The `/ask` endpoint response MUST include these fields:
- `answer` (str)
- `sources` (list of objects with `document`, `section`, `relevance_score`)
- `escalation` (bool)
- `escalation_reason` (str | null)

Do not omit or rename these fields.

## Out of Scope
Do NOT build anything listed in `spec.md` Section 11 (Out of Scope):
- No authentication
- No Slack/Teams integration
- No automated actions
- No multi-turn memory
- No PDF ingestion
- No Docker/deployment config
