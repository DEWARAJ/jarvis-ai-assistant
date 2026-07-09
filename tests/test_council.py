"""Tests for the multi-agent Council (core/council.py) + its routing.

These are deterministic and need no network/LLM: they verify the intent routes to
the council, the Council degrades honestly when the brain is offline, and empty input
is handled. The full live workflow is exercised manually with `council <task>`.
"""
from __future__ import annotations

from core.reasoning_core import ReasoningCore
from core.council import Council


class _FakeLLM:
    def __init__(self, available): self.available = available
    def chat(self, system, user): return "stub"


class _FakeOrch:
    """Minimal orchestrator stand-in for offline-path tests."""
    def __init__(self, llm_available):
        self.llm = _FakeLLM(llm_available)
        self.tools = None
        class _L:
            def info(self, *a, **k): pass
            def begin(self, *a, **k): pass
            def done(self, *a, **k): pass
        self.logger = _L()
        self.live = _L()


def test_council_routes():
    rc = ReasoningCore()
    for phrase in ("council should I rewrite my page", "convene the council", "council review"):
        assert rc.classify(phrase).name == "council_review"


def test_council_extracts_args():
    rc = ReasoningCore()
    i = rc.classify("council should I add dark mode")
    assert i.name == "council_review" and "dark mode" in i.args


def test_council_offline_is_honest():
    c = Council(_FakeOrch(llm_available=False))
    out = c.review("anything")
    assert "offline" in out.lower() or "reasoning core" in out.lower()


def test_council_empty_input():
    c = Council(_FakeOrch(llm_available=True))
    out = c.review("")
    assert "council" in out.lower()
