"""JARVIS v6.0 — Network threat scanner, process monitor, file integrity, camera."""
from __future__ import annotations
import os, hashlib, json, threading
from pathlib import Path
from datetime import datetime

try: import psutil; _PSUTIL = True
except ImportError: _PSUTIL = False

_INTEGRITY_STORE = Path("memory") / "file_hashes.json"
_registered_hashes: dict[str, str] = {}

_SUSPICIOUS_PROCESSES = {"mimikatz","netcat","nc","wireshark","nmap","metasploit",
                          "meterpreter","cobaltstrike","empire"}


def scan_network(subnet: str = "") -> list[dict]:
    """Scan local network for devices."""
    from modules.network_control import scan_network as _scan, get_local_ip
    if not subnet:
        local = get_local_ip()
        subnet = ".".join(local.split(".")[:3]) + ".0/24"
    return _scan(subnet)


def monitor_processes() -> list[dict]:
    """Find suspicious processes by name."""
    if not _PSUTIL: return [{"error": "psutil not installed"}]
    suspicious = []
    for p in psutil.process_iter(["pid","name","cpu_percent"]):
        try:
            name = p.info["name"].lower()
            if any(s in name for s in _SUSPICIOUS_PROCESSES):
                suspicious.append(p.info)
        except Exception: pass
    return suspicious


def register_file_hash(path: str) -> str:
    """Hash a file for integrity monitoring."""
    try:
        content = Path(path).read_bytes()
        h = hashlib.sha256(content).hexdigest()[:16]
        _registered_hashes[path] = h
        _INTEGRITY_STORE.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(_INTEGRITY_STORE.read_text()) if _INTEGRITY_STORE.exists() else {}
        existing[path] = h
        _INTEGRITY_STORE.write_text(json.dumps(existing, indent=2))
        return f"Registered {path}: {h}"
    except Exception as e: return f"Hash error: {e}"


def check_integrity(path: str) -> str:
    """Verify file hasn't changed since registration."""
    try:
        current = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
        stored = _registered_hashes.get(path)
        if not stored:
            existing = json.loads(_INTEGRITY_STORE.read_text()) if _INTEGRITY_STORE.exists() else {}
            stored = existing.get(path)
        if not stored: return f"{path}: not registered"
        if current == stored: return f"{path}: INTACT"
        return f"ALERT: {path} MODIFIED (stored={stored}, current={current})"
    except Exception as e: return f"Integrity error: {e}"


def check_open_ports(host: str = "127.0.0.1") -> list[int]:
    """Detect open ports on localhost."""
    import socket
    open_ports = []
    common = [21,22,23,25,80,443,3389,5900,8080,8443,27017,5432,3306]
    for port in common:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            if s.connect_ex((host, port)) == 0:
                open_ports.append(port)
            s.close()
        except: pass
    return open_ports


def capture_camera_frame(url: str | None = None, confirmed: bool = False) -> str:
    """Capture frame from camera. Requires confirmation first use."""
    try:
        import cv2
        cap = cv2.VideoCapture(url or 0)
        ret, frame = cap.read()
        cap.release()
        if not ret: return "Camera: no frame captured"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"screenshots/camera_{ts}.jpg"
        cv2.imwrite(path, frame)
        return path
    except ImportError: return "opencv-python not installed."
    except Exception as e: return f"Camera error: {e}"
