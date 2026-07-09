"""JARVIS v6.0 — File monitor: core file changes and new downloads."""
from __future__ import annotations
from pathlib import Path
from proactive.system_monitor import Alert, Priority

_watched_dirs: list[str] = []
_core_files = [
    "jarvis_main.py","security.py","llm_router.py",
    "core/orchestrator.py","core/security_audit.py",
]

def watch_dir(path: str) -> None:
    _watched_dirs.append(path)

def run(alert_queue, shutdown_event) -> None:
    base = Path(".")
    snapshots: dict[str, float] = {}
    for f in _core_files:
        p = base / f
        if p.exists(): snapshots[str(p)] = p.stat().st_mtime
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        for f in downloads.iterdir():
            snapshots[str(f)] = f.stat().st_mtime
    while not shutdown_event.is_set():
        try:
            for f in _core_files:
                p = base / f
                if not p.exists(): continue
                mtime = p.stat().st_mtime
                if str(p) in snapshots and mtime != snapshots[str(p)]:
                    alert_queue.put(Alert(f"CORE FILE CHANGED: {f}",
                                          Priority.HIGH, "file_monitor"))
                snapshots[str(p)] = mtime
            if downloads.exists():
                for f in downloads.iterdir():
                    if str(f) not in snapshots:
                        alert_queue.put(Alert(f"New download: {f.name}",
                                              Priority.LOW, "file_monitor"))
                    snapshots[str(f)] = f.stat().st_mtime
        except Exception: pass
        shutdown_event.wait(timeout=120)
