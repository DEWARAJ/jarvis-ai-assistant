"""
autonomous_engine.py  —  JARVIS v9.0  ENGINE 4 (Autonomous Operation)
Goal tree, opportunity scanner, and overnight task runner. Complements the existing
core/autonomy_daemon.py (the Iron-Man self-driving loop) — this adds tracked goals,
a daily opportunity scan, and a persistent overnight queue.

Storage (anchored to project root, not CWD):
  memory/goal_tree.json        goals + milestones
  memory/opportunities.jsonl   scanned opportunities
  memory/overnight_log.jsonl   completed overnight tasks
"""
from __future__ import annotations
import json, os, time, threading
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_MEM = _ROOT / "memory"
_MEM.mkdir(exist_ok=True)
GOALS_FILE = _MEM / "goal_tree.json"
OPPORTUNITIES_FILE = _MEM / "opportunities.jsonl"
OVERNIGHT_LOG = _MEM / "overnight_log.jsonl"


def _anthropic_key() -> str:
    try:
        from tool_engine import _resolve_anthropic_key
        return _resolve_anthropic_key()
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")


# ── GOAL TREE ─────────────────────────────────────────────────────────────────
DEFAULT_GOALS = {
    "goals": [
        {"id": "g1", "title": "Land robotics/mechatronics engineering job in US",
         "priority": "critical", "milestones": [
            {"id": "g1m1", "title": "GitHub portfolio with 4 strong repos", "done": False},
            {"id": "g1m2", "title": "Resume at 9/10 with ATS keywords", "done": False},
            {"id": "g1m3", "title": "50 applications sent", "done": False},
            {"id": "g1m4", "title": "5 interviews scheduled", "done": False},
            {"id": "g1m5", "title": "Offer received", "done": False}]},
        {"id": "g2", "title": "Profitable algorithmic trading system",
         "priority": "high", "milestones": [
            {"id": "g2m1", "title": "HMM bot live paper trading 30 days", "done": False},
            {"id": "g2m2", "title": "Sharpe > 1.0 on paper", "done": False},
            {"id": "g2m3", "title": "Live trading with $1k account", "done": False},
            {"id": "g2m4", "title": "Consistent monthly profit 3 months", "done": False}]},
        {"id": "g3", "title": "JARVIS fully autonomous frontier AI agent",
         "priority": "high", "milestones": [
            {"id": "g3m1", "title": "Stable 9/10 with all fixes", "done": True},
            {"id": "g3m2", "title": "Immortal memory across sessions", "done": False},
            {"id": "g3m3", "title": "Autonomous overnight tasks working", "done": False},
            {"id": "g3m4", "title": "Voice interface fully stable", "done": False}]},
    ]
}


