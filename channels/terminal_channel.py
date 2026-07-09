"""Terminal channel — threaded queue architecture.

DESIGN: input() NEVER called in main loop. Keyboard input runs in
_keyboard_thread → input_queue. Voice input runs in _voice_thread →
input_queue. Main loop: input_queue.get(timeout=0.05). This fixes the
"only responds once" bug and allows concurrent voice + keyboard + alerts.

Queues:
  input_queue  : (source, text) tuples — keyboard or voice
  alert_queue  : proactive alerts from monitors → printed between replies
"""
from __future__ import annotations
import queue
import threading

from channels.voice_output import VoiceOutput
from channels.voice_input import VoiceInput


class TerminalChannel:
    def __init__(self, orchestrator, logger=None):
        self.orch    = orchestrator
        self.logger  = logger
        self.voice   = VoiceOutput(logger, getattr(orchestrator, "settings", None))
        self.mic     = VoiceInput(logger)

        self.input_queue: queue.Queue  = queue.Queue()
        self.alert_queue: queue.Queue  = queue.Queue()
        self._stop      = threading.Event()

    # ── boot ────────────────────────────────────────────────────────────────

    def boot_banner(self):
        banner = getattr(self.orch, "settings", {}).get("boot_banner", "JARVIS OS ONLINE")
        print("=" * 52)
        print(f"   {banner}")
        print("   Threaded Queue Core · Voice + Text Input")
        print("   Type 'help' for commands · 'shutdown jarvis' to exit")
        print("=" * 52)

    # ── threads ─────────────────────────────────────────────────────────────

    def _keyboard_thread(self):
        """Blocking input() lives HERE only — never in the main loop."""
        while not self._stop.is_set() and self.orch.running:
            try:
                text = input("\nJARVIS> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.input_queue.put(("keyboard", "shutdown jarvis"))
                return
            if text:
                self.input_queue.put(("keyboard", text))

    def _voice_thread(self):
        """Polls mic.listen() when voice is enabled. Non-blocking poll loop."""
        if not self.mic.available:
            return
        while not self._stop.is_set() and self.orch.running:
            try:
                text = self.mic.listen()
                if text:
                    self.input_queue.put(("voice", text))
            except Exception:
                pass
            # mic.listen() already has its own blocking timeout; small sleep prevents
            # a tight spin if it returns None immediately
            self._stop.wait(0.05)

    def _monitor_thread(self):
        """Drains proactive_monitor alerts into alert_queue."""
        try:
            from core.proactive_monitor import get_alerts
        except ImportError:
            return
        while not self._stop.is_set() and self.orch.running:
            try:
                for alert in get_alerts():
                    self.alert_queue.put(alert)
            except Exception:
                pass
            self._stop.wait(5.0)

    # ── main loop ───────────────────────────────────────────────────────────

    def run(self):
        self.boot_banner()

        # Start daemon threads
        for target in (self._keyboard_thread, self._voice_thread, self._monitor_thread):
            t = threading.Thread(target=target, daemon=True)
            t.start()

        while self.orch.running:
            # Drain any proactive alerts first (non-blocking)
            while not self.alert_queue.empty():
                try:
                    alert = self.alert_queue.get_nowait()
                    print(f"\n[JARVIS ALERT] {alert}")
                except queue.Empty:
                    break

            # Wait for next input (non-blocking with timeout so alerts stay live)
            try:
                source, text = self.input_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if not text:
                continue

            # Echo voice input so user sees what was heard
            if source == "voice":
                print(f"\nJARVIS> [voice] {text}")

            # Interrupt any in-flight TTS before processing new query
            try:
                self.voice.stop()
            except Exception:
                pass

            # Handle via orchestrator
            try:
                reply = self.orch.handle(text)
            except Exception as e:
                reply = f"[Error] {e}"

            print(reply)

            # Check for shutdown
            lo = text.lower()
            if any(s in lo for s in ("shutdown jarvis", "/exit", "goodbye jarvis")):
                self._stop.set()
                break

            # Speak reply (fires on background thread inside VoiceOutput)
            lang = getattr(self.orch, "speak_lang", "auto")
            self.voice.say(reply, getattr(self.orch, "voice_on", False),
                           None if lang == "auto" else lang)

        self._stop.set()
        print("\nJARVIS OS OFFLINE. Goodbye, sir.")
