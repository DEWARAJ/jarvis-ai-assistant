"""JARVIS v6.0 — Email (Gmail), SMS (Twilio), Calendar (Google), Push notifications."""
from __future__ import annotations
import os, smtplib, imaplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Gmail ────────────────────────────────────────────────────────────────────

def read_emails(n: int = 5) -> str:
    addr = os.getenv("GMAIL_ADDRESS","")
    pwd  = os.getenv("GMAIL_APP_PASSWORD","")
    if not addr or not pwd: return "GMAIL_ADDRESS and GMAIL_APP_PASSWORD not set in .env"
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com")
        M.login(addr, pwd)
        M.select("inbox")
        _, data = M.search(None, "ALL")
        ids = data[0].split()[-n:]
        msgs = []
        for i in reversed(ids):
            _, raw = M.fetch(i, "(RFC822)")
            msg = email.message_from_bytes(raw[0][1])
            msgs.append(f"From: {msg['From']}\nSubject: {msg['Subject']}\n---")
        M.logout()
        return "\n".join(msgs) if msgs else "Inbox empty."
    except Exception as e: return f"Email read error: {e}"


def send_email(to: str, subject: str, body: str, confirmed: bool = False) -> str:
    addr = os.getenv("GMAIL_ADDRESS","")
    pwd  = os.getenv("GMAIL_APP_PASSWORD","")
    if not addr or not pwd: return "GMAIL credentials not set."
    try:
        msg = MIMEMultipart()
        msg["From"] = addr; msg["To"] = to; msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(addr, pwd)
            s.send_message(msg)
        return f"Email sent to {to}."
    except Exception as e: return f"Email send error: {e}"


def create_draft(to: str, subject: str, body: str) -> str:
    return f"Draft (not sent): To={to} | Subject={subject} | Body={body[:100]}..."


# ── SMS via Twilio ────────────────────────────────────────────────────────────

def send_sms(message: str, to: str | None = None, confirmed: bool = False) -> str:
    if not confirmed:
        target = to or os.getenv("DEW_PHONE_NUMBER","Dew's number")
    try:
        from twilio.rest import Client
        client = Client(os.getenv("TWILIO_ACCOUNT_SID"),
                        os.getenv("TWILIO_AUTH_TOKEN"))
        client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=to or os.getenv("DEW_PHONE_NUMBER"))
        return f"SMS sent."
    except ImportError: return "twilio not installed. pip install twilio"
    except Exception as e: return f"SMS error: {e}"


# ── Push notifications ────────────────────────────────────────────────────────

def push_notify(message: str, title: str = "JARVIS") -> str:
    """Class A — JARVIS can push alerts without asking."""
    # Try ntfy first
    topic = os.getenv("NTFY_TOPIC","jarvis-dew")
    try:
        import requests
        r = requests.post(f"https://ntfy.sh/{topic}",
                         data=message.encode(),
                         headers={"Title": title}, timeout=5)
        if r.status_code == 200: return f"Push sent via ntfy."
    except Exception: pass
    # Try Pushbullet
    pb_key = os.getenv("PUSHBULLET_API_KEY","")
    if pb_key:
        try:
            import requests
            r = requests.post("https://api.pushbullet.com/v2/pushes",
                json={"type":"note","title":title,"body":message},
                headers={"Access-Token": pb_key}, timeout=5)
            if r.status_code == 200: return "Push sent via Pushbullet."
        except Exception: pass
    return "No push service configured (NTFY_TOPIC or PUSHBULLET_API_KEY)."


# ── Google Calendar ───────────────────────────────────────────────────────────

def list_calendar_events(days: int = 7) -> str:
    creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON","")
    if not creds_path: return "GOOGLE_CREDENTIALS_JSON not set in .env"
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from datetime import datetime, timezone, timedelta
        creds = Credentials.from_authorized_user_file(creds_path)
        svc = build("calendar","v3",credentials=creds)
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        result = svc.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = result.get("items",[])
        if not events: return f"No events in next {days} days."
        return "\n".join(
            f"- {e['start'].get('dateTime',e['start'].get('date'))}: {e.get('summary','(no title)')}"
            for e in events)
    except ImportError: return "google-api-python-client not installed."
    except Exception as e: return f"Calendar error: {e}"


def create_calendar_event(title: str, start: str, end: str,
                          description: str = "", confirmed: bool = False) -> str:
    creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON","")
    if not creds_path: return "GOOGLE_CREDENTIALS_JSON not set."
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(creds_path)
        svc = build("calendar","v3",credentials=creds)
        event = {"summary": title,
                 "description": description,
                 "start": {"dateTime": start, "timeZone": "America/New_York"},
                 "end":   {"dateTime": end,   "timeZone": "America/New_York"}}
        svc.events().insert(calendarId="primary",body=event).execute()
        return f"Event '{title}' created."
    except Exception as e: return f"Calendar create error: {e}"

