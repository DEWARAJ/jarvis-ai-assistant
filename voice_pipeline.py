"""JARVIS v6.0 — Voice pipeline: STT, TTS, wake word, text cleaner."""
from __future__ import annotations
import re, os, sys, tempfile, subprocess

WAKE_WORDS = {"jarvis","hey jarvis","ok jarvis","okay jarvis","yo jarvis"}

def _clean_for_speech(text: str) -> str:
    text = re.sub(r'```[\s\S]*?```', 'code block', text)
    text = re.sub(r'\[(?:OBS|ORI|DEC|ACT|MISSION|JARVIS[^\]]*)\]', '', text)
    text = re.sub(r'#{1,6}\s', '', text)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:450]

def speak(text: str) -> None:
    clean = _clean_for_speech(text)
    if not clean: return
    # Try edge-tts
    try:
        import edge_tts, asyncio
        async def _run():
            c = edge_tts.Communicate(clean, "en-US-GuyNeural")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            await c.save(tmp)
            if sys.platform == "win32":
                os.system(f'start /wait "" "{tmp}"')
            else:
                for p in ["mpg123","mpg321"]:
                    r = subprocess.run([p, tmp], capture_output=True)
                    if r.returncode == 0: break
            try: os.unlink(tmp)
            except: pass
        asyncio.run(_run())
        return
    except Exception: pass
    # Fallback pyttsx3
    try:
        import pyttsx3
        e = pyttsx3.init()
        e.setProperty('rate', 185)
        e.say(clean)
        e.runAndWait()
    except Exception: pass

def strip_wake_word(text: str) -> str:
    lo = text.lower()
    for w in sorted(WAKE_WORDS, key=len, reverse=True):
        if lo.startswith(w):
            return text[len(w):].strip(" ,.")
    return text

def is_wake_word(text: str) -> bool:
    lo = text.lower().strip()
    return any(lo.startswith(w) for w in WAKE_WORDS)

class VoiceListener:
    def __init__(self, energy_threshold: int = 300):
        self.available = False
        self._rec = None
        self._mic = None
        try:
            import speech_recognition as sr
            self._rec = sr.Recognizer()
            self._rec.energy_threshold = energy_threshold
            self._rec.dynamic_energy_threshold = True
            self._mic = sr.Microphone()
            with self._mic as src:
                self._rec.adjust_for_ambient_noise(src, duration=1.5)
            self.available = True
        except Exception:
            pass

    def listen_once(self, timeout: float = 3.0,
                    phrase_limit: float = 20.0) -> str | None:
        if not self.available: return None
        import speech_recognition as sr
        try:
            with self._mic as src:
                audio = self._rec.listen(src, timeout=timeout,
                                         phrase_time_limit=phrase_limit)
            try: return self._rec.recognize_google(audio)
            except sr.UnknownValueError: return None
            except sr.RequestError:
                try: return self._rec.recognize_sphinx(audio)
                except: return None
        except sr.WaitTimeoutError: return None
        except Exception: return None
