"""JARVIS — proactive monitoring daemons.

Four daemon threads run permanently once start_monitors() is called:
  SystemMonitor  — CPU/RAM/disk every 30s; alerts on threshold breach
  TradingMonitor — checks TradingModule halt state every 60s
  FileMonitor    — watches JARVIS root for unexpected file changes every 120s
  ScheduleMonitor— reads memory/scheduled_tasks.jsonl for due reminders

All alerts go into a shared _alert_queue. The terminal channel drains it
between user queries via get_alerts().
"""
from __future__ import annotations
import queue
import threading
import time
import json
from pathlib import Path
from datetime import datetime

_alert_queue: queue.Queue = queue.Queue()
_started = False
_lock    = threading.Lock()

CPU_WARN   = 85   # %
RAM_WARN   = 88   # %
DISK_WARN  = 90   # %


def get_alerts() -> list[str]:
    """Drain all pending alerts. Called by terminal_channel between queries."""
    out = []
    while not _alert_queue.empty():
        try:
            out.append(_alert_queue.get_nowait())
        except queue.Empty:
            break
    return out


def start_monitors(base_dir: str = ".", trader=None, logger=None):
    """Start all daemon monitor threads. Idempotent."""
    global _started
    with _lock:
        if _started:
            return
        _started = True

    for target, kwargs in [
        (_system_monitor,   {"logger": logger}),
        (_trading_monitor,  {"trader": trader, "logger": logger}),
        (_file_monitor,     {"base_dir": base_dir, "logger": logger}),
        (_schedule_monitor, {"base_dir": base_dir, "logger": logger}),
    ]:
        t = threading.Thread(target=target, kwargs=kwargs, daemon=True,
                             name=f"monitor-{target.__name__}")
        t.start()


def _emit(msg: str):
    _alert_queue.put(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _system_monitor(logger=None):
    try:
        import psutil
    except ImportError:
        return
    while True:
        try:
            cpu  = psutil.cpu_percent(interval=1)
            ram  = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            if cpu  >= CPU_WARN:  _emit(f"SYSTEM — CPU at {cpu}% (warn {CPU_WARN}%)")
            if ram  >= RAM_WARN:  _emit(f"SYSTEM — RAM at {ram}% (warn {RAM_WARN}%)")
            if disk >= DISK_WARN: _emit(f"SYSTEM — Disk at {disk}% used (warn {DISK_WARN}%)")
        except Exception:
            pass
        time.sleep(30)


def _trading_monitor(trader=None, logger=None):
    last_halted = None
    while True:
        try:
            if trader is not None:
                halted = getattr(trader, "_halted", False)
                active = getattr(trader, "_active", False)
                if halted and last_halted is not True:
                    _emit("TRADING — auto-halted (daily loss limit). Manual review required.")
                    last_halted = True
                elif not halted:
                    last_halted = False
                pv = getattr(trader, "_portfolio_value_cache", None)
                if pv and active:
                    try:
                        trader.check_daily_halt(pv)
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(60)


def _file_monitor(base_dir: str = ".", logger=None):
    watched = [
        "core/orchestrator.py",
        "core/security_audit.py",
        "core/safety_guard.py",
        "core/permission_manager.py",
    ]
    base = Path(base_dir)
    snapshots: dict[str, float] = {}
    for rel in watched:
        p = base / rel
        if p.exists():
            snapshots[rel] = p.stat().st_mtime
    while True:
        time.sleep(120)
        try:
            for rel in watched:
                p = base / rel
                if not p.exists():
                    continue
                mtime = p.stat().st_mtime
                if rel in snapshots and mtime != snapshots[rel]:
                    _emit(f"FILE CHANGED — {rel} modified externally.")
                snapshots[rel] = mtime
        except Exception:
            pass


def _schedule_monitor(base_dir: str = ".", logger=None):
    schedule_file = Path(base_dir) / "memory" / "scheduled_tasks.jsonl"
    alerted: set[str] = set()
    while True:
        time.sleep(60)
        try:
            if not schedule_file.exists():
                continue
            now = datetime.now()
            with open(schedule_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    task = json.loads(line)
                    due_str = task.get("due", "")
                    title   = task.get("title", "Task")
                    key     = f"{due_str}:{title}"
                    if key in alerted:
                        continue
                    try:
                        due = datetime.fromisoformat(due_str)
                    except ValueError:
                        continue
                    diff = (due - now).total_seconds()
                    if 0 <= diff <= 300:
                        _emit(f"REMINDER — '{title}' due at {due_str}")
                        alerted.add(key)
        except Exception:
            pass
