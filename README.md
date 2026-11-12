# auto-resume-tasks

Background task failure auto-recovery decision framework.

Classifies errors as transient/fatal/logical and decides whether to retry, resume, abandon, or escalate to human.

- Full jitter backoff to avoid thundering herd
- Semantic fingerprint circuit breaker to prevent infinite loops

## Install

Install this skill in your agent environment to use it.

## Version

v1.2.1
