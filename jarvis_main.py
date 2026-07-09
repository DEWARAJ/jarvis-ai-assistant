"""JARVIS v7.0 — Main entry point.   [DEPRECATED — use main.py]

DEPRECATED: the canonical entry point is main.py, which launches
core/orchestrator.py (the real brain powering the dashboard, agents, and tools).
This standalone JARVIS class is kept for reference only. Do not run it for normal use.
See README_ENTRYPOINT.md.


Threaded queue architecture:
  Thread 1 _keyboard_thread : ONLY place input() is called
  Thread 2 _voice_thread    : wake-word STT listener
  Thread 3 _tts_thread      : edge-tts / pyttsx3 TTS consumer
  Thread 4 _monitor_thread  : psutil system alerts every 30s
  Thread 5 local_api        : HTTP server on port 7799
  Main loop                 : drains alert_queue, fabric results, input_queue

v7.0 additions:
  internet_layer  — live search auto-injected before every Claude call
  tool_engine     — Anthropic tool_use ReAct loop
  agent_fabric    — parallel sub-agent spawning
  streaming_engine — token-by-token streaming to TTS
  hermes_bridge   — universal Hermes agent connector
  daemon_wrapper  — Windows/Linux service installer
  local_api       — HTTP API port 7799

Commands: /exit /status /memory /sysinfo /fullpower /think /ooda /mission
          /adapt /rollback /health /trade /voice /screenshot /search
          /hermes <msg> /agents /spawn <type> <task>
          /daemon install|status /api status
"""
from __future__ import annotations

import os
import sys

# Fix Windows cp1252 encoding — Claude responses contain emoji that cp1252 can't print
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass  # Python < 3.7
import re
import queue
import threading
import time
import json
from datetime import datetime
from pathlib import Path

# ── dotenv ────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── graceful optional imports ─────────────────────────────────────────────────
try:
    import anthropic as _ant; _ANT_OK = True
except ImportError:
    _ant = None; _ANT_OK = False

try:
    import psutil as _psutil; _PSUTIL_OK = True
except ImportError:
    _psutil = None; _PSUTIL_OK = False

# ── root-level modules ────────────────────────────────────────────────────────
try:
    from security import classify_action, SecurityClass, AuditLog
    _SEC_OK = True
except ImportError:
    _SEC_OK = False

try:
    from llm_router import route, complexity_score, health_report
    _ROUTER_OK = True
except ImportError:
    _ROUTER_OK = False

try:
    from voice_pipeline import speak, _clean_for_speech, WAKE_WORDS, VoiceListener
    _VOICE_OK = True
except ImportError:
    _VOICE_OK = False

try:
    from ooda_loop import run_ooda, format_ooda_display
    _OODA_OK = True
except ImportError:
    _OODA_OK = False

try:
    from mission_engine import (create_mission, list_missions, format_mission,
                                 get_active_summary, classify_mission)
    _MISSION_OK = True
except ImportError:
    _MISSION_OK = False

try:
    from adapt_engine import adapt_file, list_backups, rollback
    _ADAPT_OK = True
except ImportError:
    _ADAPT_OK = False

# ── v7.0 optional imports ─────────────────────────────────────────────────────
try:
    from internet_layer import augment_query_with_live_data, live_search, format_search_for_context
    _INTERNET_OK = True
except ImportError:
    _INTERNET_OK = False

try:
    from tool_engine import react_loop, JARVIS_TOOLS
    _REACT_OK = True
except ImportError:
    _REACT_OK = False

try:
    from streaming_engine import stream_response
    _STREAM_OK = True
except ImportError:
    _STREAM_OK = False

try:
    from agent_fabric import get_fabric
    _FABRIC_OK = True
except ImportError:
    _FABRIC_OK = False

try:
    from hermes_bridge import HermesBridge
    _HERMES_OK = True
except ImportError:
    _HERMES_OK = False

try:
    from daemon_wrapper import install_service, service_status
    _DAEMON_OK = True
