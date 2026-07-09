"""
agent_fabric.py  —  JARVIS v7.0   [DEPRECATED]

Multi-agent coordinator for the legacy jarvis_main.py system. Each sub-agent runs in
its own daemon thread; results flow back via result_queue.

DEPRECATED: the canonical brain is core/orchestrator.py, which uses
core/agent_registry.py for sub-agents. This module is only reached by the legacy
jarvis_main.py entry point. Kept working for backward compatibility.
"""
from __future__ import annotations
import json, uuid, threading, queue
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

BLACKBOARD = Path("memory/shared_blackboard.json")

# ── Task dataclass ────────────────────────────────────────────────────────────
@dataclass
class AgentTask:
    id:           str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_type:   str = ""
    task:         str = ""
    priority:     str = "medium"
    status:       str = "queued"   # queued|running|complete|failed
    result:       str = ""
    created_at:   str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""


# ── Sub-agent system prompts ──────────────────────────────────────────────────
_PROMPTS: dict[str, str] = {
    "research": (
        "You are JARVIS ResearchAgent. Deep internet research specialist. "
        "Search multiple sources, synthesise findings, return dense factual summaries. "
        "Cite sources. Use web_search tool for every factual claim."
    ),
    "trading": (
        "You are JARVIS TradingAgent. Market analysis and trade execution specialist. "
        "Check Alpaca status, analyse conditions, execute with strict risk management. "
        "Hard rules: never risk >2% per trade, halt at 5% daily loss."
    ),
    "build": (
        "You are JARVIS BuildAgent. Production code and application building specialist. "
        "Write complete, tested Python. Never deliver partial implementations."
    ),
    "monitor": (
        "You are JARVIS MonitorAgent. Continuous system and environment watcher. "
        "Surface anomalies proactively. Be terse and factual."
    ),
    "communication": (
        "You are JARVIS CommunicationAgent. Email, SMS, calendar, notifications. "
        "Show full content before sending. Never send without explicit confirmation."
    ),
}


# ── Sub-agent runner ──────────────────────────────────────────────────────────
class SubAgent:
    def __init__(self, agent_type: str, result_queue: queue.Queue):
        self.agent_type   = agent_type
        self.result_queue = result_queue

    def run(self, task: AgentTask) -> None:
        task.status = "running"
        system = _PROMPTS.get(
            self.agent_type,
            "You are a JARVIS sub-agent. Complete the assigned task precisely."
        )
        try:
            from tool_engine import react_loop
            task.result = react_loop(
                user_message=task.task,
                system_prompt=system,
                history=[],
                verbose=False,
            )
            task.status = "complete"
        except Exception as e:
            task.result = f"Sub-agent error: {e}"
            task.status = "failed"
        task.completed_at = datetime.now().isoformat()
        self.result_queue.put(task)


# ── Coordinator ───────────────────────────────────────────────────────────────
class AgentFabric:
    def __init__(self):
        self.result_queue: queue.Queue    = queue.Queue()
        self._tasks: dict[str, AgentTask] = {}
        self._lock   = threading.Lock()
        self._load_blackboard()

    def spawn(self, agent_type: str, task: str, priority: str = "medium") -> str:
        """Spawn sub-agent in daemon thread. Returns task ID."""
        t = AgentTask(agent_type=agent_type, task=task, priority=priority)
        with self._lock:
            self._tasks[t.id] = t
        agent = SubAgent(agent_type, self.result_queue)  # ONE instance only
        thread = threading.Thread(
            target=agent.run,
            args=(t,), daemon=True,
            name=f"JARVIS-{agent_type}-{t.id}",
        )
        thread.start()
        print(f"[FABRIC] spawned {agent_type} | {task[:60]} | id={t.id}")
        self._save_blackboard()
        return t.id

    def collect_results(self, timeout: float = 0.05) -> list[AgentTask]:
        """Non-blocking drain of completed results."""
        done: list[AgentTask] = []
        while True:
            try:
                t = self.result_queue.get(timeout=timeout)
                done.append(t)
                with self._lock:
                    self._tasks[t.id] = t
                self._save_blackboard()
            except queue.Empty:
                break
        return done

    def get_status(self) -> str:
        with self._lock:
            tasks = list(self._tasks.values())
        if not tasks:
            return "No sub-agents active."
        lines = ["[AGENT FABRIC]"]
        for t in tasks[-15:]:
            lines.append(
                f"  [{t.status.upper():8}] {t.agent_type:12} | {t.task[:40]} | {t.id}"
            )
        return "\n".join(lines)

    def _load_blackboard(self) -> None:
        BLACKBOARD.parent.mkdir(exist_ok=True)
        if not BLACKBOARD.exists():
            return
        try:
            data = json.loads(BLACKBOARD.read_text(encoding="utf-8"))
            for item in data.get("tasks", []):
                valid = {k: v for k, v in item.items()
                         if k in AgentTask.__dataclass_fields__}
                t = AgentTask(**valid)
                self._tasks[t.id] = t
        except Exception:
            pass

    def _save_blackboard(self) -> None:
        with self._lock:
            tasks = [t.__dict__ for t in list(self._tasks.values())[-50:]]
        try:
            BLACKBOARD.write_text(
                json.dumps(
                    {"updated": datetime.now().isoformat(), "tasks": tasks},
                    indent=2, ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────
_fabric: Optional[AgentFabric] = None


def get_fabric() -> AgentFabric:
    global _fabric
    if _fabric is None:
        _fabric = AgentFabric()
    return _fabric
