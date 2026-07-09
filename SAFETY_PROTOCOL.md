# SAFETY PROTOCOL

JARVIS is designed to be reliable through safety gates, not pretend perfection.

## Action tiers
1. **Allowed (no approval):** read project files, create notes/tasks/plans, draft content & customer replies, analyze business knowledge, suggest trading ideas, launch whitelisted apps.
2. **Requires confirmation:** overwrite/delete/move files, run shell commands, install packages, modify system settings, send email, post content, change ads, access external accounts, spend money, place trades, connect APIs, edit business-critical files, execute automation scripts.
3. **Forbidden unless explicitly enabled:** autonomous trading, autonomous ad spend, autonomous email/social, storing passwords/API keys, destructive file ops without backup, running unknown executables, bypassing safety checks.

## Guard behavior
- Every orchestrator action passes through `SafetyGuard.review()` then `PermissionManager.check()`.
- Risky actions are **blocked and reported**, never silently executed.
- Failures are logged and surfaced honestly. JARVIS never claims success on failure.
- Destructive file operations require a backup first.

## Secrets
JARVIS never stores passwords or API keys in memory or logs. `.env` is for the user only.