except ImportError:
    _DAEMON_OK = False

try:
    from local_api import start_api_server
    _API_OK = True
except ImportError:
    _API_OK = False

# ── memory paths ──────────────────────────────────────────────────────────────
_MEM_DIR      = Path("memory")
_EPISODIC     = _MEM_DIR / "episodic.jsonl"
_SEMANTIC     = _MEM_DIR / "semantic.json"
_SESSIONS_DIR = _MEM_DIR / "sessions"
for _p in (_MEM_DIR, _SESSIONS_DIR, _MEM_DIR / "vector_store", _MEM_DIR / "code_backups"):
    _p.mkdir(parents=True, exist_ok=True)

_HISTORY_MAX = 30  # rolling turns kept in context

# ══════════════════════════════════════════════════════════════════════════════

class JARVIS:
    VERSION = "7.0"

    def __init__(self):
        self._stop        = threading.Event()
        self.input_queue  = queue.Queue()
        self.output_queue = queue.Queue()
        self.alert_queue  = queue.Queue()
        self._history: list[dict] = []   # {"role","content"}
        self._audit       = AuditLog() if _SEC_OK else None
        self._session_ts  = datetime.now().isoformat(timespec="seconds")
        self._fullpower   = False
        self._voice_active = False
        self._tts_queue   = queue.Queue()

        # Load semantic memory
        self._semantic: dict = {}
        if _SEMANTIC.exists():
            try:
                self._semantic = json.loads(_SEMANTIC.read_text(encoding="utf-8"))
            except Exception:
                pass

    # ── boot ──────────────────────────────────────────────────────────────────

    def _banner(self) -> None:
        art = (
            "\n"
            "  ╔══════════════════════════════════════════╗\n"
            "  ║   J . A . R . V . I . S   v7.0          ║\n"
            "  ║   GODMODE — Live Internet · ReAct Loop   ║\n"
            "  ║   Multi-Agent · Streaming · Persistent   ║\n"
            "  ╚══════════════════════════════════════════╝\n"
        )
        print(art)
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        active = get_active_summary() if _MISSION_OK else "—"
        print(f"  Active missions : {active}")
        print(f"  Internet search : {'Firecrawl+Brave+Perplexity' if _INTERNET_OK else 'offline'}")
        print(f"  ReAct loop      : {'ON  (' + str(len(JARVIS_TOOLS)) + ' tools)' if _REACT_OK else 'off'}")
        print(f"  Agent fabric    : {'ON' if _FABRIC_OK else 'off'}")
        print(f"  Local API       : {'http://127.0.0.1:7799' if _API_OK else 'off'}")
        print("  Type /help for commands. Say 'Hey JARVIS' for voice.\n")

    # ── threads ───────────────────────────────────────────────────────────────

    def _keyboard_thread(self) -> None:
        while not self._stop.is_set():
            try:
                text = input("\nJARVIS> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.input_queue.put(("keyboard", "/exit"))
                return
            if text:
                self.input_queue.put(("keyboard", text))

    def _voice_thread(self) -> None:
        if not _VOICE_OK:
            return
        listener = VoiceListener()
        if not listener.available:
            return
        self._voice_active = True
        while not self._stop.is_set():
            try:
                text = listener.listen_once(timeout=2.0, phrase_limit=20.0)
                if text:
                    lo = text.lower()
                    matched_wake = next(
                        (w for w in WAKE_WORDS if lo.startswith(w)), None)
                    if matched_wake:
                        cmd = text[len(matched_wake):].strip(" ,.")
                        if cmd:
                            self.input_queue.put(("voice", cmd))
            except Exception:
                time.sleep(1)

    def _tts_thread(self) -> None:
        while not self._stop.is_set():
            try:
                text = self._tts_queue.get(timeout=0.2)
                if _VOICE_OK:
                    speak(text)
            except queue.Empty:
                continue
            except Exception:
                pass

    def _monitor_thread(self) -> None:
        if not _PSUTIL_OK:
            return
        while not self._stop.is_set():
            try:
                cpu  = _psutil.cpu_percent(interval=1)
                ram  = _psutil.virtual_memory().percent
                disk = _psutil.disk_usage("/").percent
                if cpu  >= 90: self.alert_queue.put(f"CPU at {cpu:.0f}%")
                if ram  >= 88: self.alert_queue.put(f"RAM at {ram:.0f}%")
                if disk >= 90: self.alert_queue.put(f"Disk at {disk:.0f}%")
            except Exception:
                pass
            self._stop.wait(timeout=30)

    # ── memory ────────────────────────────────────────────────────────────────

    def _append_episodic(self, role: str, content: str) -> None:
        entry = {"ts": datetime.now().isoformat(timespec="seconds"),
                 "role": role, "summary": content[:300]}
        try:
            with open(_EPISODIC, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _save_semantic(self) -> None:
        tmp = _SEMANTIC.with_suffix(".tmp_jarvis")
        try:
            tmp.write_text(json.dumps(self._semantic, indent=2, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, _SEMANTIC)
        except Exception:
            pass
        finally:
            if tmp.exists():
                try: tmp.unlink()
                except: pass

    def _trim_history(self) -> None:
        if len(self._history) > _HISTORY_MAX * 2:
            self._history = self._history[-_HISTORY_MAX * 2:]

    # ── system prompt ─────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        sem = self._semantic
        projects = sem.get("current_projects", [])
        tasks    = sem.get("unfinished_tasks", [])
        today    = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            f"You are JARVIS v{self.VERSION}, Dew's autonomous AI agent.",
            f"Today: {today}",
            "",
            "Identity laws (Class X — never violate):",
            "  • Never fake trade results or hide losses",
            "  • Never access systems not owned by Dew",
            "  • Never modify your own identity or safety gates",
            "  • Never store secrets outside .env",
            "",
            "Capabilities: OS control, file ops, trading (Alpaca paper/live),",
            "  web search, voice, vision, email, calendar, IoT, databases.",
            "",
            "Memory: episodic, semantic, and 5-tier persistent memory.",
        ]
        if projects:
            lines += ["", "Current projects:"] + [f"  • {p}" for p in projects[:5]]
        if tasks:
            lines += ["", "Unfinished tasks:"] + [f"  • {t}" for t in tasks[:5]]
        lines += [
            "",
            "Security: A=auto B=1confirm C=2confirm X=hardblock.",
            "Show reasoning for Class B/C. Be concise. OODA for complex tasks.",
        ]
        return "\n".join(lines)

    # ── LLM call ──────────────────────────────────────────────────────────────

    def _call_claude(self, text: str) -> str:
        if not _ANT_OK:
            return "[Error] anthropic not installed. pip install anthropic"
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            return "[Error] ANTHROPIC_API_KEY not set in .env"

        # Augment time-sensitive queries with live web data
        augmented = augment_query_with_live_data(text) if _INTERNET_OK else text

        self._history.append({"role": "user", "content": text})
        self._trim_history()

        # Primary path: ReAct tool_use loop
        if _REACT_OK:
            try:
                reply = react_loop(
                    user_message=augmented,
                    system_prompt=self._build_system_prompt(),
                    history=self._history[:-1],  # exclude just-appended user turn
                    verbose=True,
                )
                self._history.append({"role": "assistant", "content": reply})
                self._append_episodic("user", text)
                self._append_episodic("assistant", reply)
                return reply
            except Exception as e:
                print(f"  [REACT fallback] {e}")

        # Secondary path: streaming
        if _STREAM_OK:
            try:
                reply = stream_response(
                    user_message=augmented,
                    system_prompt=self._build_system_prompt(),
                    history=self._history[:-1],
                    tts_queue=self._tts_queue,
                    print_live=True,
                )
                self._history.append({"role": "assistant", "content": reply})
                self._append_episodic("user", text)
                self._append_episodic("assistant", reply)
                return reply
            except Exception as e:
                print(f"  [STREAM fallback] {e}")

        # Final fallback: plain messages.create
        model = route(text) if _ROUTER_OK else "claude-sonnet-4-6"
        try:
            client = _ant.Anthropic(api_key=key)
            r = client.messages.create(
                model=model,
                max_tokens=4096,
                system=self._build_system_prompt(),
                messages=self._history,
            )
            reply = r.content[0].text
        except Exception as e:
            reply = f"[LLM Error] {e}"

        self._history.append({"role": "assistant", "content": reply})
        self._append_episodic("user", text)
        self._append_episodic("assistant", reply)
        return reply

    # ── command router ────────────────────────────────────────────────────────

    def _route(self, text: str) -> str:
        cmd = text.strip()
        lo  = cmd.lower()

        if lo in ("/exit", "/quit", "exit", "quit", "shutdown jarvis"):
            self._stop.set()
            return "Goodbye, Dew. JARVIS shutting down."

        if lo == "/help":
            return (
                "Commands:\n"
                "  /exit          — shut down\n"
                "  /status        — system health + stats\n"
                "  /sysinfo       — CPU/RAM/disk\n"
                "  /memory        — recent episodic memory\n"
                "  /fullpower     — toggle extended mode\n"
                "  /think <text>  — OODA reasoning only\n"
                "  /ooda <text>   — full OODA loop\n"
                "  /mission       — list active missions\n"
                "  /mission new <title> :: <description>\n"
                "  /adapt <file> :: <goal>\n"
                "  /rollback <file>\n"
                "  /health        — module health check\n"
                "  /trade         — trading status\n"
                "  /search <q>    — web search\n"
                "  /screenshot    — screenshot + vision analysis\n"
                "  /voice on|off\n"
            )

        if lo in ("/status", "/status sys", "/sysinfo"):
            if _PSUTIL_OK:
                cpu  = _psutil.cpu_percent(interval=0.5)
                ram  = _psutil.virtual_memory()
                disk = _psutil.disk_usage("/")
                return (
                    f"CPU: {cpu:.0f}%\n"
                    f"RAM: {ram.used/1e9:.1f}GB / {ram.total/1e9:.1f}GB ({ram.percent:.0f}%)\n"
                    f"Disk free: {disk.free/1e9:.1f}GB ({disk.percent:.0f}% used)\n"
                    f"Voice: {'active' if self._voice_active else 'off'}\n"
                    f"Fullpower: {self._fullpower}\n"
                    f"History: {len(self._history)} turns"
                )
            return "psutil not installed — pip install psutil"

        if lo.startswith("/memory"):
            if not _EPISODIC.exists():
                return "No episodic memory yet."
            lines = []
            try:
                with open(_EPISODIC, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            e = json.loads(line)
                            lines.append(f"[{e.get('ts','')}] {e.get('role','')}: {e.get('summary','')}")
            except Exception as e:
                return f"Memory error: {e}"
            return "\n".join(lines[-20:]) if lines else "Memory empty."

        if lo == "/fullpower":
            self._fullpower = not self._fullpower
            return f"Fullpower: {'ENABLED' if self._fullpower else 'disabled'}"

        if lo.startswith("/think ") or lo.startswith("/ooda "):
            if not _OODA_OK:
                return "ooda_loop.py not loaded."
            q = cmd.split(None, 1)[1] if len(cmd.split(None, 1)) > 1 else cmd
            result = run_ooda(q, self._history)
            return format_ooda_display(result)

        if lo.startswith("/mission"):
            if not _MISSION_OK:
                return "mission_engine.py not loaded."
            parts = cmd.split(None, 1)
            if len(parts) == 1 or parts[1].strip() == "":
                return get_active_summary()
            sub = parts[1].strip()
            if sub.lower().startswith("new "):
                rest = sub[4:].strip()
                if "::" in rest:
                    title, desc = rest.split("::", 1)
                else:
                    title = rest; desc = rest
                m = create_mission(title.strip(), desc.strip())
                return format_mission(m)
            return get_active_summary()

        if lo.startswith("/adapt "):
            if not _ADAPT_OK:
                return "adapt_engine.py not loaded."
            rest = cmd[7:].strip()
            if "::" in rest:
                file_path, goal = rest.split("::", 1)
                return adapt_file(file_path.strip(), goal.strip())
            return "Usage: /adapt <file> :: <goal>"

        if lo.startswith("/rollback "):
            if not _ADAPT_OK:
                return "adapt_engine.py not loaded."
            return rollback(cmd[10:].strip(), confirmed=False)

        if lo == "/health":
            lines = [f"JARVIS v{self.VERSION}:"]
            for name, ok in [
                ("anthropic",      _ANT_OK),
                ("security",       _SEC_OK),
                ("llm_router",     _ROUTER_OK),
                ("voice_pipeline", _VOICE_OK),
                ("ooda_loop",      _OODA_OK),
                ("mission_engine", _MISSION_OK),
                ("adapt_engine",   _ADAPT_OK),
                ("internet_layer", _INTERNET_OK),
                ("tool_engine",    _REACT_OK),
                ("streaming",      _STREAM_OK),
                ("agent_fabric",   _FABRIC_OK),
                ("hermes_bridge",  _HERMES_OK),
                ("daemon_wrapper", _DAEMON_OK),
                ("local_api",      _API_OK),
            ]:
                lines.append(f"  {name:16}: {'OK' if ok else 'MISSING'}")
            if _REACT_OK:
                lines.append(f"  tools defined  : {len(JARVIS_TOOLS)}")
            if _ROUTER_OK:
                lines.append(health_report())
            return "\n".join(lines)

        if lo.startswith("/trade"):
            try:
                from modules.trading_module import AlpacaClient
                return AlpacaClient().get_status_report()
            except ImportError:
                return "trading_module not loaded."
            except Exception as e:
                return f"Trade error: {e}"

        if lo == "/screenshot":
            try:
                from modules.gui_automation import take_screenshot_and_analyze
                return take_screenshot_and_analyze("Describe what you see on screen.")
            except ImportError:
                return "gui_automation not loaded."

        if lo.startswith("/voice"):
            parts = lo.split()
            if len(parts) > 1 and parts[1] == "off":
                self._voice_active = False; return "Voice off."
            elif len(parts) > 1 and parts[1] == "on":
                self._voice_active = True; return "Voice on."
            return f"Voice: {'active' if self._voice_active else 'off'}"

        # ── v7.0 commands ─────────────────────────────────────────────────────

        if lo.startswith("/search "):
            query = cmd[8:].strip()
            if _INTERNET_OK:
                data = live_search(query)
                return format_search_for_context(data) or "No results."
            return self._call_claude(f"Search and summarize: {query}")

        if lo == "/hermes status":
            if not _HERMES_OK:
                return "hermes_bridge.py not loaded."
            return HermesBridge().status()

        if lo.startswith("/hermes "):
            if not _HERMES_OK:
                return "hermes_bridge.py not loaded."
            task = cmd[8:].strip()
            def _hermes_async():
                try:
                    result = HermesBridge().send(task, priority="high")
                    self.alert_queue.put(f"[HERMES RESULT]\n{result}")
                except Exception as e:
                    self.alert_queue.put(f"[HERMES ERROR] {e}")

            threading.Thread(target=_hermes_async, daemon=True, name="JARVIS-Hermes").start()
            return f"Hermes on it, sir. Task dispatched async — result will appear when ready.\nTask: {task[:80]}"

        if lo == "/agents":
            if not _FABRIC_OK:
                return "agent_fabric.py not loaded."
            return get_fabric().get_status()

        if lo.startswith("/spawn "):
            if not _FABRIC_OK:
                return "agent_fabric.py not loaded."
            parts = cmd[7:].split(" ", 1)
            if len(parts) < 2:
                return "Usage: /spawn <research|trading|build|monitor|communication> <task>"
            tid = get_fabric().spawn(parts[0].strip(), parts[1].strip())
            return f"Sub-agent spawned: {parts[0]} | ID: {tid}"

        if lo == "/daemon install":
            if not _DAEMON_OK:
                return "daemon_wrapper.py not loaded."
            return install_service()

        if lo == "/daemon status":
            if not _DAEMON_OK:
                return "daemon_wrapper.py not loaded."
            return service_status()

        if lo == "/api status":
            return (f"JARVIS local API: http://127.0.0.1:7799\n"
                    f"  POST /command  GET /status  GET /memory\n"
                    f"  POST /hermes   GET /alerts  GET /health")

        if lo == "/internet status":
            if not _INTERNET_OK:
                return "internet_layer.py not loaded."
            from internet_layer import firecrawl_search, brave_search, perplexity_search
            providers = []
            import os as _os
            if _os.getenv("FIRECRAWL_API_KEY"):  providers.append("firecrawl")
            if _os.getenv("BRAVE_SEARCH_API_KEY"): providers.append("brave")
            if _os.getenv("PERPLEXITY_API_KEY"):  providers.append("perplexity")
            if _os.getenv("TAVILY_API_KEY"):       providers.append("tavily")
            providers.append("duckduckgo")
            return f"Live search providers active: {', '.join(providers)}"

        # Security gate
        if _SEC_OK:
            cls = classify_action(cmd)
            if cls == SecurityClass.X:
                if self._audit: self._audit.record(cmd, "X", False)
                return f"CLASS X HARD BLOCK: '{cmd[:60]}' permanently prohibited."
            if cls == SecurityClass.C:
                if self._audit: self._audit.record(cmd, "C", False, "double-confirm required")
                return f"CLASS C: double confirmation required. Repeat + 'CONFIRM CONFIRM'."
            # Class B removed — actions execute autonomously

        return self._call_claude(cmd)

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._banner()

        for target, name in [
            (self._keyboard_thread, "keyboard"),
            (self._voice_thread,   "voice"),
            (self._tts_thread,     "tts"),
            (self._monitor_thread, "monitor"),
        ]:
            threading.Thread(target=target, daemon=True, name=name).start()

        # Start local HTTP API
        if _API_OK:
            api_port = int(os.getenv("JARVIS_API_PORT", "7799"))
            start_api_server(self.input_queue, port=api_port)

        # Init agent fabric singleton
        if _FABRIC_OK:
            _fabric_instance = get_fabric()

        while not self._stop.is_set():
            # Drain alerts
            while True:
                try:
                    print(f"\n[JARVIS ALERT] {self.alert_queue.get_nowait()}")
                except queue.Empty:
                    break

            # Collect completed sub-agent results
            if _FABRIC_OK:
                for task in get_fabric().collect_results(timeout=0.01):
                    msg = (f"\n[SUB-AGENT {task.agent_type.upper()} COMPLETE | {task.id}]\n"
                           f"{task.result}")
                    print(msg)
                    self._tts_queue.put(f"Sub-agent {task.agent_type} finished.")
                    self._append_episodic("system", f"sub-agent {task.agent_type}: {task.result[:200]}")

            # Get next input
            try:
                source, text = self.input_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if not text.strip():
                continue

            if source == "voice":
                print(f"\nJARVIS> [voice] {text}")

            try:
                response = self._route(text)
            except Exception as e:
                response = f"[Error] {e}"

            if response:
                print(f"\n{response}")
                self._tts_queue.put(response)

        print("\n[JARVIS] Saving session...")
        self._append_episodic("system", f"Session ended {datetime.now().isoformat()}")
        self._save_semantic()
        print("[JARVIS] Goodbye.")


def main() -> None:
    os.chdir(Path(__file__).parent)
    jarvis = JARVIS()
    try:
        jarvis.run()
    except KeyboardInterrupt:
        jarvis._stop.set()
        print("\n[JARVIS] Interrupted.")


if __name__ == "__main__":
    main()
