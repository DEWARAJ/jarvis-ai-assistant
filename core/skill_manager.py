"""Skill Manager — JARVIS installs and upgrades its own skills from the live internet.

The master can say "install the vision skill" or "upgrade playwright" and JARVIS will fetch
it from PyPI and add the capability. Per the master's standing grant, this is enabled — with
the precautions he asked for:

  PRECAUTIONS (the "safe" part):
   - The actual install/upgrade runs ONLY after a single 'confirm' (one tap, not a wall).
   - Packages come from PyPI (pip); downloaded skill files must be HTTPS from allowlisted hosts,
     size-capped, and are SAVED for review — never auto-executed.
   - A deny-list + name validation blocks obvious junk; a static scanner flags risky code.
   - Everything is logged to logs/skills.log. Keys are never stored.
"""
from __future__ import annotations
import os, re, sys, json, time, subprocess, urllib.request, urllib.parse

# Friendly skill name -> the pip package(s) that unlock it.
SKILLS = {
    "vision": (["pillow"], "screen capture + image handling"),
    "automation": (["pyautogui"], "keyboard & mouse control"),
    "volume": (["pycaw"], "precise system volume control"),
    "system": (["psutil"], "CPU/RAM/disk/battery + process control"),
    "browser": (["playwright"], "real browser automation, one-word YouTube playback"),
    "ui": (["uiautomation"], "pixel-exact Windows UI clicking"),
    "voice": (["pyttsx3"], "offline text-to-speech"),
    "speech": (["SpeechRecognition"], "microphone speech-to-text"),
    "documents": (["python-docx", "openpyxl", "pypdf"], "read/write Word, Excel, PDF"),
    "ocr": (["pytesseract", "pillow"], "read text from images / the screen"),
    "data": (["pandas"], "data analysis & tables"),
    "embeddings": (["sentence-transformers"], "neural vector memory"),
    "screenshots": (["mss"], "fast multi-monitor screenshots"),
}

_PKG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_DENY = {"crypto-miner", "xmrig", "keylogger", "rat", "botnet", "pyminer"}
_DENY_SUBSTR = ("miner", "keylog", "botnet", "ransom")
_ALLOWED_HOSTS = {"raw.githubusercontent.com", "gist.githubusercontent.com",
                  "files.pythonhosted.org", "cdn.jsdelivr.net"}
_DANGER_PATTERNS = ["os.system", "subprocess", "eval(", "exec(", "__import__",
                    "socket.", "shutil.rmtree", "rm -rf", "base64.b64decode", "pickle.loads"]
_LOG = os.path.join("logs", "skills.log")


_KN_DIR = "skills_knowledge"
_KN_INDEX = os.path.join(_KN_DIR, "index.json")


