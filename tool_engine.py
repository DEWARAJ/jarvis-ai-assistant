"""
tool_engine.py  —  JARVIS v7.0
Anthropic tool_use ReAct loop.

Claude calls tools with structured parameters.
JARVIS executes -> returns result -> Claude reasons -> next tool or final answer.
Replaces fragile text-parsing with true structured execution.
"""
from __future__ import annotations
import os, json, subprocess, io, contextlib
from pathlib import Path

try:
    import anthropic as _ant; _ANT_OK = True
except ImportError:
    _ant = None; _ANT_OK = False

try:
    # override=True so .env key always wins over any stale shell ANTHROPIC_API_KEY
    from dotenv import load_dotenv; load_dotenv(override=True)
except ImportError:
    pass


def _resolve_anthropic_key() -> str:
    """
    Resolve ANTHROPIC_API_KEY robustly. The .env FILE is the source of truth —
    a stale/invalid ANTHROPIC_API_KEY in the shell environment (e.g. Claude Code's
    session token) must NEVER win. Read the file first; fall back to os.environ only
    if the file has no key.
    """
    from pathlib import Path as _P
    for env_path in (_P(".env"), _P(__file__).resolve().parent / ".env"):
        try:
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except OSError:
            pass
    return os.getenv("ANTHROPIC_API_KEY", "")

# ── Tool schemas ──────────────────────────────────────────────────────────────
JARVIS_TOOLS: list[dict] = [
    {
        "name": "web_search",
        "description": (
            "Search the live internet for current information, news, prices, facts. "
            "Use for any query needing up-to-date data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "count": {"type": "integer", "description": "Number of results", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "scrape_url",
        "description": "Deep-scrape a URL via Firecrawl and return full page content as markdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "read_file",
        "description": "Read contents of a local file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a local file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "Execute a shell command. Returns stdout, stderr, returncode.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["command"],
        },
    },
    {
        "name": "run_python",
        "description": "Execute Python code and return captured stdout.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "get_system_info",
        "description": "Get CPU, RAM, disk usage and top processes.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_message_to_hermes",
        "description": "Send a task or message to the Hermes agent for processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "default": "medium",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "get_trading_status",
        "description": "Get Alpaca account, open positions, and today's P&L.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "memory_search",
        "description": "Search JARVIS episodic and semantic memory.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "spawn_sub_agent",
        "description": "Spawn a specialized sub-agent for a parallel task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["research", "trading", "build", "monitor", "communication"],
                },
                "task": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "default": "medium",
                },
            },
            "required": ["agent_type", "task"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot and return the file path.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_notification",
        "description": "Send a desktop notification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["title", "message"],
        },
    },
]


