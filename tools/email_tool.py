"""Read-only Gmail access for JARVIS via IMAP (pure standard library).

Auth uses a Gmail APP PASSWORD (needs 2-step verification ON), stored in .env as:
    GMAIL_ADDRESS=you@gmail.com
    GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
JARVIS reads only — it NEVER sends or deletes. Keys are read from the environment,
never stored in memory or config.
"""
from __future__ import annotations
import os, imaplib, email
from email.header import decode_header
from tools.base_tool import BaseTool


def _decode(s) -> str:
    if not s:
        return ""
    out = []
    for part, enc in decode_header(s):
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                out.append(part.decode("utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


class EmailTool(BaseTool):
    name = "email"; scope = "read-only inbox (never sends)"
    HOST = "imap.gmail.com"

    def configured(self) -> bool:
        return bool(os.environ.get("GMAIL_ADDRESS") and os.environ.get("GMAIL_APP_PASSWORD"))

    def recent(self, n: int = 8, unread_only: bool = False) -> tuple[str, str]:
        """Return (status, digest_text). digest empty on failure/not-configured."""
        addr = os.environ.get("GMAIL_ADDRESS")
        pw = os.environ.get("GMAIL_APP_PASSWORD")
        if not (addr and pw):
            return ("Email isn't connected yet. Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to your .env "
                    "(use a Gmail App Password — needs 2-step verification on).", "")
        try:
            M = imaplib.IMAP4_SSL(self.HOST, timeout=20)
            M.login(addr, pw)
            M.select("INBOX", readonly=True)  # readonly = cannot modify/delete
            crit = "UNSEEN" if unread_only else "ALL"
            typ, data = M.search(None, crit)
            ids = data[0].split()
            ids = ids[-n:][::-1] if ids else []
            items = []
            for i in ids:
                typ, msg_data = M.fetch(i, "(RFC822.HEADER)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                items.append({
                    "from": _decode(msg.get("From", "")),
                    "subject": _decode(msg.get("Subject", "(no subject)")),
                    "date": msg.get("Date", ""),
                })
            M.logout()
        except imaplib.IMAP4.error as e:
            return (f"Login failed ({e}). Check the address and that you used an App Password, not your normal password.", "")
        except (OSError, TimeoutError) as e:
            return (f"Couldn't reach Gmail ({e}).", "")
        if not items:
            return ("No matching emails found.", "")
        lines = [f"{j+1}. {it['subject']}  —  {it['from']}" for j, it in enumerate(items)]
        kind = "unread" if unread_only else "recent"
        digest = f"{len(items)} {kind} emails:\n" + "\n".join(lines)
        return (f"Fetched {len(items)} {kind} email(s).", digest)
