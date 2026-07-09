"""JARVIS v6.0 — OS control module. Wraps psutil, subprocess, winreg."""
from __future__ import annotations
import os, subprocess, sys
from typing import Any

try: import psutil; _PSUTIL = True
except ImportError: _PSUTIL = False

try:
    import winreg; _WINREG = True
except ImportError: _WINREG = False

try:
    import wmi; _WMI = True
except ImportError: _WMI = False


def list_processes(sort_by: str = "cpu") -> list[dict]:
    if not _PSUTIL: return [{"error": "psutil not installed"}]
    procs = []
    for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
        try: procs.append(p.info)
        except psutil.NoSuchProcess: pass
    key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
    return sorted(procs, key=lambda x: x.get(key) or 0, reverse=True)[:30]


def kill_process(name_or_pid: str | int, confirmed: bool = False) -> str:
    if not _PSUTIL: return "psutil not installed."
    killed = []
    for p in psutil.process_iter(["pid","name"]):
        try:
            if str(p.info["pid"]) == str(name_or_pid) or \
               p.info["name"].lower() == str(name_or_pid).lower():
                p.kill(); killed.append(p.info["name"])
        except Exception: pass
    return f"Killed: {killed}" if killed else f"No process matching '{name_or_pid}'."


def start_app(path: str, confirmed: bool = False) -> str:
    try:
        subprocess.Popen(path, shell=True)
        return f"Started: {path}"
    except Exception as e: return f"Failed: {e}"


def system_info() -> dict[str, Any]:
    info: dict = {"platform": sys.platform}
    if _PSUTIL:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        info.update({
            "cpu_count": psutil.cpu_count(),
            "cpu_pct": psutil.cpu_percent(interval=0.5),
            "ram_gb": round(vm.total / 1e9, 1),
            "ram_used_pct": vm.percent,
            "disk_free_gb": round(disk.free / 1e9, 1),
            "disk_pct": disk.percent,
        })
    return info


def get_installed_apps() -> list[str]:
    apps = []
    if _WINREG:
        key_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for kp in key_paths:
                try:
                    with winreg.OpenKey(root, kp) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
                                name, _ = winreg.QueryValueEx(sub, "DisplayName")
                                apps.append(name)
                            except Exception: pass
                except Exception: pass
    return sorted(set(apps))


def read_registry(hive: str, path: str, value: str) -> Any:
    if not _WINREG: return "winreg not available (not Windows)"
    hives = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    try:
        with winreg.OpenKey(hives.get(hive.upper(), winreg.HKEY_LOCAL_MACHINE), path) as k:
            val, _ = winreg.QueryValueEx(k, value)
            return val
    except Exception as e: return f"Registry read error: {e}"


def write_registry(hive: str, path: str, value: str, data: Any,
                   confirmed: bool = False) -> str:
    if not confirmed: return "Class C: registry write requires double confirmation."
    if not _WINREG: return "winreg not available."
    hives = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    try:
        with winreg.CreateKey(hives.get(hive.upper(), winreg.HKEY_LOCAL_MACHINE), path) as k:
            winreg.SetValueEx(k, value, 0, winreg.REG_SZ, str(data))
        return f"Registry written: {hive}\\{path}\\{value}={data}"
    except Exception as e: return f"Registry write error: {e}"


def shutdown(action: str = "shutdown", confirmed: bool = False) -> str:
    if not confirmed: return f"Class C: '{action}' requires double confirmation."
    cmds = {"shutdown": "shutdown /s /t 0", "restart": "shutdown /r /t 0",
            "sleep": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"}
    cmd = cmds.get(action.lower(), f"shutdown /s /t 0")
    os.system(cmd)
    return f"Executing: {action}"


def get_services() -> list[dict]:
    if not _WMI: return [{"error": "wmi not installed"}]
    try:
        c = wmi.WMI()
        return [{"name": s.Name, "state": s.State, "mode": s.StartMode}
                for s in c.Win32_Service()]
    except Exception as e: return [{"error": str(e)}]


def manage_service(name: str, action: str, confirmed: bool = False) -> str:
    try:
        subprocess.run(f"sc {action} {name}", shell=True, check=True,
                       capture_output=True)
        return f"Service '{name}' {action}ed."
    except Exception as e: return f"Service error: {e}"
