"""Voice input — real STT with wake-word gating and Sphinx offline fallback.

Priority:
  1. Google Web Speech (online, best accuracy) via SpeechRecognition
  2. Sphinx (offline fallback) via SpeechRecognition
  3. Stub — available=False, listen() returns None

Wake word: "jarvis" (configurable). When not heard, listen() returns None
so the queue doesn't flood with background noise fragments.

listen() blocks for up to `phrase_time_limit` seconds then returns.
Designed to be called in a loop from a daemon thread.
"""
from __future__ import annotations

_WAKE_WORDS = ("jarvis", "hey jarvis", "ok jarvis")


class VoiceInput:
    def __init__(self, logger=None, wake_word: bool = True,
                 phrase_time_limit: int = 10, energy_threshold: int = 300):
        self.logger           = logger
        self._wake_word       = wake_word
        self._phrase_limit    = phrase_time_limit
        self._energy          = energy_threshold
        self.available        = False
        self._recognizer      = None
        self._mic             = None
        self._engine          = "none"

        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = energy_threshold
            self._recognizer.dynamic_energy_threshold = True
            self._mic = sr.Microphone()
            # Warm up — calibrate for ambient noise (1 second)
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
            self.available = True
            self._engine   = "google"
            if logger:
                logger.info("[VoiceInput] SpeechRecognition ready (Google STT primary).")
        except ImportError:
            if logger:
                logger.info("[VoiceInput] speech_recognition not installed. Voice input disabled.")
        except Exception as e:
            if logger:
                logger.info(f"[VoiceInput] Mic init failed: {e}. Voice input disabled.")

    # ── public ──────────────────────────────────────────────────────────────

    def listen(self) -> str | None:
        """Non-blocking listen — returns text or None. Blocks up to phrase_time_limit."""
        if not self.available or self._recognizer is None or self._mic is None:
            return None
        import speech_recognition as sr
        try:
            with self._mic as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=2,
                    phrase_time_limit=self._phrase_limit,
                )
        except sr.WaitTimeoutError:
            return None
        except Exception:
            return None

        text = self._transcribe(audio)
        if not text:
            return None

        if self._wake_word:
            lo = text.lower()
            matched = next((w for w in _WAKE_WORDS if lo.startswith(w)), None)
            if matched is None:
                return None
            text = text[len(matched):].strip(" ,.!?")
            if not text:
                return None

        if self.logger:
            self.logger.info(f"[VoiceInput] heard: {text!r}")
        return text

    # ── internal ────────────────────────────────────────────────────────────

    def _transcribe(self, audio) -> str | None:
        import speech_recognition as sr
        try:
            return self._recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            pass  # network fail → try Sphinx
        try:
            return self._recognizer.recognize_sphinx(audio)
        except Exception:
            return None
