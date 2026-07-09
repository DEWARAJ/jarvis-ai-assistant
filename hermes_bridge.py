"""
hermes_bridge.py  —  JARVIS v7.0
Universal Hermes Agent Bridge.

Auto-detects connection type from .env. Tries in order:
  http       -> POST to HERMES_URL/message
  module     -> import HERMES_MODULE_PATH and call .run()
  elevenlabs -> text-to-speech via ElevenLabs voice agent
  internal   -> Hermes runs as a real Claude agent via Anthropic API (DEFAULT)
  queue      -> passive blackboard fallback (last resort, no intelligence)

Default when no external Hermes configured: INTERNAL mode.
Hermes gets its own system prompt + full ReAct tool loop (web_search, scrape_url, etc.)

.env keys: HERMES_URL, HERMES_MODULE_PATH, HERMES_API_KEY,
           HERMES_TYPE, HERMES_VOICE_ID, ELEVENLABS_API_KEY
"""
from __future__ import annotations
import os, json, uuid, time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests as _req; _REQ_OK = True
except ImportError:
    _req = None; _REQ_OK = False

try:
    # override=True so .env key always wins over any stale shell ANTHROPIC_API_KEY
    from dotenv import load_dotenv; load_dotenv(override=True)
except ImportError:
    pass

HERMES_LOG = Path("memory/hermes_log.jsonl")
HERMES_LOG.parent.mkdir(exist_ok=True)
BLACKBOARD = Path("memory/shared_blackboard.json")


