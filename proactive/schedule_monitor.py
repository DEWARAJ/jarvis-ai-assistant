"""JARVIS v6.0 — Schedule monitor: reminders and recurring tasks."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from proactive.system_monitor import Alert, Priority

_SCHEDULE_FILE = Path("memory") / "scheduled_tasks.jsonl"
_alerted: set[str] = set()

def add_reminder(title: str, due: str, recurring: bool = False,
                 recur_time: str = "") -> str:
    _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {"title": title, "due": due, "recurring": recurring,
             "recur_time": recur_time, "created": datetime.now().isoformat()}
    with open(_SCHEDULE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return f"Reminder set: '{title}' at {due}"

def run(alert_queue, shutdown_event) -> None:
    while not shutdown_event.is_set():
        try:
            if not _SCHEDULE_FILE.exists():
                shutdown_event.wait(timeout=60); continue
            now = datetime.now()
            with open(_SCHEDULE_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    task = json.loads(line)
                    due_str = task.get("due","")
                    title   = task.get("title","Task")
                    key     = f"{due_str}:{title}"
                    if key in _alerted: continue
                    try:
                        due = datetime.fromisoformat(due_str)
                        diff = (due - now).total_seconds()
                        if 0 <= diff <= 300:
                            alert_queue.put(Alert(f"REMINDER: {title}",
                                                  Priority.HIGH, "schedule_monitor"))
                            _alerted.add(key)
                    except ValueError:
                        try:
                            h, m = map(int, due_str.split(":"))
                            if now.hour == h and now.minute == m:
                                day_key = f"{due_str}:{title}:{now.date()}"
                                if day_key not in _alerted:
                                    alert_queue.put(Alert(f"DAILY: {title}",
                                        Priority.MEDIUM, "schedule_monitor"))
                                    _alerted.add(day_key)
                        except Exception: pass
        except Exception: pass
        shutdown_event.wait(timeout=60)
