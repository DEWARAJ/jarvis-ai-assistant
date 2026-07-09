"""JARVIS v6.0 — Mission engine: classify, plan, track multi-step missions."""
from __future__ import annotations
import os, json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field

_MISSIONS_PATH = Path("missions")
_MISSIONS_PATH.mkdir(parents=True, exist_ok=True)

_MISSION_TYPES = {
    "research":     ["FRIDAY web search","analyze sources","synthesize findings","report"],
    "trade":        ["market analysis","risk assessment","place order","monitor position"],
    "automation":   ["plan steps","request permissions","execute","verify"],
    "build":        ["specify","design","implement","test","deploy"],
    "communication":["draft","review","confirm","send"],
    "analysis":     ["gather data","process","identify patterns","conclude"],
    "security":     ["threat assess","scan","classify","respond"],
}

_CLASSIFY_SYSTEM = """\
You classify user requests into mission types. Reply with ONE word from this list:
research, trade, automation, build, communication, analysis, security, general

No other words. Just the mission type."""


@dataclass
class Mission:
    id:          str
    title:       str
    type:        str
    steps:       list[str] = field(default_factory=list)
    completed:   list[int] = field(default_factory=list)
    status:      str = "active"
    created:     str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    result:      str = ""


def classify_mission(text: str) -> str:
    """Classify request into mission type using LLM."""
    key = os.getenv("ANTHROPIC_API_KEY","")
    if not key:
        # Keyword fallback
        t = text.lower()
        for mtype in _MISSION_TYPES:
            if mtype in t: return mtype
        return "general"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        r = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=10,
            system=_CLASSIFY_SYSTEM,
            messages=[{"role":"user","content":text}])
        mtype = r.content[0].text.strip().lower()
        return mtype if mtype in _MISSION_TYPES else "general"
    except Exception:
        return "general"


def create_mission(title: str, text: str) -> Mission:
    mtype = classify_mission(text)
    steps = _MISSION_TYPES.get(mtype, ["analyze","execute","verify"])
    m = Mission(
        id=f"M{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title=title, type=mtype, steps=steps)
    _save_mission(m)
    return m


def _save_mission(m: Mission) -> None:
    p = _MISSIONS_PATH / f"{m.id}.json"
    p.write_text(json.dumps(asdict(m), indent=2, ensure_ascii=False))


def load_mission(mission_id: str) -> Mission | None:
    p = _MISSIONS_PATH / f"{mission_id}.json"
    if not p.exists(): return None
    data = json.loads(p.read_text())
    return Mission(**data)


def list_missions(status: str = "active") -> list[Mission]:
    missions = []
    for f in _MISSIONS_PATH.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            m = Mission(**data)
            if status == "all" or m.status == status:
                missions.append(m)
        except Exception: pass
    return sorted(missions, key=lambda x: x.created, reverse=True)


def advance_mission(mission_id: str, step_index: int) -> str:
    m = load_mission(mission_id)
    if not m: return f"Mission {mission_id} not found."
    if step_index not in m.completed:
        m.completed.append(step_index)
    if len(m.completed) >= len(m.steps):
        m.status = "completed"
    _save_mission(m)
    next_step = m.steps[step_index + 1] if step_index + 1 < len(m.steps) else "Mission complete."
    return f"Step {step_index + 1} done. Next: {next_step}"


def format_mission(m: Mission) -> str:
    lines = [f"MISSION [{m.id}]: {m.title} ({m.type.upper()})",
             f"Status: {m.status}"]
    for i, step in enumerate(m.steps):
        mark = "v" if i in m.completed else "o"
        lines.append(f"  {mark} {i+1}. {step}")
    if m.result: lines.append(f"Result: {m.result}")
    return "\n".join(lines)


def get_active_summary() -> str:
    missions = list_missions("active")
    if not missions: return "No active missions."
    return "\n".join(f"- {m.id}: {m.title} [{m.type}]" for m in missions[:5])
