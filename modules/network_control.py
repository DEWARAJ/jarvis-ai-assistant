"""JARVIS v6.0 — Network: scan, ping, SSH, VPN, connectivity."""
from __future__ import annotations
import os, socket, subprocess

try: import requests; _REQUESTS = True
except ImportError: _REQUESTS = False

try: import paramiko; _PARAMIKO = True
except ImportError: _PARAMIKO = False

try: import nmap; _NMAP = True
except ImportError: _NMAP = False


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except: return "127.0.0.1"


def get_public_ip() -> str:
    if not _REQUESTS: return "requests not installed"
    try: return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception as e: return f"Error: {e}"


def ping(host: str, count: int = 3) -> str:
    try:
        r = subprocess.run(["ping","-n" if os.name=="nt" else "-c",
                            str(count), host],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e: return f"Ping error: {e}"


def check_port(host: str, port: int) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        r = s.connect_ex((host, port))
        s.close()
        return r == 0
    except: return False


def scan_network(subnet: str = "", timeout: float = 2) -> list[dict]:
    if not _NMAP: return [{"error": "python-nmap not installed"}]
    if not subnet:
        local = get_local_ip()
        subnet = ".".join(local.split(".")[:3]) + ".0/24"
    try:
        nm = nmap.PortScanner()
        nm.scan(hosts=subnet, arguments="-sn", timeout=30)
        return [{"host": h, "status": nm[h]["status"]["state"],
                 "hostname": nm[h].hostname()}
                for h in nm.all_hosts()]
    except Exception as e: return [{"error": str(e)}]


def ssh_command(host: str, username: str, command: str,
                key_path: str | None = None, confirmed: bool = False) -> str:
    if not _PARAMIKO: return "paramiko not installed."
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kp = key_path or os.path.expanduser("~/.ssh/id_rsa")
        client.connect(host, username=username, key_filename=kp, timeout=10)
        _, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        client.close()
        return out or err or "(no output)"
    except Exception as e: return f"SSH error: {e}"


def check_internet() -> bool:
    if _REQUESTS:
        try: requests.get("https://8.8.8.8", timeout=3); return True
        except: pass
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8",53))
        return True
    except: return False


def get_network_interfaces() -> list[dict]:
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        return [{"interface": iface, "ip": a.address}
                for iface, addr_list in addrs.items()
                for a in addr_list if a.family == socket.AF_INET]
    except ImportError: return [{"error": "psutil not installed"}]
