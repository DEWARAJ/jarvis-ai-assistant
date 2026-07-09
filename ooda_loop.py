"""JARVIS v6.0 — OODA Loop: Observe-Orient-Decide-Act cognitive engine.

Independent thinking as a SEPARATE Claude API call before acting.
Returns tagged text: [OBS] ... [ORI] ... [DEC] ... [ACT] ...
"""
from __future__ import annotations
import os

_OODA_SYSTEM = """\
You are JARVIS's internal reasoning engine executing an OODA loop.
Given a situation, reason through all 4 phases:

[OBS] What is actually happening? Facts only, no interpretation.
[ORI] What does this mean? Context, patterns, implications.
[DEC] What should be done? Evaluate options, pick best.
[ACT] What is the concrete next action? Be specific.

Keep each phase concise (2-4 sentences). Tag each section exactly as shown."""


def run_ooda(situation: str, history: list | None = None) -> str:
    """Run independent OODA reasoning. Returns full tagged analysis."""
    key = os.getenv("ANTHROPIC_API_KEY","")
    if not key: return "[OBS] No API key. [ORI] Cannot reason. [DEC] Skip. [ACT] Request key."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msgs = list(history or []) + [{"role":"user","content":situation}]
        r = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=_OODA_SYSTEM,
            messages=msgs)
        return r.content[0].text
    except Exception as e:
        return f"[OBS] OODA error: {e}. [ORI] API unavailable. [DEC] Skip OODA. [ACT] Proceed without."


def extract_action(ooda_output: str) -> str:
    """Pull just the [ACT] section from OODA output."""
    if "[ACT]" in ooda_output:
        act = ooda_output.split("[ACT]")[-1].strip()
        # Strip any trailing tags
        for tag in ["[OBS]","[ORI]","[DEC]","[ACT]"]:
            if tag in act: act = act.split(tag)[0].strip()
        return act
    return ooda_output


def strip_ooda_tags(text: str) -> str:
    """Remove OODA tags for display/TTS."""
    import re
    return re.sub(r'\[(OBS|ORI|DEC|ACT)\]', '', text).strip()


def format_ooda_display(ooda_output: str) -> str:
    """Format OODA output for terminal display."""
    sections = {
        "OBS": "Observe",
        "ORI": "Orient",
        "DEC": "Decide",
        "ACT": "Act",
    }
    lines = []
    for tag, label in sections.items():
        marker = f"[{tag}]"
        if marker in ooda_output:
            text = ooda_output.split(marker)[-1]
            for next_tag in sections:
                if f"[{next_tag}]" in text and next_tag != tag:
                    text = text.split(f"[{next_tag}]")[0]
            lines.append(f"  {label}: {text.strip()}")
    return "\n".join(lines) if lines else ooda_output