def load_goals() -> dict:
    if not GOALS_FILE.exists():
        GOALS_FILE.write_text(json.dumps(DEFAULT_GOALS, indent=2), encoding="utf-8")
        return DEFAULT_GOALS
    try:
        return json.loads(GOALS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_GOALS


def show_goal_tree() -> str:
    goals = load_goals()
    lines = ["JARVIS GOAL TREE:"]
    for g in goals["goals"]:
        done = sum(1 for m in g["milestones"] if m.get("done"))
        total = len(g["milestones"])
        pct = int(done / total * 100) if total else 0
        bar = "#" * int(pct / 10) + "-" * (10 - int(pct / 10))
        lines.append(f"\n  [{g['priority'].upper():8}] {g['title']}")
        lines.append(f"  [{bar}] {pct}% ({done}/{total})")
        for m in g["milestones"]:
            lines.append(f"    {'[x]' if m.get('done') else '[ ]'} {m['title']}")
    return "\n".join(lines)


def mark_milestone_done(goal_id: str, milestone_id: str) -> str:
    goals = load_goals()
    for g in goals["goals"]:
        if g["id"] == goal_id:
            for m in g["milestones"]:
                if m["id"] == milestone_id:
                    m["done"] = True
                    m["completed_at"] = datetime.now().isoformat()
                    GOALS_FILE.write_text(json.dumps(goals, indent=2), encoding="utf-8")
                    return f"Milestone complete: {m['title']}"
    return "Milestone not found."


# ── OPPORTUNITY SCANNER ───────────────────────────────────────────────────────
_SCANS = [
    ("job", "robotics mechatronics engineer entry level hiring 2026 NYC Boston"),
    ("job", "embedded systems firmware engineer OPT STEM sponsorship 2026"),
    ("trading", "algorithmic trading momentum breakout signals this week"),
    ("business", "AI SaaS micro-startup profitable niche 2026 solo founder"),
]


def scan_opportunities() -> list[dict]:
    """Daily scan for opportunities relevant to Dew. Returns the list found."""
    try:
        from internet_layer import live_search
    except Exception:
        return []
    found = []
    for category, query in _SCANS:
        try:
            results = live_search(query, count=3)
            for r in (results.get("results", []) or [])[:2]:
                opp = {"ts": datetime.now().isoformat(), "category": category,
                       "title": r.get("title", ""), "url": r.get("url", ""),
                       "snippet": (r.get("snippet") or r.get("description") or "")[:200],
                       "relevance_score": 0.6}
                found.append(opp)
                try:
                    from memory.vector_store import store as vstore
                    vstore(f"[OPPORTUNITY:{category}] {opp['title']} — {opp['snippet']}",
                           category="opportunity", tags=[category], source=opp["url"])
                except Exception:
                    pass
        except Exception:
            pass
    with OPPORTUNITIES_FILE.open("a", encoding="utf-8") as f:
        for opp in found:
            f.write(json.dumps(opp, ensure_ascii=False) + "\n")
    return found


def get_todays_opportunities() -> str:
    if not OPPORTUNITIES_FILE.exists():
        return "No opportunities scanned yet. Run /scan."
    cutoff = datetime.now() - timedelta(days=1)
    entries = [json.loads(l) for l in OPPORTUNITIES_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    recent = [e for e in entries if datetime.fromisoformat(e["ts"]) > cutoff]
    if not recent:
        return "No new opportunities in the last 24 hours."
    lines = [f"OPPORTUNITIES ({len(recent)} today):"]
    for e in sorted(recent, key=lambda x: x.get("relevance_score", 0), reverse=True)[:8]:
        sc = int(e.get("relevance_score", 0) * 100)
        lines.append(f"  [{e['category'].upper():8}] {sc}% — {e['title'][:50]}")
        if e.get("url"):
            lines.append(f"           {e['url'][:60]}")
    return "\n".join(lines)


# ── OVERNIGHT TASK RUNNER ─────────────────────────────────────────────────────
def run_overnight_tasks(tasks: list[str] | None = None) -> list[dict]:
    """Execute queued overnight tasks via the Hermes brain (react_loop). Returns results."""
    try:
        from tool_engine import react_loop
    except Exception:
        return []
    queue = tasks or []
    if not queue:
        return []
    results = []
    SYS = ("You are JARVIS executing an overnight autonomous task for Dew. Complete it fully "
           "and precisely. Produce concrete, actionable output — not a summary of what you would do.")
    for task in queue[:10]:
        try:
            out = react_loop(user_message=task, system_prompt=SYS, history=[],
                             max_iterations=6, verbose=False)
            entry = {"ts": datetime.now().isoformat(), "task": task,
                     "result_preview": (out or "")[:300], "status": "complete"}
        except Exception as e:
            entry = {"ts": datetime.now().isoformat(), "task": task,
                     "result_preview": f"failed: {e}", "status": "failed"}
        results.append(entry)
        with OVERNIGHT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        time.sleep(1)
    return results


def get_overnight_report() -> str:
    if not OVERNIGHT_LOG.exists():
        return ""
    entries = [json.loads(l) for l in OVERNIGHT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    cutoff = datetime.now() - timedelta(days=1)
    recent = [e for e in entries if datetime.fromisoformat(e["ts"]) > cutoff]
    if not recent:
        return ""
    lines = [f"JARVIS OVERNIGHT REPORT — {len(recent)} tasks:"]
    for e in recent:
        icon = "[x]" if e.get("status") == "complete" else "[!]"
        lines.append(f"  {icon} {e['task'][:54]}")
        if e.get("result_preview"):
            lines.append(f"      -> {e['result_preview'][:60]}")
    return "\n".join(lines)