def _slug(s: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", (s or "skill").lower()).strip("-") or "skill")[:60]


def _log(event: dict):
    try:
        os.makedirs("logs", exist_ok=True)
        event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


class SkillManager:
    def __init__(self, orch=None):
        self.orch = orch

    # ---- resolve a request to concrete pip packages ----
    def resolve(self, request: str):
        """Return (pkgs, label, kind) where kind is 'skill' (known software), 'pypi' (raw package),
        or 'none'."""
        req = (request or "").strip().lower()
        if not req:
            return (None, "no skill named", "none")
        for name, (pkgs, desc) in SKILLS.items():
            if re.search(r"\b" + re.escape(name) + r"\b", req):
                return (list(pkgs), name + " — " + desc, "skill")
        tok = req.replace("skill", "").replace("package", "").replace("the", "").strip().split()
        cand = tok[0] if tok else ""
        if not cand:
            return (None, "no skill named", "none")
        if cand in _DENY or any(s in cand for s in _DENY_SUBSTR):
            return (None, "that package is on the deny-list, sir", "none")
        if not _PKG_RE.match(cand):
            return (None, "that doesn't look like a valid package name", "none")
        return ([cand], cand + " (from PyPI)", "pypi")

    # ---- the confirmed action ----
    def do_install(self, pkgs: list, upgrade: bool = False) -> str:
        pkgs = [p for p in (pkgs or []) if _PKG_RE.match(p) and p not in _DENY
                and not any(s in p.lower() for s in _DENY_SUBSTR)]
        if not pkgs:
            return "Nothing valid to install, sir."
        cmd = [sys.executable, "-m", "pip", "install"] + (["--upgrade"] if upgrade else []) + pkgs
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            ok = r.returncode == 0
            _log({"event": "install", "pkgs": pkgs, "upgrade": upgrade, "ok": ok})
            if ok:
                verb = "Upgraded" if upgrade else "Installed"
                return f"{verb} {', '.join(pkgs)}, sir. Restart me to use the new skill."
            tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
            return "The install didn't fully succeed, sir: " + tail[0]
        except Exception as e:
            _log({"event": "install_error", "pkgs": pkgs, "error": str(e)})
            return f"I couldn't run the install, sir ({e})."

    # ---- download a skill file (saved for review, NOT executed) ----
    def download_skill(self, url: str, name: str = "") -> dict:
        url = (url or "").strip().strip('"').strip("'")
        if not url.lower().startswith("https://"):
            return {"ok": False, "detail": "downloads must be HTTPS, sir"}
        host = urllib.parse.urlparse(url).netloc.lower()
        if host not in _ALLOWED_HOSTS:
            return {"ok": False, "detail": f"'{host}' isn't an allowlisted source. Allowed: " + ", ".join(sorted(_ALLOWED_HOSTS))}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-OS skill-fetch"})
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read(2_000_000)  # 2 MB cap
            text = raw.decode("utf-8", errors="replace")
        except Exception as e:
            return {"ok": False, "detail": f"couldn't fetch it ({e})"}
        flags = [p for p in _DANGER_PATTERNS if p in text]
        safe_name = re.sub(r"[^a-z0-9_]+", "_", (name or os.path.basename(url) or "skill").lower()).strip("_") or "skill"
        if not safe_name.endswith("_py"):
            safe_name = safe_name.replace(".py", "")
        try:
            os.makedirs("skills_downloaded", exist_ok=True)
            path = os.path.join("skills_downloaded", safe_name + ".py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            return {"ok": False, "detail": f"couldn't save it ({e})"}
        _log({"event": "download_skill", "url": url, "path": path, "flags": flags})
        preview = "\n".join(text.splitlines()[:12])
        return {"ok": True, "path": os.path.abspath(path), "flags": flags,
                "preview": preview, "lines": len(text.splitlines())}

    # ---- status ----
    def list_installed(self) -> dict:
        import importlib
        out = {}
        for name, (pkgs, desc) in SKILLS.items():
            mods = {"pillow": "PIL", "python-docx": "docx", "sentence-transformers": "sentence_transformers",
                    "SpeechRecognition": "speech_recognition", "pytesseract": "pytesseract"}
            present = all(self._has(mods.get(p, p.replace("-", "_"))) for p in pkgs)
            out[name] = {"installed": present, "pkgs": pkgs, "desc": desc}
        return out

    @staticmethod
    def _has(mod: str) -> bool:
        import importlib
        try:
            importlib.import_module(mod)
            return True
        except Exception:
            return False

    # ===== Knowledge skill packs (learn a domain from the live internet) =====
    def _kn_index(self) -> list:
        try:
            with open(_KN_INDEX, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def knowledge_index(self) -> list:
        return self._kn_index()

    def recall_pack(self, topic: str) -> str:
        """Return the saved expert pack text for a learned topic (best match), or ''."""
        t = _slug(topic)
        for it in self._kn_index():
            if _slug(it.get("topic", "")) == t or t in _slug(it.get("topic", "")):
                try:
                    with open(it["path"], encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    return ""
        return ""

    def match_topic(self, query: str):
        t = _slug(query)
        for it in self._kn_index():
            st = _slug(it.get("topic", ""))
            if st and (st == t or (t and t in st) or st in t):
                return it.get("topic")
        return None

    def learn(self, topic: str, refresh: bool = False, deep: bool = False) -> dict:
        topic = (topic or "").strip()
        if not topic:
            return {"ok": False, "detail": "name the skill to learn, sir"}
        o = self.orch
        if not (o and getattr(o, "llm", None) and o.llm.available):
            return {"ok": False, "detail": "I need the internet and a brain online to learn a new skill, sir."}
        queries = [topic + " advanced tutorial", topic + " tips and best practices", topic + " common mistakes"]
        if deep:
            queries += [topic + " advanced techniques examples", topic + " expert workflow",
                        topic + " troubleshooting and shortcuts"]
        evidence = ""
        web = o.tools.get("web") if getattr(o, "tools", None) else None
        if web:
            for q in queries:
                try:
                    _st, res = web.search(q, n=3)
                    if res:
                        evidence += "\n" + res
                except Exception:
                    pass
        existing = self.recall_pack(topic) if (deep or refresh) else ""
        sysp = ("You are JARVIS assembling an expert SKILL PACK so you can advise your master like a seasoned "
                "practitioner. Sections: Overview; Core concepts; Step-by-step workflow; Advanced techniques; "
                "Tips & best practices; Common pitfalls; Recommended resources. Be concrete and accurate. "
                + ("Go COMPREHENSIVE and in-depth - advanced examples, edge cases, real workflows. " if deep else "")
                + "Plain text headers.")
        parts = ["Build an expert skill pack on: " + topic]
        if existing:
            parts.append("Expand and improve THIS existing pack (keep what works, add depth, fix gaps):\n" + existing[:4000])
        parts.append(("Live web evidence (use it and cite the best sources):\n" + evidence) if evidence
                     else "(No live web reachable - use your own expertise and say so.)")
        pack = o.llm.chat(sysp, "\n\n".join(parts))
        if not pack:
            return {"ok": False, "detail": "the reasoning core didn't return the pack just now, sir."}
        try:
            os.makedirs(_KN_DIR, exist_ok=True)
            path = os.path.join(_KN_DIR, _slug(topic) + ".md")
            tag = (" (deepened)" if deep else " (refreshed)") if (deep or refresh) else ""
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Skill pack: " + topic + "\n_Learned " + time.strftime("%Y-%m-%d %H:%M") + tag + "_\n\n" + pack)
            idx = [it for it in self._kn_index() if _slug(it.get("topic", "")) != _slug(topic)]
            idx.append({"topic": topic, "path": os.path.abspath(path), "summary": " ".join(pack.split())[:200],
                        "chars": len(pack), "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            with open(_KN_INDEX, "w", encoding="utf-8") as f:
                json.dump(idx[-100:], f, indent=2)
            _log({"event": "learn", "topic": topic, "deep": deep, "refresh": refresh, "chars": len(pack)})
        except Exception as e:
            return {"ok": True, "path": "", "summary": " ".join(pack.split())[:200], "topic": topic,
                    "detail": "learned but couldn't save (" + str(e) + ")", "pack": pack}
        return {"ok": True, "path": os.path.abspath(path), "summary": " ".join(pack.split())[:200],
                "topic": topic, "pack": pack, "deep": deep}
