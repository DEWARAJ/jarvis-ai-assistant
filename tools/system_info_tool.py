"""System Information Tool for JARVIS OS.

Gives JARVIS real-time awareness of the machine it is running on:
  - CPU usage & core count
  - RAM used / total
  - Disk space per drive
  - Battery level & charging status
  - Network interfaces & approximate speed
  - System uptime
  - Running process count
  - GPU info (if available)

Uses psutil (cross-platform, no admin needed).
Gracefully degrades if psutil is not installed — returns install hint.
"""
from __future__ import annotations
import os, sys, platform, datetime
from tools.base_tool import BaseTool

_HINT = "System info needs one install: pip install psutil  (then restart JARVIS)."


def _psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        return None


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


class SystemInfoTool(BaseTool):
    name = "system_info"
    scope = "hardware & OS diagnostics"

    # ── Full snapshot ──────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """Return a full system status snapshot as a dict + human-readable text."""
        ps = _psutil()
        if not ps:
            return {"ok": False, "spoken": _HINT, "text": _HINT}

        lines = []

        # ── OS & uptime ──
        boot = datetime.datetime.fromtimestamp(ps.boot_time())
        uptime = datetime.datetime.now() - boot
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m = rem // 60
        lines.append(f"System: {platform.system()} {platform.release()} | "
                     f"Uptime: {h}h {m}m")

        # ── CPU ──
        try:
            cpu_pct = ps.cpu_percent(interval=0.5)
            cores = ps.cpu_count(logical=True)
            freq = ps.cpu_freq()
            freq_str = f" @ {freq.current:.0f} MHz" if freq else ""
            lines.append(f"CPU: {cpu_pct:.1f}% used | {cores} logical cores{freq_str}")
        except Exception as e:
            lines.append(f"CPU: unavailable ({e})")

        # ── RAM ──
        try:
            ram = ps.virtual_memory()
            lines.append(
                f"RAM: {_fmt_bytes(ram.used)} / {_fmt_bytes(ram.total)} "
                f"({ram.percent:.1f}% used)"
            )
        except Exception as e:
            lines.append(f"RAM: unavailable ({e})")

        # ── Disk ──
        try:
            parts = ps.disk_partitions(all=False)
            disk_lines = []
            for p in parts[:4]:   # cap at 4 drives
                try:
                    u = ps.disk_usage(p.mountpoint)
                    disk_lines.append(
                        f"  {p.device}: {_fmt_bytes(u.used)} / {_fmt_bytes(u.total)} "
                        f"({u.percent:.1f}% used)"
                    )
                except Exception:
                    pass
            if disk_lines:
                lines.append("Disk:")
                lines.extend(disk_lines)
        except Exception as e:
            lines.append(f"Disk: unavailable ({e})")

        # ── Battery ──
        try:
            bat = ps.sensors_battery()
            if bat is not None:
                status = "charging" if bat.power_plugged else "on battery"
                secs = bat.secsleft
                if secs and secs > 0 and not bat.power_plugged:
                    h2, m2 = divmod(secs, 3600)
                    rem_str = f" | ~{h2}h {m2 // 60}m remaining"
                else:
                    rem_str = ""
                lines.append(
                    f"Battery: {bat.percent:.0f}% ({status}){rem_str}"
                )
            else:
                lines.append("Battery: no battery detected (desktop)")
        except Exception:
            pass

        # ── Network ──
        try:
            addrs = ps.net_if_addrs()
            active = [
                f"{iface}: {info[0].address}"
                for iface, info in addrs.items()
                if info and not iface.startswith("Loopback") and "127." not in (info[0].address or "")
            ]
            if active:
                lines.append("Network: " + " | ".join(active[:3]))
        except Exception:
            pass

        # ── Processes ──
        try:
            proc_count = len(ps.pids())
            lines.append(f"Processes: {proc_count} running")
        except Exception:
            pass

        text = "\n".join(lines)
        spoken = self._spoken_summary(ps)
        return {"ok": True, "text": text, "spoken": spoken, "raw": lines}

    def _spoken_summary(self, ps) -> str:
        """Compact spoken version — 2-3 sentences."""
        parts = []
        try:
            cpu = ps.cpu_percent(interval=0.3)
            ram = ps.virtual_memory()
            parts.append(
                f"CPU is at {cpu:.0f} percent and RAM at {ram.percent:.0f} percent."
            )
        except Exception:
            pass
        try:
            bat = ps.sensors_battery()
            if bat:
                status = "charging" if bat.power_plugged else "on battery"
                parts.append(f"Battery is at {bat.percent:.0f} percent, {status}.")
        except Exception:
            pass
        try:
            disks = ps.disk_partitions(all=False)
            for d in disks[:1]:
                u = ps.disk_usage(d.mountpoint)
                parts.append(f"Primary disk: {u.percent:.0f} percent used, "
                             f"{_fmt_bytes(u.free)} free.")
        except Exception:
            pass
        return " ".join(parts) if parts else "System info retrieved."

    # ── Individual queries ─────────────────────────────────────────────────────

    def cpu(self) -> dict:
        ps = _psutil()
        if not ps:
            return {"ok": False, "spoken": _HINT}
        try:
            pct = ps.cpu_percent(interval=0.5)
            cores = ps.cpu_count(logical=True)
            return {"ok": True, "percent": pct, "cores": cores,
                    "spoken": f"CPU is at {pct:.1f} percent across {cores} cores, sir."}
        except Exception as e:
            return {"ok": False, "spoken": f"CPU unavailable: {e}"}

    def ram(self) -> dict:
        ps = _psutil()
        if not ps:
            return {"ok": False, "spoken": _HINT}
        try:
            r = ps.virtual_memory()
            return {"ok": True, "percent": r.percent,
                    "used": r.used, "total": r.total,
                    "spoken": (f"RAM: {_fmt_bytes(r.used)} used of {_fmt_bytes(r.total)}, "
                               f"{r.percent:.1f} percent utilisation, sir.")}
        except Exception as e:
            return {"ok": False, "spoken": f"RAM unavailable: {e}"}

    def battery(self) -> dict:
        ps = _psutil()
        if not ps:
            return {"ok": False, "spoken": _HINT}
        try:
            bat = ps.sensors_battery()
            if bat is None:
                return {"ok": True, "spoken": "No battery — this appears to be a desktop, sir."}
            status = "charging" if bat.power_plugged else "discharging"
            secs = bat.secsleft
            if secs and secs > 0 and not bat.power_plugged:
                h, m = divmod(secs, 3600)
                time_str = f", approximately {h} hours and {m // 60} minutes remaining"
            else:
                time_str = ""
            return {
                "ok": True, "percent": bat.percent, "plugged": bat.power_plugged,
                "spoken": f"Battery is at {bat.percent:.0f} percent, currently {status}{time_str}, sir.",
            }
        except Exception as e:
            return {"ok": False, "spoken": f"Battery info unavailable: {e}"}

    def disk(self) -> dict:
        ps = _psutil()
        if not ps:
            return {"ok": False, "spoken": _HINT}
        try:
            parts = ps.disk_partitions(all=False)
            lines = []
            for p in parts[:4]:
                try:
                    u = ps.disk_usage(p.mountpoint)
                    lines.append(
                        f"{p.device}: {_fmt_bytes(u.free)} free of {_fmt_bytes(u.total)}"
                    )
                except Exception:
                    pass
            spoken = "Disk space — " + "; ".join(lines) + ", sir." if lines else "No disk info."
            return {"ok": True, "spoken": spoken, "drives": lines}
        except Exception as e:
            return {"ok": False, "spoken": f"Disk info unavailable: {e}"}

    def top_processes(self, n: int = 5) -> dict:
        """Return top N processes by CPU usage."""
        ps = _psutil()
        if not ps:
            return {"ok": False, "spoken": _HINT}
        try:
            procs = []
            for proc in ps.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    procs.append(proc.info)
                except Exception:
                    pass
            procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
            top = procs[:n]
            lines = [
                f"{p['name']} (PID {p['pid']}): CPU {p.get('cpu_percent', 0):.1f}%, "
                f"RAM {p.get('memory_percent', 0):.1f}%"
                for p in top
            ]
            spoken = ("Top processes by CPU: "
                      + "; ".join(f"{p['name']} at {p.get('cpu_percent', 0):.0f} percent"
                                  for p in top[:3])
                      + ", sir.")
            return {"ok": True, "spoken": spoken, "processes": lines}
        except Exception as e:
            return {"ok": False, "spoken": f"Process list unavailable: {e}"}
