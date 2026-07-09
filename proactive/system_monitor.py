"""JARVIS v6.0 — System monitor: CPU, RAM, disk alerts."""
from __future__ import annotations
import time
from dataclasses import dataclass
from enum import Enum

class Priority(Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"

@dataclass
class Alert:
    message:  str
    priority: Priority
    source:   str = "system_monitor"

_cpu_high_start: float | None = None

def run(alert_queue, shutdown_event) -> None:
    try: import psutil
    except ImportError: return
    global _cpu_high_start
    while not shutdown_event.is_set():
        try:
            cpu  = psutil.cpu_percent(interval=2)
            ram  = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            now  = time.time()
            if cpu >= 95:
                alert_queue.put(Alert(f"CPU at {cpu:.0f}%", Priority.CRITICAL))
            elif cpu >= 80:
                if _cpu_high_start is None: _cpu_high_start = now
                elif now - _cpu_high_start > 300:
                    alert_queue.put(Alert(f"CPU above 80% for 5+ min", Priority.HIGH))
            else: _cpu_high_start = None
            if ram >= 90: alert_queue.put(Alert(f"RAM at {ram:.0f}%", Priority.CRITICAL))
            if disk >= 95: alert_queue.put(Alert(f"Disk at {disk:.0f}%", Priority.HIGH))
            elif disk >= 85: alert_queue.put(Alert(f"Disk at {disk:.0f}%", Priority.MEDIUM))
        except Exception: pass
        shutdown_event.wait(timeout=28)
