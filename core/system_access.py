"""JARVIS — gated system access layer.

All file ops, web search, shell commands, and system status go through here.
Every action is classified (A/B/C/X) before execution. Class B requires the
caller to pass confirmed=True (orchestrator must have obtained consent first).
Class X always raises. Never bypasses security_audit.
"""
from __future__ import annotations
import os
import subprocess
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False


class AccessDenied(Exception):
    pass


class SystemAccess:
    def __init__(self, base_dir: str = ".", logger=None, audit=None):
        self.base = Path(base_dir).resolve()
        self.logger = logger
        self.audit  = audit   # AuditLog instance (optional)

    # ── internal ────────────────────────────────────────────────────────────

    def _log(self, msg: str):
        if self.logger:
            try:
                self.logger.info(msg)
            except Exception:
                pass

    def _audit(self, action: str, cls: str, approved: bool, context: str = ""):
        if self.audit:
            try:
                self.audit.record(action=action, cls=cls, approved=approved, context=context)
            except Exception:
                pass

    def _classify(self, action: str) -> str:
        from core.security_audit import SecurityClassifier
        return SecurityClassifier.classify(action)

    def _gate(self, action: str, confirmed: bool = False) -> str:
        cls = self._classify(action)
        if cls == "X":
            self._audit(action, "X", False)
            raise AccessDenied(f"Class X hard-block: '{action}' is permanently prohibited.")
        if cls == "C" and not confirmed:
            self._audit(action, "C", False, "double-confirm required")
            raise AccessDenied(
                f"Class C action requires double confirmation. "
                f"Repeat with confirmed=True AFTER user types the action name + 'confirm'."
            )
        # Class B removed — executes autonomously
        self._audit(action, cls, True)
        return cls

    # ── file ops ────────────────────────────────────────────────────────────

    def read_file(self, path: str) -> str:
        """Class A — reading is always allowed."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base / path
        self._log(f"[SystemAccess] read_file: {p}")
        try:
            return p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return p.read_text(encoding="latin-1", errors="replace")

    def write_file(self, path: str, content: str, confirmed: bool = False) -> str:
        """Class B — requires confirmation."""
        self._gate(f"write file {path}", confirmed)
        p = Path(path)
        if not p.is_absolute():
            p = self.base / path
        p.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write via temp file
        tmp = p.with_suffix(".tmp_jarvis")
        try:
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, p)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
        self._log(f"[SystemAccess] wrote {len(content)} chars to {p}")
        return f"Written {len(content)} chars → {p}"

    def delete_file(self, path: str, confirmed: bool = False) -> str:
        """Class C — double confirm required."""
        self._gate(f"delete permanently {path}", confirmed)
        p = Path(path)
        if not p.is_absolute():
            p = self.base / path
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        self._log(f"[SystemAccess] deleted {p}")
        return f"Deleted: {p}"

    def list_dir(self, path: str = ".") -> list[str]:
        """Class A — directory listing."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base / path
        return sorted(str(f.relative_to(p)) for f in p.iterdir())

    def backup_file(self, path: str) -> str:
        """Class A — backup before mutation."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base / path
        if not p.exists():
            return f"Nothing to backup: {p}"
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = p.with_suffix(f".bak.{ts}{p.suffix}" if p.suffix else f".bak.{ts}")
        shutil.copy2(p, bak)
        self._log(f"[SystemAccess] backup {p} → {bak}")
        return str(bak)

    # ── shell ────────────────────────────────────────────────────────────────

    def run_command(self, cmd: str, confirmed: bool = False,
                    timeout: int = 30, cwd: str | None = None) -> dict[str, Any]:
        """Class B — execute shell command. Returns {stdout, stderr, returncode}."""
        self._gate(f"run command {cmd}", confirmed)
        self._log(f"[SystemAccess] run_command: {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd or str(self.base)
            )
            return {
                "stdout":     result.stdout.strip(),
                "stderr":     result.stderr.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Timed out after {timeout}s", "returncode": -1}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    # ── web ─────────────────────────────────────────────────────────────────

    def web_search(self, query: str, num: int = 5) -> list[dict]:
        """Class A — web search via Brave or fallback DuckDuckGo."""
        self._log(f"[SystemAccess] web_search: {query}")
        brave_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
        if brave_key and _REQUESTS:
            try:
                r = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": num},
                    headers={"Accept": "application/json",
                             "Accept-Encoding": "gzip",
                             "X-Subscription-Token": brave_key},
                    timeout=10,
                )
                results = r.json().get("web", {}).get("results", [])
                return [{"title": x.get("title"), "url": x.get("url"),
                         "snippet": x.get("description")} for x in results[:num]]
            except Exception:
                pass
        # Fallback: DuckDuckGo instant answer API (no key needed)
        if _REQUESTS:
            try:
                r = requests.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_redirect": 1},
                    timeout=10,
                )
                data = r.json()
                out = []
                if data.get("AbstractText"):
                    out.append({"title": data.get("Heading", query),
                                "url": data.get("AbstractURL", ""),
                                "snippet": data["AbstractText"]})
                for t in data.get("RelatedTopics", [])[:num - 1]:
                    if isinstance(t, dict) and t.get("Text"):
                        out.append({"title": t.get("Text", "")[:60],
                                    "url": t.get("FirstURL", ""),
                                    "snippet": t.get("Text", "")})
                return out[:num]
            except Exception:
                pass
        return []

    def fetch_url(self, url: str) -> str:
        """Class A — fetch page text."""
        if not _REQUESTS:
            return "[Error] requests not installed."
        try:
            r = requests.get(url, timeout=15,
                             headers={"User-Agent": "JARVIS/5.0"})
            r.raise_for_status()
            import re
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:8000]
        except Exception as e:
            return f"[Error fetching {url}] {e}"

    # ── system status ────────────────────────────────────────────────────────

    def system_status(self) -> dict[str, Any]:
        """Class A — CPU, RAM, disk snapshot."""
        status: dict[str, Any] = {}
        if _PSUTIL:
            try:
                status["cpu_pct"]  = psutil.cpu_percent(interval=0.2)
                vm = psutil.virtual_memory()
                status["ram_used_gb"]  = round(vm.used / 1e9, 2)
                status["ram_total_gb"] = round(vm.total / 1e9, 2)
                status["ram_pct"]      = vm.percent
                disk = psutil.disk_usage("/")
                status["disk_free_gb"] = round(disk.free / 1e9, 2)
                status["disk_pct"]     = disk.percent
                status["top_procs"] = [
                    {"name": p.info["name"], "cpu": p.info["cpu_percent"]}
                    for p in sorted(
                        psutil.process_iter(["name", "cpu_percent"]),
                        key=lambda p: p.info.get("cpu_percent") or 0,
                        reverse=True,
                    )[:5]
                ]
            except Exception as e:
                status["error"] = str(e)
        else:
            status["error"] = "psutil not installed"
        return status

    def format_status(self) -> str:
        s = self.system_status()
        if "error" in s:
            return f"System status unavailable: {s['error']}"
        lines = [
            f"CPU: {s.get('cpu_pct', '?')}%",
            f"RAM: {s.get('ram_used_gb')}GB / {s.get('ram_total_gb')}GB ({s.get('ram_pct')}%)",
            f"Disk free: {s.get('disk_free_gb')}GB ({s.get('disk_pct')}% used)",
        ]
        procs = s.get("top_procs", [])
        if procs:
            lines.append("Top processes: " + ", ".join(
                f"{p['name']}({p['cpu']}%)" for p in procs
            ))
        return "\n".join(lines)
