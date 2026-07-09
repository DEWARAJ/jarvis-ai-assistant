"""Phase 5 STEP 3-5 — multi-agent verification debate (LANE 3 ONLY).

A structured debate, not a free-for-all:
  1 RESEARCH   — gather evidence (live search when the question is also time-sensitive)
  2 ANSWER     — draft the answer from that evidence
  3 CHALLENGE  — argue the opposite, find the flaw, check the evidence really supports it
  4 VERIFY     — cross-check claims vs sources, flag anything unsupported or stale
  5 SYNTHESIZE — reconcile into the final output

Final output carries: the conclusion, a confidence level (certain/likely/uncertain) by
evidence strength, any point the agents disagreed on (dissent is NEVER hidden), and
sources with timestamps for live-data claims.

STEP 4 disagreement handling is tied to STAKES:
  - consequential (financial / strategic / irreversible / "should I") + no consensus
    -> return ALL positions, state plainly "the agents did not agree — you decide".
    A surfaced disagreement on a high-stakes call is the CORRECT output, not a failure.
  - low-stakes / knowable-correct + minor disagreement -> synthesize one best answer,
    note the disagreement in a line.
  - NEVER fabricate consensus.

Performance guards (STEP 5): Lane-3 only (the router gates this), a hard wall-clock cap,
and honest "partial" labelling if the cap is hit. Runs sequentially; the orchestrator's
_state_lock (BUG 9) is now in place, so parallelising the research step is safe to add
later, but sequential keeps it deterministic.
"""
from __future__ import annotations
import time

_HIGH_STAKES = (
    "should i", "should we", "invest", "trade", "trading strategy", "switch my",
    "all in", "quit", "buy", "sell", "spend", "irreversible", "bet", "mortgage",
    "loan", "fire", "hire", "lawsuit", "contract", "delete everything", "go live",
)


def _is_high_stakes(question: str) -> bool:
    low = (question or "").lower()
    return any(s in low for s in _HIGH_STAKES)


def _confidence(verify_text: str) -> str:
    low = (verify_text or "").lower()
    if "confidence: certain" in low or "i am certain" in low:
        return "certain"
    if "confidence: uncertain" in low or "unsupported" in low or "stale" in low or "no consensus" in low:
        return "uncertain"
    return "likely"


def _consensus(verify_text: str) -> bool:
    low = (verify_text or "").lower()
    if "consensus: no" in low or "do not agree" in low or "disagree" in low:
        return False
    return True


def deliberate(orch, question: str, live: bool = False, time_cap_s: float = 60.0) -> str | None:
    """Run the Lane-3 verification debate. Returns the final spoken answer, or None to let
    the caller fall back (e.g. brain offline)."""
    question = (question or "").strip()
    if not question:
        return "Give me the decision to weigh, sir, and I'll put it to the council."
    llm = getattr(orch, "llm", None)
    if not (llm and getattr(llm, "available", False)):
        return None
    sysp = getattr(orch, "system_prompt", "You are JARVIS.")
    t0 = time.time()
    live_note = ""

    def _capped() -> bool:
        return (time.time() - t0) > time_cap_s

    # 1 RESEARCH (live search only when the question is also time-sensitive)
    evidence = ""
    if live:
        web = orch.tools.get("web") if getattr(orch, "tools", None) else None
        if web:
            try:
                _status, evidence = web.search(question)
                live_note = "\n[Sources from a live web search; verify timestamps below.]"
            except Exception:
                evidence = ""
    research = llm.chat(
        sysp + " ROLE: RESEARCH. Gather the strongest evidence on both sides. Cite sources "
        "with dates where you have them. Be factual, not persuasive.",
        "Question: " + question + (("\n\nLive results:\n" + evidence) if evidence else ""),
        no_cache=True) or ""

    # 2 ANSWER
    answer = llm.chat(
        sysp + " ROLE: ANSWER. Draft the single best answer strictly from the evidence given. "
        "Do not overstate certainty.",
        "Question: " + question + "\n\nEvidence:\n" + (research or "(none gathered)"),
        no_cache=True) or ""
    if _capped():
        return ("Partial — debate not fully resolved within the time budget, sir. Best answer so far:\n\n"
                + (answer or research or "I couldn't reach the brain."))

    # 3 CHALLENGE (red-team)
    challenge = llm.chat(
        sysp + " ROLE: CHALLENGE. Argue the opposite. Find the flaw in the proposed answer, and "
        "check whether the evidence actually supports it. Be adversarial, not agreeable.",
        "Question: " + question + "\n\nProposed answer:\n" + answer + "\n\nEvidence:\n" + research,
        no_cache=True) or ""

    # 4 VERIFY (fact-check + consensus/confidence verdict)
    verify = llm.chat(
        sysp + " ROLE: VERIFY. Cross-check every material claim against the evidence. Flag anything "
        "unsupported or stale. End with exactly two lines: 'CONSENSUS: yes' or 'CONSENSUS: no', then "
        "'CONFIDENCE: certain|likely|uncertain'.",
        "Question: " + question + "\n\nAnswer:\n" + answer + "\n\nChallenge:\n" + challenge +
        "\n\nEvidence:\n" + research, no_cache=True) or ""

    consensus = _consensus(verify)
    confidence = _confidence(verify)
    high_stakes = _is_high_stakes(question)

    # STEP 4 — disagreement handling tied to stakes
    if (not consensus) and high_stakes:
        return (
            "The agents did not agree, sir. This is a genuine judgement call — here are the positions, "
            "you decide.\n\n"
            "POSITION A (the case for):\n" + (answer or "(none)") + "\n\n"
            "POSITION B (the case against / the risk):\n" + (challenge or "(none)") + "\n\n"
            "What VERIFY flagged:\n" + (verify or "(none)") + "\n\n"
            "Confidence in either side: " + confidence + "." + live_note)

    # 5 SYNTHESIZE — reconcile into one answer (low-stakes, or genuine consensus)
    synth = llm.chat(
        sysp + " ROLE: SYNTHESIZE. Reconcile the answer, the challenge and the verification into the "
        "final response. Lead with the conclusion. If there was minor disagreement, note it in one line "
        "rather than hiding it. NEVER fabricate consensus. Tag the conclusion with confidence "
        "(I am certain / most likely / I am uncertain) and cite sources with timestamps for any "
        "live-data claim.",
        "Question: " + question + "\n\nAnswer:\n" + answer + "\n\nChallenge:\n" + challenge +
        "\n\nVerification:\n" + verify, no_cache=True) or answer or research

    footer = f"\n\n[Verification: confidence {confidence}; agents {'agreed' if consensus else 'partially disagreed'}.]"
    return (synth + footer + live_note).strip()