class HermesBridge:
    def __init__(self):
        self.url         = os.getenv("HERMES_URL", "")
        self.module_path = os.getenv("HERMES_MODULE_PATH", "")
        self.api_key     = os.getenv("HERMES_API_KEY", "")
        self.hermes_type = os.getenv("HERMES_TYPE", "")
        self._module: Optional[object] = None
        self._conn_type = self._detect()

    def _detect(self) -> str:
        # Only honour explicit HERMES_TYPE if it's a real external type
        # "queue" is NOT a valid forced type — it's the last-resort passive fallback
        forced = self.hermes_type.strip().lower()
        if forced and forced not in ("queue", "auto", ""):
            return forced
        # Auto-detect order: http → module → elevenlabs → internal → queue
        if self.url:
            return "http"
        if self.module_path and Path(self.module_path).exists():
            return "module"
        if os.getenv("ELEVENLABS_API_KEY", ""):
            return "elevenlabs"
        # Default: Hermes runs as internal Claude agent
        if os.getenv("ANTHROPIC_API_KEY", ""):
            return "internal"
        return "queue"

    def send(self, message: str, priority: str = "medium", history: list | None = None) -> str:
        msg = {
            "id":                str(uuid.uuid4())[:8],
            "from":              "JARVIS",
            "to":                "HERMES",
            "timestamp":         datetime.now().isoformat(),
            "type":              "task",
            "priority":          priority,
            "content":           message,
            "requires_response": True,
            "timeout_seconds":   600,
            "history":           history or [],
        }
        self._log(msg, "sent")
        dispatch = {
            "http":       self._http,
            "module":     self._module_call,
            "elevenlabs": self._elevenlabs,
            "internal":   self._internal,
            "queue":      self._queue,
        }
        result = dispatch.get(self._conn_type, self._internal)(msg)
        self._log({"response": result}, "received")
        return result

    def _internal(self, msg: dict) -> str:
        """
        Hermes runs as a real Claude agent via ANTHROPIC_API_KEY.
        Gets its own system prompt + full ReAct tool loop.
        This is the default when no external Hermes is configured.
        """
        try:
            from tool_engine import _resolve_anthropic_key
            key = _resolve_anthropic_key()
        except ImportError:
            key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            return "[Hermes] ANTHROPIC_API_KEY not set — cannot run internal agent."

        HERMES_SYSTEM = (
            "You are HERMES, JARVIS's dedicated research and analysis agent. "
            "You are highly capable, thorough, and fast. "
            "Your job: receive tasks from JARVIS and complete them fully. "
            "For research tasks: search multiple sources, synthesise, return dense factual results. "
            "For analysis tasks: reason step by step, surface key insights. "
            "For any task needing current data: use web_search and scrape_url tools. "
            "Always return a complete, actionable result — never say 'I cannot' or time out. "
            "Be concise but complete. Dew depends on your results."
        )

        task_text = msg.get("content", "")
        priority  = msg.get("priority", "medium")
        brain     = msg.get("history", [])  # JARVIS conversation history = Hermes brain context
        print(f"  [HERMES internal] running task (priority={priority}): {task_text[:80]}")
        if brain:
            print(f"  [HERMES internal] brain context: {len(brain)} turns loaded")

        try:
            from tool_engine import react_loop
            result = react_loop(
                user_message=task_text,
                system_prompt=HERMES_SYSTEM,
                history=brain,
                max_iterations=20,
                verbose=True,
            )
            return result
        except ImportError:
            # Fallback: plain Anthropic call without tools
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                r = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=HERMES_SYSTEM,
                    messages=[{"role": "user", "content": task_text}],
                )
                return r.content[0].text
            except Exception as e:
                return f"[Hermes internal error] {e}"
        except Exception as e:
            return f"[Hermes react_loop error] {e}"

    def status(self) -> str:
        return (
            f"Hermes Bridge\n"
            f"  connection: {self._conn_type}\n"
            f"  url:        {self.url or 'not set'}\n"
            f"  module:     {self.module_path or 'not set'}\n"
            f"  api_key:    {'set' if self.api_key else 'not set'}\n"
            f"  log:        {HERMES_LOG} ({'exists' if HERMES_LOG.exists() else 'empty'})"
        )

    def _http(self, msg: dict) -> str:
        if not _REQ_OK:
            return "requests not installed."
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            r = _req.post(f"{self.url}/message", json=msg, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data.get("content", data.get("response", str(data)))
        except Exception as e:
            return f"Hermes HTTP error: {e}"

    def _module_call(self, msg: dict) -> str:
        if self._module is None:
            import importlib.util
            spec = importlib.util.spec_from_file_location("hermes_agent", self.module_path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._module = mod
        try:
            if hasattr(self._module, "run"):
                return str(self._module.run(msg["content"]))  # type: ignore
            if hasattr(self._module, "process"):
                return str(self._module.process(msg))  # type: ignore
            return "Hermes module found but missing run() or process()."
        except Exception as e:
            return f"Hermes module error: {e}"

    def _elevenlabs(self, msg: dict) -> str:
        if not _REQ_OK:
            return "requests not installed."
        key      = os.getenv("ELEVENLABS_API_KEY", "")
        voice_id = os.getenv("HERMES_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        try:
            r = _req.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": key, "Content-Type": "application/json"},
                json={"text": msg["content"], "model_id": "eleven_monolingual_v1",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}},
                timeout=15,
            )
            r.raise_for_status()
            import tempfile, subprocess, sys as _sys
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(r.content)
                tmp = f.name
            if _sys.platform == "win32":
                import os as _os; _os.system(f'start /wait "" "{tmp}"')
            else:
                subprocess.run(["mpg123", tmp], capture_output=True)
            return f"Hermes spoke: {msg['content'][:60]}"
        except Exception as e:
            return f"ElevenLabs error: {e}"

    def _queue(self, msg: dict) -> str:
        BLACKBOARD.parent.mkdir(exist_ok=True)
        try:
            data: dict = {}
            if BLACKBOARD.exists():
                data = json.loads(BLACKBOARD.read_text(encoding="utf-8"))
            data.setdefault("hermes_inbox", []).append(msg)
            BLACKBOARD.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            for _ in range(20):
                time.sleep(0.5)
                if BLACKBOARD.exists():
                    fresh = json.loads(BLACKBOARD.read_text(encoding="utf-8"))
                    for resp in fresh.get("hermes_responses", []):
                        if resp.get("reply_to") == msg["id"]:
                            return resp.get("content", "(empty)")
            return "Message queued. No Hermes response within 10s."
        except Exception as e:
            return f"Queue error: {e}"

    @staticmethod
    def _log(data: dict, direction: str) -> None:
        entry = {"ts": datetime.now().isoformat(), "direction": direction, **data}
        try:
            with HERMES_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass
