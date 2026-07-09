"""Voice output — multilingual neural (English / Telugu / Hindi) with safe fallbacks.

Uses core.voice.MultilingualVoice (edge-tts neural voices, auto language detection).
If edge-tts isn't installed it falls back to pyttsx3 (English). Never crashes; if no
audio is available it simply stays silent. Keeps the say(text, enabled) interface.

Playback runs on a background thread so the conversation loop never blocks waiting for
audio to finish — this is what lets a NEW query arrive mid-playback and interrupt the
old one (interrupt-and-replace, handled inside MultilingualVoice via its play lock).
"""
from __future__ import annotations
import threading


class VoiceOutput:
    def __init__(self, logger=None, settings=None):
        self.logger = logger
        self.voice = None
        try:
            from core.voice import MultilingualVoice
            self.voice = MultilingualVoice(logger=logger, settings=settings or {})
        except Exception as e:
            if logger:
                logger.info("Voice output unavailable (%s). Text only." % e)

    @property
    def available(self) -> bool:
        return bool(self.voice and self.voice.tts_available)

    def say(self, text: str, enabled: bool, lang: str | None = None) -> None:
        if not (enabled and self.voice):
            return
        # Fire-and-forget on a daemon thread. MultilingualVoice.speak() bumps its play
        # sequence and stops any in-flight audio first, so concurrent says never overlap —
        # the newest wins (interrupt-and-replace). The main loop stays responsive.
        def _run():
            try:
                self.voice.speak(text, lang=lang)
            except Exception as e:
                if self.logger:
                    self.logger.warn("TTS failed: %s" % e)
        threading.Thread(target=_run, name="tts-speak", daemon=True).start()

    def stop(self) -> None:
        """Immediately silence any current/queued speech (new query or 'stop')."""
        try:
            if self.voice:
                self.voice.stop()
        except Exception:
            pass
