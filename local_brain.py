"""
local_brain.py  —  JARVIS v10.0  Neural Core (Local Decision Engine).

Routes queries to the cheapest sufficient handler. ~80% of routine queries
(time, calc, open app, system status, list files) never touch the API.

Routes: instant | web_search | hermes | llm
Only complex reasoning / creative / analysis goes to the LLM.
"""
from __future__ import annotations
import os, re, math, subprocess, platform
from datetime import datetime
from pathlib import Path
from typing import Callable
from dataclasses import dataclass

try:
    import psutil; PSUTIL = True
except ImportError:
    PSUTIL = False
try:
    import pyperclip; CLIPBOARD = True
except ImportError:
    CLIPBOARD = False
try:
    from PIL import ImageGrab; SCREENSHOT = True
except ImportError:
    SCREENSHOT = False


# ── LAYER 1: instant action handlers ──────────────────────────────────────────
@dataclass
class InstantAction:
    pattern: re.Pattern
    handler: Callable
    description: str
    security_class: str = "A"


def _time_now(m) -> str:
    now = datetime.now()
    return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}, sir."

def _date_now(m) -> str:
    return datetime.now().strftime("Today is %A, %B %d, %Y, sir.")

def _open_app(m) -> str:
    app = m.group(1).strip()
    app_map = {"notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe",
               "terminal": "cmd.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
               "explorer": "explorer.exe", "chrome": "chrome.exe", "firefox": "firefox.exe",
               "code": "code", "vscode": "code"}
    exe = app_map.get(app.lower(), app)
    try:
        subprocess.Popen(exe, shell=True)
        return f"Opening {app}, sir."
    except Exception as e:
        return f"Cannot open {app}: {e}"

def _list_files(m) -> str:
    directory = (m.group(1).strip() if m.lastindex and m.group(1) else "") or "."
    p = Path(directory)
    if not p.exists():
        return f"Directory not found: {directory}"
    items = sorted(p.iterdir())[:30]
    lines = [f"Contents of {p.absolute()} ({len(items)} shown):"]
    for it in items:
        icon = "DIR " if it.is_dir() else "FILE"
        size = ""
        if it.is_file():
            s = it.stat().st_size
            size = f" ({s:,} B)" if s < 1e6 else f" ({s/1e6:.1f} MB)"
        lines.append(f"  {icon}  {it.name}{size}")
    return "\n".join(lines)

def _system_status(m) -> str:
    if not PSUTIL:
        return "psutil not installed."
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return (f"CPU: {cpu}%\nRAM: {ram.percent}% ({ram.used/1e9:.1f}/{ram.total/1e9:.1f} GB)\n"
            f"Disk: {disk.percent}% ({disk.free/1e9:.1f} GB free)")

def _clipboard_read(m) -> str:
    if not CLIPBOARD:
        return "pyperclip not installed."
    c = pyperclip.paste()
    return f"Clipboard ({len(c)} chars):\n{c[:500]}"

def _screenshot_take(m) -> str:
    if not SCREENSHOT:
        return "Pillow not installed."
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path("screenshots"); path.mkdir(exist_ok=True)
    fp = path / f"ss_{ts}.png"
    img = ImageGrab.grab(); img.save(str(fp))
    return f"Screenshot saved: {fp} ({img.size[0]}x{img.size[1]})"

def _calculate(m) -> str:
    raw = m.group(1).strip()
    if not all(c in "0123456789.+-*/()%^ " for c in raw):
        return "Cannot evaluate: unsafe characters."
    try:
        result = eval(raw.replace("^", "**"), {"__builtins__": {}}, {"math": math})
        if isinstance(result, float):
            result = round(result, 6)
        return f"{raw} = {result}"
    except Exception as e:
        return f"Calculation error: {e}"

def _get_ip(m) -> str:
    try:
        import requests
        return f"Your public IP: {requests.get('https://api.ipify.org', timeout=5).text}"
    except Exception as e:
        return f"Cannot get IP: {e}"

def _processes(m) -> str:
    if not PSUTIL:
        return "psutil not installed."
    filt = (m.group(1).strip().lower() if m.lastindex and m.group(1) else "")
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            i = p.info
            if filt and filt not in (i["name"] or "").lower():
                continue
            procs.append(i)
        except Exception:
            pass
    procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
    lines = [f"{'PID':>7} {'CPU':>5} {'MEM':>5}  NAME"]
    for p in procs[:20]:
        lines.append(f"{p['pid']:>7} {p.get('cpu_percent',0):>4.1f}% {p.get('memory_percent',0):>4.1f}%  {p['name']}")
    return "\n".join(lines)

def _ping(m) -> str:
    host = m.group(1).strip()
    flag = "-n" if platform.system() == "Windows" else "-c"
    try:
        r = subprocess.run(["ping", flag, "4", host], capture_output=True, text=True, timeout=10)
        return (r.stdout or "")[-500:]
    except Exception as e:
        return f"Ping failed: {e}"

def _uptime(m) -> str:
    if not PSUTIL:
        return "psutil not installed."
    boot = datetime.fromtimestamp(psutil.boot_time())
    d = datetime.now() - boot
    return f"System uptime: {int(d.total_seconds()//3600)}h {int((d.total_seconds()%3600)//60)}m"

def _pwd(m) -> str:
    return f"Current directory: {os.getcwd()}"


