"""JARVIS v6.0 — IoT: Fitbit, Home Assistant, MQTT, smart home."""
from __future__ import annotations
import os

try: import requests; _REQUESTS = True
except ImportError: _REQUESTS = False


# ── Fitbit ────────────────────────────────────────────────────────────────────

def get_fitbit_today() -> dict:
    """Get today's Fitbit data: steps, heart rate, sleep."""
    client_id = os.getenv("FITBIT_CLIENT_ID","")
    if not client_id: return {"error": "FITBIT_CLIENT_ID not set"}
    if not _REQUESTS: return {"error": "requests not installed"}
    token = os.getenv("FITBIT_ACCESS_TOKEN","")
    if not token:
        return {"error": "FITBIT_ACCESS_TOKEN not set. Run Fitbit OAuth flow first."}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        data: dict = {}
        # Steps
        r = requests.get("https://api.fitbit.com/1/user/-/activities/date/today.json",
                         headers=headers, timeout=10)
        if r.status_code == 200:
            summary = r.json().get("summary",{})
            data["steps"] = summary.get("steps",0)
            data["calories"] = summary.get("caloriesOut",0)
            data["active_minutes"] = summary.get("fairlyActiveMinutes",0)
        # Heart rate
        r2 = requests.get("https://api.fitbit.com/1/user/-/activities/heart/date/today/1d.json",
                          headers=headers, timeout=10)
        if r2.status_code == 200:
            hr = r2.json().get("activities-heart",[])
            if hr: data["resting_hr"] = hr[-1].get("value",{}).get("restingHeartRate","N/A")
        return data
    except Exception as e: return {"error": str(e)}


# ── Home Assistant ─────────────────────────────────────────────────────────────

class HomeAssistant:
    def __init__(self):
        self.url   = os.getenv("HOME_ASSISTANT_URL","").rstrip("/")
        self.token = os.getenv("HOME_ASSISTANT_TOKEN","")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"}

    def _check(self) -> str | None:
        if not self.url or not self.token:
            return "HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN not set"
        if not _REQUESTS: return "requests not installed"
        return None

    def get_states(self, domain: str | None = None) -> list[dict]:
        err = self._check()
        if err: return [{"error": err}]
        try:
            r = requests.get(f"{self.url}/api/states",
                             headers=self._headers(), timeout=10)
            states = r.json()
            if domain:
                states = [s for s in states
                          if s.get("entity_id","").startswith(domain+".")]
            return [{"entity_id": s["entity_id"],
                     "state": s["state"],
                     "name": s.get("attributes",{}).get("friendly_name","")}
                    for s in states[:20]]
        except Exception as e: return [{"error": str(e)}]

    def turn_on(self, entity_id: str, confirmed: bool = False) -> str:
        err = self._check()
        if err: return err
        try:
            domain = entity_id.split(".")[0]
            requests.post(f"{self.url}/api/services/{domain}/turn_on",
                         headers=self._headers(),
                         json={"entity_id": entity_id}, timeout=10)
            return f"Turned on: {entity_id}"
        except Exception as e: return f"HA error: {e}"

    def turn_off(self, entity_id: str, confirmed: bool = False) -> str:
        err = self._check()
        if err: return err
        try:
            domain = entity_id.split(".")[0]
            requests.post(f"{self.url}/api/services/{domain}/turn_off",
                         headers=self._headers(),
                         json={"entity_id": entity_id}, timeout=10)
            return f"Turned off: {entity_id}"
        except Exception as e: return f"HA error: {e}"


# ── MQTT ──────────────────────────────────────────────────────────────────────

def mqtt_publish(topic: str, message: str, host: str = "localhost",
                 port: int = 1883, confirmed: bool = False) -> str:
    try:
        import paho.mqtt.publish as publish
        publish.single(topic, message, hostname=host, port=port)
        return f"Published to {topic}: {message}"
    except ImportError: return "paho-mqtt not installed. pip install paho-mqtt"
    except Exception as e: return f"MQTT error: {e}"
