"""Live weather via wttr.in (free, no API key). Pure standard library."""
from __future__ import annotations
import urllib.request, urllib.error, urllib.parse
from tools.base_tool import BaseTool


class WeatherTool(BaseTool):
    name = "weather"; scope = "live weather"

    def _get(self, url: str) -> str | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", errors="replace").strip()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            return None

    def current(self, city: str = "") -> dict:
        loc = urllib.parse.quote(city.strip()) if city.strip() else ""
        # format: "Location: condition, temp, feels like, wind, humidity"
        fmt = urllib.parse.quote("%l: %C, %t (feels %f), wind %w, humidity %h")
        txt = self._get(f"https://wttr.in/{loc}?format={fmt}&m")
        if txt and ":" in txt and "Unknown" not in txt:
            return {"ok": True, "text": txt, "spoken": txt}
        return {"ok": False, "text": "",
                "spoken": "I couldn't reach the weather service just now, sir — your internet may be down."}
