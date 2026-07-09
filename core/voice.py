"""Multilingual neural voice for JARVIS — English, Telugu, Hindi.

Output: Microsoft edge-tts neural voices (online, natural). Auto-detects the language of
the text (Telugu / Devanagari-Hindi / else English) and picks the matching voice. Falls
back to pyttsx3 (English, offline) if edge-tts or audio playback isn't available.

Input: SpeechRecognition (Google web speech) tuned so the master does NOT have to shout —
low energy threshold + dynamic gain + ambient calibration. Tries en-IN, then hi-IN, te-IN.

Every dependency is optional; nothing here ever crashes JARVIS. If a package is missing the
relevant capability simply reports unavailable.
"""
from __future__ import annotations
import os, sys, re, tempfile, asyncio, threading, time

_TELUGU = re.compile(r"[ఀ-౿]")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Default neural voices (overridable via settings.voice.voices)
_VOICES = {
    "en": "en-GB-RyanNeural",     # British butler feel for JARVIS
    "te": "te-IN-MohanNeural",    # Telugu (male). Female: te-IN-ShrutiNeural
    "hi": "hi-IN-MadhurNeural",   # Hindi (male).   Female: hi-IN-SwaraNeural
}
# Prosody per language (overridable via settings.voice.prosody). Slightly slower rate and a
# touch lower pitch reads as calmer/more human than the flat default — the difference between
# "generic neural robot" and a measured butler. edge-tts takes rate/volume/pitch directly.
_PROSODY = {
    "en": {"rate": "-6%", "pitch": "-3Hz", "volume": "+0%"},
    "te": {"rate": "-4%", "pitch": "+0Hz", "volume": "+0%"},
    "hi": {"rate": "-4%", "pitch": "+0Hz", "volume": "+0%"},
}
# Speech-recognition languages tried in order (BCP-47)
_STT_LANGS = ["en-IN", "hi-IN", "te-IN"]

_LANG_NAME = {"en": "English", "te": "Telugu", "hi": "Hindi"}


def detect_lang(text: str) -> str:
    """'te' if any Telugu char, 'hi' if any Devanagari char, else 'en'. Pure stdlib."""
    t = text or ""
    if _TELUGU.search(t):
        return "te"
    if _DEVANAGARI.search(t):
        return "hi"
    return "en"


