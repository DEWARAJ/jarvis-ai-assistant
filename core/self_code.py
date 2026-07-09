"""Self-Code — DISABLED at the master's request (2026-06-09).

JARVIS does NOT rewrite its own source code. The master asked for this off, and it is
safer this way. JARVIS still *updates* itself on command (skills, packages, knowledge)
via 'update yourself' / 'improve yourself' / 'install the autonomous toolkit', each of
which is gated behind one explicit confirmation. This stub remains only so any stale
import resolves; it performs no source editing.
"""
from __future__ import annotations


class SelfCoder:
    """Inert. Self-rewriting is disabled; calls return a clear, harmless refusal."""

    disabled = True

    def __init__(self, orch=None):
        self.orch = orch

    def propose(self, *_a, **_k) -> dict:
        return {"ok": False, "detail": "Self-rewriting is disabled, sir. Say 'update yourself' instead."}

    def apply(self, *_a, **_k) -> str:
        return "Self-rewriting is disabled, sir."
