#!/usr/bin/env python3
"""Standalone scheduled greeting — spoken aloud by Windows, no GUI needed.

Run by Task Scheduler (see setup_schedule.bat):
    pythonw daily_greeting.py morning|midday|afternoon|evening|night
With no argument it picks the slot from the current time.
  - morning : "Good morning" + live weather
  - midday  : live weather + (if a commute is configured) opens live Google Maps traffic in Chrome
  - evening : warm welcome back
  - night   : "Good night"
Speaks via Windows SAPI so it works even when JARVIS isn't open. Degrades silently elsewhere.
"""
from __future__ import annotations
import os, sys, json, subprocess, datetime, urllib.request, urllib.parse

_DIR = os.path.dirname(os.path.abspath(__file__))


def _settings() -> dict:
    try:
        with open(os.path.join(_DIR, "config", "settings.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _weather() -> str:
    try:
        fmt = urllib.parse.quote("%C, %t, wind %w")
        req = urllib.request.Request("https://wttr.in/?format=" + fmt + "&m",
                                     headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            txt = r.read().decode("utf-8", errors="replace").strip()
        return txt if txt and "Unknown" not in txt else ""
    except Exception:
        return ""


def _open_in_chrome(url: str) -> bool:
    """Open url in Chrome specifically (falls back to default browser)."""
    if not sys.platform.startswith("win"):
        return False
    la = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(la, r"Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, url])
                return True
            except Exception:
                pass
    try:
        import webbrowser
        return webbrowser.open(url)
    except Exception:
        return False


def _traffic(settings: dict) -> str:
    """If a commute destination is configured, open live Google Maps traffic. Returns a spoken note."""
    comp = (settings.get("companion") or {})
    dest = (comp.get("commute_to") or "").strip()
    if not dest:
        return " To see your commute traffic, set your destination in settings."
    src = (comp.get("commute_from") or "").strip()
    base = "https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=" + urllib.parse.quote(dest)
    if src:
        base += "&origin=" + urllib.parse.quote(src)
    _open_in_chrome(base)
    return " I've opened live traffic for your route to " + dest + " on screen."


def build(slot: str, settings: dict):
    """Return (spoken_message, url_to_open_or_None)."""
    if slot == "morning":
        w = _weather()
        return ("Good morning, sir." + ((" Today's weather: " + w + ".") if w else "") +
                " I hope you have a productive day.", None)
    if slot == "midday":
        w = _weather()
        msg = "Good afternoon, sir."
        if w:
            msg += " The weather right now: " + w + "."
        msg += _traffic(settings)
        return (msg, None)
    if slot == "afternoon":
        return ("Good afternoon, sir. I hope the day is treating you well.", None)
    if slot == "evening":
        return ("Good evening, sir. Welcome back — I'm here whenever you need me.", None)
    return ("Good night, sir. Rest well; I'll keep watch.", None)


def speak(msg: str) -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ps = ("Add-Type -AssemblyName System.Speech; "
              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$s.Rate = 0; $s.Speak([Console]::In.ReadToEnd())")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       input=msg, text=True, timeout=40)
    except Exception:
        pass


def main():
    slot = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if slot not in ("morning", "midday", "afternoon", "evening", "night"):
        h = datetime.datetime.now().hour
        slot = ("morning" if 5 <= h < 12 else "midday" if 12 <= h < 14
                else "afternoon" if 14 <= h < 17 else "evening" if 17 <= h < 22 else "night")
    msg, _ = build(slot, _settings())
    print(msg)
    speak(msg)


if __name__ == "__main__":
    main()
