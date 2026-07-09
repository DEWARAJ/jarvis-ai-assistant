"""
daemon_wrapper.py  —  JARVIS v7.0
Persistent background service wrapper.

Windows: NSSM wraps jarvis_main.py as Windows Service
Linux:   systemd unit file

Usage:
  python daemon_wrapper.py --install
  python daemon_wrapper.py --start
  python daemon_wrapper.py --stop
  python daemon_wrapper.py --status
"""
from __future__ import annotations
import os, sys, subprocess, platform
from pathlib import Path

JARVIS_DIR  = Path(__file__).parent.absolute()
LOGS_DIR    = JARVIS_DIR / "logs"


def install_windows_service() -> str:
    nssm = Path("C:/nssm/nssm.exe")
    if not nssm.exists():
        return (
            "NSSM not found.\n"
            "1. Download: https://nssm.cc/download\n"
            "2. Extract nssm.exe to C:\\nssm\\nssm.exe\n"
            "3. Re-run: python daemon_wrapper.py --install"
        )
    LOGS_DIR.mkdir(exist_ok=True)
    script = JARVIS_DIR / "jarvis_main.py"
    steps = [
        [str(nssm), "install",  "JARVIS", sys.executable, str(script)],
        [str(nssm), "set", "JARVIS", "AppDirectory",    str(JARVIS_DIR)],
        [str(nssm), "set", "JARVIS", "DisplayName",     "J.A.R.V.I.S AI Agent"],
        [str(nssm), "set", "JARVIS", "Description",     "Autonomous AI Agent for Dew"],
        [str(nssm), "set", "JARVIS", "Start",           "SERVICE_AUTO_START"],
        [str(nssm), "set", "JARVIS", "AppRestartDelay", "3000"],
        [str(nssm), "set", "JARVIS", "AppStdout",       str(LOGS_DIR / "service_stdout.log")],
        [str(nssm), "set", "JARVIS", "AppStderr",       str(LOGS_DIR / "service_stderr.log")],
    ]
    for cmd in steps:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode not in (0, 5):
            return f"NSSM error at {cmd[2]}: {r.stderr.strip()}"
    return "JARVIS installed as Windows service.\nStart: nssm start JARVIS"


def install_linux_service() -> str:
    LOGS_DIR.mkdir(exist_ok=True)
    unit = f"""[Unit]
Description=J.A.R.V.I.S Autonomous AI Agent
After=network.target

[Service]
Type=simple
User={os.getenv("USER", "root")}
WorkingDirectory={JARVIS_DIR}
ExecStart={sys.executable} {JARVIS_DIR / "jarvis_main.py"}
Restart=always
RestartSec=3
StandardOutput=append:{LOGS_DIR}/service.log
StandardError=append:{LOGS_DIR}/service_error.log
EnvironmentFile={JARVIS_DIR}/.env

[Install]
WantedBy=multi-user.target
"""
    service_path = Path("/etc/systemd/system/jarvis.service")
    try:
        service_path.write_text(unit)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", "jarvis"], check=True)
        return "JARVIS systemd service installed.\nStart: sudo systemctl start jarvis"
    except PermissionError:
        local = JARVIS_DIR / "jarvis.service"
        local.write_text(unit)
        return (
            f"Saved to {local}\n"
            "Copy to /etc/systemd/system/ then:\n"
            "  sudo systemctl daemon-reload && sudo systemctl enable jarvis\n"
            "  sudo systemctl start jarvis"
        )


def install_service() -> str:
    return (install_windows_service() if platform.system() == "Windows"
            else install_linux_service())


def start_service() -> str:
    if platform.system() == "Windows":
        r = subprocess.run(["nssm", "start", "JARVIS"], capture_output=True, text=True)
        return r.stdout.strip() or r.stderr.strip()
    r = subprocess.run(["systemctl", "start", "jarvis"], capture_output=True, text=True)
    return "Started." if r.returncode == 0 else r.stderr.strip()


def stop_service() -> str:
    if platform.system() == "Windows":
        r = subprocess.run(["nssm", "stop", "JARVIS"], capture_output=True, text=True)
        return r.stdout.strip() or r.stderr.strip()
    r = subprocess.run(["systemctl", "stop", "jarvis"], capture_output=True, text=True)
    return "Stopped." if r.returncode == 0 else r.stderr.strip()


def service_status() -> str:
    if platform.system() == "Windows":
        r = subprocess.run(["nssm", "status", "JARVIS"], capture_output=True, text=True)
        return r.stdout.strip() or "NSSM not available."
    r = subprocess.run(["systemctl", "is-active", "jarvis"], capture_output=True, text=True)
    return r.stdout.strip()


if __name__ == "__main__":
    for flag, fn in [("--install", install_service), ("--start", start_service),
                     ("--stop", stop_service), ("--status", service_status)]:
        if flag in sys.argv:
            print(fn()); break
    else:
        print("Usage: python daemon_wrapper.py --install|--start|--stop|--status")