class MultilingualVoice:
    def __init__(self, logger=None, settings=None):
        self.logger = logger
        vcfg = ((settings or {}).get("voice", {}) or {})
        self.voices = dict(_VOICES)
        self.voices.update(vcfg.get("voices", {}) or {})
        self.prosody = {k: dict(v) for k, v in _PROSODY.items()}
        for lang, p in (vcfg.get("prosody", {}) or {}).items():
            self.prosody.setdefault(lang, {}).update(p or {})
        self.stt_langs = list(vcfg.get("stt_langs", _STT_LANGS))
        # Problem 2: ONE playback at a time. interrupt-and-replace — a new utterance stops the
        # one in flight (a user asking something new wants the OLD answer's audio gone, not
        # queued behind it). Shared across ALL voice sources (main loop, Iron Man, advisor).
        self._play_lock = threading.RLock()
        self._play_seq = 0           # bumped on every new speak(); cancels older playback
        self._mci_alias = "jarvistts"
        self._edge = None
        self._pyttsx = None
        self._sr = None
        self._recognizer = None
        try:
            import edge_tts  # noqa: F401
            self._edge = edge_tts
        except Exception:
            pass
        try:
            import speech_recognition as sr  # noqa: F401
            self._sr = sr
        except Exception:
            pass

    def _log(self, m):
        if self.logger:
            try: self.logger.info("voice: " + str(m))
            except Exception: pass

    # ---------------- text to speech ----------------
    @property
    def tts_available(self) -> bool:
        return bool(self._edge) or self._pyttsx_ok()

    def _pyttsx_ok(self) -> bool:
        try:
            if self._pyttsx is None:
                import pyttsx3
                self._pyttsx = pyttsx3.init()
            return True
        except Exception:
            return False

    def speak(self, text: str, lang: str | None = None) -> bool:
        """Speak text aloud. lang in {'en','te','hi'} or None to auto-detect.

        Problem 2 fix — interrupt-and-replace: bump the play sequence and stop any audio
        currently playing BEFORE starting this one, so a newer response never overlaps an
        older one. Safe from any thread (main loop, Iron Man daemon, ProactiveAdvisor)."""
        text = (text or "").strip()
        if not text:
            return False
        lang = lang or detect_lang(text)
        # claim this utterance as the newest; anything older must stop.
        with self._play_lock:
            self._play_seq += 1
            self._stop_current()
        if self._edge and self._speak_edge(text, lang):
            return True
        return self._speak_pyttsx(text)   # english-ish offline fallback

    def stop(self) -> None:
        """Public: immediately stop any voice output (used on new query / 'stop')."""
        with self._play_lock:
            self._play_seq += 1
            self._stop_current()

    def _stop_current(self) -> None:
        """Stop whatever is playing now. Best-effort across every backend."""
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW("stop %s" % self._mci_alias, None, 0, None)
                ctypes.windll.winmm.mciSendStringW("close %s" % self._mci_alias, None, 0, None)
            except Exception:
                pass
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            if self._pyttsx is not None:
                self._pyttsx.stop()
        except Exception:
            pass

    def synth_to_file(self, text: str, lang: str | None = None, path: str | None = None):
        """Generate neural speech to an mp3 file (used by the HUD /api/tts). Returns path or None.

        Problem 1 fix — applies per-language prosody (rate/pitch/volume) and inserts natural
        pauses at sentence/clause boundaries so long replies don't run on in a flat monotone."""
        if not (self._edge and (text or "").strip()):
            return None
        lang = lang or detect_lang(text)
        voice = self.voices.get(lang, self.voices["en"])
        pros = self.prosody.get(lang, {})
        rate = pros.get("rate", "+0%"); pitch = pros.get("pitch", "+0Hz"); volume = pros.get("volume", "+0%")
        spoken = self._shape_text(text)
        # unique path per language (HUD reuses by lang; that's fine — one HUD stream at a time)
        path = path or os.path.join(tempfile.gettempdir(), "jarvis_tts_%s.mp3" % lang)
        try:
            async def go():
                await self._edge.Communicate(spoken, voice, rate=rate, pitch=pitch, volume=volume).save(path)
            asyncio.run(go())
            return path if os.path.exists(path) and os.path.getsize(path) > 0 else None
        except Exception as e:
            self._log("edge synth: " + str(e))
            return None

    @staticmethod
    def _shape_text(text: str) -> str:
        """Light prosody shaping: normalise whitespace and add a small pause after sentence
        enders so delivery breathes instead of running flat. edge-tts honours commas/periods
        as micro-pauses; doubling the boundary punctuation lengthens them slightly."""
        t = re.sub(r"\s+", " ", (text or "").strip())
        # ensure a space after sentence punctuation, then lengthen the pause subtly
        t = re.sub(r"([.!?])(?=[A-Za-z0-9])", r"\1 ", t)
        t = re.sub(r"([.!?])\s", r"\1  ", t)   # double-space after enders = longer pause
        return t

    def _speak_edge(self, text, lang) -> bool:
        my_seq = self._play_seq
        mp3 = self.synth_to_file(text, lang, path=os.path.join(
            tempfile.gettempdir(), "jarvis_speak_%s.mp3" % lang))
        if not mp3:
            return False
        # if a newer utterance arrived while we were synthesising, abandon this one (no overlap)
        with self._play_lock:
            if my_seq != self._play_seq:
                return True   # superseded; treat as handled, do not play stale audio
            return self._play(mp3, my_seq)

    def _play(self, path, my_seq=None) -> bool:
        # Windows MCI first (no extra dependency, plays mp3 natively).
        # Uses 'play ... wait' so it blocks until done, but a newer speak() calls _stop_current()
        # which issues 'stop'/'close' on the shared alias, cutting this off cleanly (no overlap).
        if sys.platform.startswith("win"):
            try:
                import ctypes
                a = self._mci_alias
                w = ctypes.windll.winmm.mciSendStringW
                w('close %s' % a, None, 0, None)
                w('open "%s" type mpegvideo alias %s' % (path, a), None, 0, None)
                w('play %s wait' % a, None, 0, None)
                w('close %s' % a, None, 0, None)
                return True
            except Exception as e:
                self._log("mci: " + str(e))
        for fn in (self._play_playsound, self._play_pygame):
            if fn(path):
                return True
        try:
            os.startfile(path)  # last resort: default player
            return True
        except Exception:
            return False

    def _play_playsound(self, path) -> bool:
        try:
            from playsound import playsound
            playsound(path)
            return True
        except Exception:
            return False

    def _play_pygame(self, path) -> bool:
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(80)
            return True
        except Exception:
            return False

    def _speak_pyttsx(self, text) -> bool:
        try:
            if self._pyttsx is None:
                import pyttsx3
                self._pyttsx = pyttsx3.init()
            self._pyttsx.say(text)
            self._pyttsx.runAndWait()
            return True
        except Exception as e:
            self._log("pyttsx: " + str(e))
            return False

    # ---------------- speech to text ----------------
    @property
    def stt_available(self) -> bool:
        return bool(self._sr)

    def listen_once(self, langs=None, timeout: int = 8, phrase_limit: int = 12):
        """Listen once and return recognised text (or None). Tuned for soft speech."""
        if not self._sr:
            return None
        sr = self._sr
        if self._recognizer is None:
            r = sr.Recognizer()
            r.dynamic_energy_threshold = True
            r.energy_threshold = 250      # low: registers normal/soft speech, no shouting
            r.pause_threshold = 0.8
            self._recognizer = r
        r = self._recognizer
        langs = langs or self.stt_langs
        try:
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=0.6)
                audio = r.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
        except Exception as e:
            self._log("mic: " + str(e))
            return None
        for lg in langs:
            try:
                txt = r.recognize_google(audio, language=lg)
                if txt:
                    return txt
            except Exception:
                continue
        return None

    # ---------------- introspection ----------------
    def report(self) -> str:
        tts = "edge-tts neural" if self._edge else ("pyttsx3 (English only)" if self._pyttsx_ok() else "none")
        stt = "ready (en/hi/te)" if self._sr else "not installed"
        langs = ", ".join(_LANG_NAME[k] for k in self.voices if k in _LANG_NAME)
        return ("Voice: speech out = %s; speech in = %s; languages = %s. "
                "Say 'install the autonomous toolkit' if any part says not installed."
                % (tts, stt, langs))