# ── Tool executors ────────────────────────────────────────────────────────────
def _execute_tool(name: str, inp: dict) -> str:
    try:
        if name == "web_search":
            from internet_layer import live_search, format_search_for_context
            return format_search_for_context(
                live_search(inp["query"], inp.get("count", 5))
            )

        if name == "scrape_url":
            from internet_layer import firecrawl_scrape
            return firecrawl_scrape(inp["url"])

        if name == "read_file":
            p = Path(inp["path"])
            if not p.exists():
                return f"File not found: {inp['path']}"
            return p.read_text(encoding="utf-8", errors="replace")[:6000]

        if name == "write_file":
            p = Path(inp["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(inp["content"], encoding="utf-8")
            return f"Written {len(inp['content'])} chars to {p}"

        if name == "run_command":
            r = subprocess.run(
                inp["command"], shell=True, capture_output=True,
                text=True, timeout=inp.get("timeout", 30),
            )
            out = (r.stdout or "")[-3000:]
            err = (r.stderr or "")[-500:]
            return (f"Exit: {r.returncode}\nOutput:\n{out}"
                    + (f"\nErrors:\n{err}" if err else ""))

        if name == "run_python":
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    exec(inp["code"], {})  # noqa: S102
                return buf.getvalue() or "(no output)"
            except Exception as e:
                return f"Exec error: {type(e).__name__}: {e}"

        if name == "get_system_info":
            try:
                import psutil
                cpu  = psutil.cpu_percent(interval=0.5)
                ram  = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                top  = sorted(
                    psutil.process_iter(["name", "cpu_percent"]),
                    key=lambda p: p.info.get("cpu_percent") or 0,
                    reverse=True,
                )[:5]
                return (f"CPU: {cpu}%\n"
                        f"RAM: {ram.percent}% ({ram.used/1e9:.1f}/{ram.total/1e9:.1f}GB)\n"
                        f"Disk: {disk.percent}% ({disk.free/1e9:.1f}GB free)\n"
                        f"Top: {[p.info['name'] for p in top]}")
            except ImportError:
                return "psutil not installed."

        if name == "send_message_to_hermes":
            from hermes_bridge import HermesBridge
            return f"Hermes: {HermesBridge().send(inp['message'], inp.get('priority', 'medium'))}"

        if name == "get_trading_status":
            try:
                from modules.trading_module import AlpacaClient
                return AlpacaClient().get_status_report()
            except Exception as e:
                return f"Trading error: {e}"

        if name == "memory_search":
            ep  = Path("memory/episodic.jsonl")
            q   = inp["query"].lower()
            if not ep.exists():
                return "No episodic memory."
            matches = []
            with ep.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and q in line.lower():
                        try:
                            e = json.loads(line)
                            matches.append(
                                f"[{e.get('ts','')}] {e.get('role','')}: {e.get('summary','')}"
                            )
                        except Exception:
                            pass
            return "\n".join(matches[-10:]) if matches else f"No memory for '{q}'"

        if name == "spawn_sub_agent":
            from agent_fabric import get_fabric
            tid = get_fabric().spawn(
                inp["agent_type"], inp["task"], inp.get("priority", "medium")
            )
            return f"Sub-agent spawned: {inp['agent_type']} | ID: {tid}"

        if name == "take_screenshot":
            try:
                from PIL import ImageGrab
                from datetime import datetime as _dt
                p = Path("screenshots")
                p.mkdir(exist_ok=True)
                fp = p / f"ss_{_dt.now().strftime('%Y%m%d_%H%M%S')}.png"
                ImageGrab.grab().save(str(fp))
                return f"Screenshot: {fp}"
            except Exception as e:
                return f"Screenshot error: {e}"

        if name == "send_notification":
            try:
                from plyer import notification
                notification.notify(
                    title=inp["title"], message=inp["message"], timeout=8
                )
                return f"Notification sent: {inp['title']}"
            except Exception as e:
                return f"Notification error: {e}"

        return f"Unknown tool: {name}"

    except Exception as e:
        return f"Tool error ({name}): {type(e).__name__}: {e}"


# ── ReAct loop ────────────────────────────────────────────────────────────────
def react_loop(
    user_message: str,
    system_prompt: str,
    history: list[dict],
    max_iterations: int = 10,
    verbose: bool = True,
    extra_tools: list[dict] | None = None,
) -> str:
    """
    Reason->Act->Observe loop via Anthropic tool_use API.
    Returns final text response.
    """
    if not _ANT_OK:
        return "[tool_engine] anthropic not installed."
    key = _resolve_anthropic_key()
    if not key:
        return "[tool_engine] ANTHROPIC_API_KEY not set."

    # Headroom proxy: if ANTHROPIC_BASE_URL is set (e.g. http://127.0.0.1:8787), route all
    # Anthropic calls through the local Headroom compression proxy → 60-95% fewer tokens.
    # Unset = direct to Anthropic (default).
    _base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip() or None
    client   = _ant.Anthropic(api_key=key, base_url=_base_url) if _base_url else _ant.Anthropic(api_key=key)
    tools    = JARVIS_TOOLS + (extra_tools or [])
    # Prompt caching: mark the last tool so Anthropic caches the whole tools array,
    # cutting repeat input tokens (~90% cheaper on cache hits within the 5-min TTL).
    tools_cached = ([*tools[:-1], {**tools[-1], "cache_control": {"type": "ephemeral"}}]
                    if tools else tools)
    # Cache the (large) system prompt too — the single biggest repeat-input saving.
    system_cached = [{"type": "text", "text": system_prompt,
                      "cache_control": {"type": "ephemeral"}}]
    messages = list(history) + [{"role": "user", "content": user_message}]

    resp = None
    for _ in range(max_iterations):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_cached,
                tools=tools_cached,
                messages=messages,
            )
        except Exception as e:
            return f"[REACT] API error: {e}"

        # Execute any tool_use blocks present, regardless of stop_reason.
        # (Claude can hit max_tokens mid-tool-call → stop_reason="max_tokens" but
        #  still carries tool_use blocks. Treat those the same as a clean tool_use.)
        tool_blocks = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]

        if tool_blocks:
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in tool_blocks:
                if verbose:
                    print(f"  [REACT] {block.name}({json.dumps(block.input)[:120]})")
                result = _execute_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
            messages.append({"role": "user", "content": results})
            continue

        # No tool calls — this is the final answer (end_turn, max_tokens on text, etc.)
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        if text.strip():
            return text
        break

    if resp is not None:
        texts = [b.text for b in resp.content if hasattr(b, "text")]
        if texts:
            return "\n".join(texts)

    # Loop hit iteration cap while still calling tools — force a final answer.
    # One more call with NO tools: Claude must synthesize everything gathered so far.
    try:
        final = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt + (
                "\n\nIMPORTANT: You have gathered enough information. "
                "Do NOT request more tools. Write your complete final answer NOW "
                "using everything collected above."
            ),
            messages=messages,
        )
        out = "".join(b.text for b in final.content if hasattr(b, "text"))
        if out.strip():
            return out
    except Exception as e:
        return f"[REACT] forced-final error: {e}"
    return "[REACT] Loop ended without final response."