INSTANT_ACTIONS: list[InstantAction] = [
    InstantAction(re.compile(r"(?:what\s+time|what(?:'s| is)\s+the\s+time|current\s+time|the\s+time|time)\b.*", re.I), _time_now, "Get time"),
    InstantAction(re.compile(r"(?:what\s+(?:day|date)|what(?:'s| is)\s+(?:the\s+)?date|today'?s?\s+date|date)\b.*", re.I), _date_now, "Get date"),
    InstantAction(re.compile(r"open (.+)", re.I), _open_app, "Open app"),
    InstantAction(re.compile(r"(?:list|show|ls)(?: files?| dir(?:ectory)?)?(?: in| at)? ?(.*)", re.I), _list_files, "List files"),
    InstantAction(re.compile(r"(?:system|sys) ?(?:status|info|stats?).*", re.I), _system_status, "System status"),
    InstantAction(re.compile(r"(?:what(?:'s| is) (?:on |in )?(?:my )?)?clipboard.*|paste", re.I), _clipboard_read, "Read clipboard"),
    InstantAction(re.compile(r"(?:take )?screenshot.*|capture screen.*", re.I), _screenshot_take, "Screenshot"),
    InstantAction(re.compile(r"(?:calculate|calc|compute|eval(?:uate)?) (.+)", re.I), _calculate, "Calculate"),
    InstantAction(re.compile(r"(?:what(?:'s| is) )?(?:my )?(?:public )?ip\b.*", re.I), _get_ip, "Public IP"),
    InstantAction(re.compile(r"(?:list |show |top )?(?:processes|procs)\b ?(.*)", re.I), _processes, "Processes"),
    InstantAction(re.compile(r"ping (.+)", re.I), _ping, "Ping"),
    InstantAction(re.compile(r"uptime.*|how long .*(?:system|computer|pc).*", re.I), _uptime, "Uptime"),
    InstantAction(re.compile(r"(?:pwd|where am i|current dir(?:ectory)?)\b.*", re.I), _pwd, "Current dir"),
]


# ── LAYER 2: complexity scoring + routing ─────────────────────────────────────
COMPLEXITY_WORDS = {
    "explain": 2, "analyze": 3, "build": 3, "create": 3, "write code": 3, "design": 3,
    "architecture": 3, "strategy": 3, "plan": 2, "compare": 2, "research": 2, "debug": 2,
    "fix": 2, "optimize": 2, "refactor": 3, "why": 2, "how does": 2, "what if": 2,
    "should i": 2, "recommend": 2, "mission": 3, "deploy": 3, "trade": 3, "invest": 3,
    "portfolio": 2, "review": 2, "critique": 2, "improve": 2, "teach": 2, "summarize": 2,
}
WEB_ONLY_PATTERNS = [
    re.compile(r"(?:what is|who is|where is|when (?:is|was|did)) .{5,}", re.I),
    re.compile(r"(?:latest|current|recent|today'?s?) (?:news|price|score|weather)", re.I),
    re.compile(r"(?:search|google|look up|find) (.+)", re.I),
]
HERMES_PATTERNS = [re.compile(r"(?:hermes|ask hermes|tell hermes|delegate to hermes)\b(.*)", re.I)]


def score_complexity(query: str) -> int:
    q = query.lower()
    score = sum(pts for w, pts in COMPLEXITY_WORDS.items() if w in q)
    if len(query) > 100: score += 1
    if len(query) > 200: score += 1
    if "and" in q and ("?" in q or any(w in q for w in ["also", "then", "after"])):
        score += 2
    return min(score, 10)


class BrainDecision:
    def __init__(self, route: str, response: str = "", handler: str = "",
                 confidence: float = 1.0, reason: str = ""):
        self.route = route          # instant | web_search | hermes | llm
        self.response = response
        self.handler = handler
        self.confidence = confidence
        self.reason = reason


def think(query: str) -> BrainDecision:
    q = (query or "").strip()
    if not q:
        return BrainDecision("instant", "I need something to work with, sir.", "empty")

    # Layer 1: instant actions (only when the pattern covers the whole query)
    for action in INSTANT_ACTIONS:
        m = action.pattern.fullmatch(q)
        if m:
            try:
                return BrainDecision("instant", action.handler(m), action.description,
                                     1.0, f"instant: {action.description}")
            except Exception:
                pass  # fall through to LLM

    # Layer 2: explicit Hermes delegation
    for pat in HERMES_PATTERNS:
        m = pat.search(q)
        if m:
            payload = (m.group(1).strip() if m.lastindex and m.group(1).strip() else q)
            return BrainDecision("hermes", payload, "hermes_bridge", 0.9, "explicit Hermes")

    # Layer 2: web-only factual lookups (low complexity)
    for pat in WEB_ONLY_PATTERNS:
        if pat.search(q) and score_complexity(q) < 4:
            return BrainDecision("web_search", q, "internet_layer", 0.8, "factual lookup")

    # Layer 3: needs the LLM
    c = score_complexity(q)
    return BrainDecision("llm", q, f"claude_{'sonnet' if c >= 6 else 'haiku'}",
                         0.7, f"reasoning (complexity {c}/10)")


def get_brain_status() -> dict:
    return {"instant_patterns": len(INSTANT_ACTIONS),
            "complexity_words": len(COMPLEXITY_WORDS),
            "web_patterns": len(WEB_ONLY_PATTERNS),
            "hermes_patterns": len(HERMES_PATTERNS)}
