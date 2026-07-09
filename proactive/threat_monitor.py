"""JARVIS v6.0 — Threat monitor: new network devices, suspicious processes."""
from __future__ import annotations
from proactive.system_monitor import Alert, Priority

_known_devices: set[str] = set()

def run(alert_queue, shutdown_event) -> None:
    while not shutdown_event.is_set():
        try:
            try:
                from modules.network_control import scan_network
                devices = scan_network()
                for d in devices:
                    host = d.get("host","")
                    if host and host not in _known_devices:
                        if _known_devices:
                            alert_queue.put(Alert(f"NEW DEVICE: {host}",
                                                  Priority.HIGH, "threat_monitor"))
                        _known_devices.add(host)
            except Exception: pass
            try:
                from modules.security_module import monitor_processes
                for p in monitor_processes():
                    alert_queue.put(Alert(
                        f"SUSPICIOUS PROCESS: {p.get('name','')} PID {p.get('pid','')}",
                        Priority.HIGH, "threat_monitor"))
            except Exception: pass
        except Exception: pass
        shutdown_event.wait(timeout=300)
