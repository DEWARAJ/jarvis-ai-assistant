"""JARVIS v2.0 — 4-tier persistent cognition memory engine.

Layers (spec v2.0):
  TIER 1  Session buffer  — held in the orchestrator's RAM history (not here).
  TIER 2  Episodic        — memory/episodic.jsonl  (append-only session summaries).
  TIER 3  Semantic        — memory/semantic.json   (durable facts, patterns, world model).
  TIER 4  Code memory     — memory/code_changelog.jsonl (every self-mutation).

This engine OWNS tiers 2-4 and the boot briefing. It deliberately reuses the existing
ConversationMemory (raw turn transcript, tier-1/2 source) and the same secret-redaction
posture as MemoryManager — it does not replace them. Wiring into orchestrator boot and the
slash-commands is a later phase; this module is self-contained and side-effect free until
its methods are called.

All writes redact secrets. JSONL tiers are append-only (O(1), corruption-tolerant).
semantic.json is read-modify-write with an atomic replace.
"""
from __future__ import annotations
import os, json, re, uuid, tempfile
from datetime import datetime

# Same redaction posture as conversation_memory.py — keys/passwords never persisted.
_SECRET = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\b(?:pplx|gsk|nvapi|AIza)[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|bearer)\s*[:=]?\s*\S{6,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
]


def _redact(text):
    if not isinstance(text, str):
        return text
    t = text
    for p in _SECRET:
        t = p.sub("[redacted]", t)
    return t


def _redact_deep(obj):
    if isinstance(obj, str):
        return _redact(obj)
    if isinstance(obj, list):
        return [_redact_deep(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _redact_deep(v) for k, v in obj.items()}
    return obj


def _now():
    return datetime.now().isoformat(timespec="seconds")


_SEMANTIC_SCHEMA = {
    "user_profile": {"name": "Dew", "goals": [], "preferences": {}, "projects": {}},
    "learned_patterns": {},
    "world_model": {},
    "last_updated": None,
}


class JarvisMemory:
    """Tiers 2-4 + boot briefing. Never raises on I/O — degrades to empty/no-op and logs."""

    def __init__(self, memory_dir="memory", logger=None):
        self.logger = logger
        self.dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        os.makedirs(os.path.join(memory_dir, "code_backups"), exist_ok=True)
        self.episodic_path = os.path.join(memory_dir, "episodic.jsonl")
        self.semantic_path = os.path.join(memory_dir, "semantic.json")
        self.changelog_path = os.path.join(memory_dir, "code_changelog.jsonl")

    # ---- shared jsonl helpers ----
    def _append_jsonl(self, path, entry):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_redact_deep(entry), ensure_ascii=False) + "\n")
            return True
        except OSError as e:
            if self.logger: self.logger.warn(f"jarvis_memory append {path} failed: {e}")
            return False

    def _read_jsonl(self, path, tail=None):
        out = []
        if not os.path.exists(path):
            return out
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        continue          # tolerate corrupt trailing line
        except OSError:
            return out
        return out[-tail:] if tail else out

    # ---- TIER 2: episodic ----
    def append_episode(self, summary, decisions=None, tasks_completed=None,
                       errors=None, mood="", session_id=None):
        """Record one session/episode summary. Returns the written entry's session_id."""
        sid = session_id or str(uuid.uuid4())
        entry = {
            "ts": _now(), "session_id": sid,
            "summary": (summary or "")[:4000],
            "decisions": decisions or [],
            "tasks_completed": tasks_completed or [],
            "errors": errors or [],
            "mood": mood or "",
        }
        self._append_jsonl(self.episodic_path, entry)
        return sid

    def recent_episodes(self, n=50):
        return self._read_jsonl(self.episodic_path, tail=n)

    # ---- TIER 3: semantic ----
    def load_semantic(self):
        if os.path.exists(self.semantic_path):
            try:
                with open(self.semantic_path, encoding="utf-8") as f:
                    data = json.load(f)
                # backfill any missing top-level keys from schema
                for k, v in _SEMANTIC_SCHEMA.items():
                    data.setdefault(k, json.loads(json.dumps(v)))
                return data
            except (OSError, json.JSONDecodeError):
                if self.logger: self.logger.warn("semantic.json unreadable; starting fresh")
        return json.loads(json.dumps(_SEMANTIC_SCHEMA))

    def _save_semantic(self, data):
        data["last_updated"] = _now()
        try:
            fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(_redact_deep(data), f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.semantic_path)        # atomic
            return True
        except OSError as e:
            if self.logger: self.logger.error(f"semantic save failed: {e}")
            return False

    def remember_fact(self, key, value, bucket="world_model"):
        """Set a durable fact. bucket in {world_model, learned_patterns} or 'preference'/'goal'/'project'."""
        d = self.load_semantic()
        if bucket == "preference":
            d["user_profile"]["preferences"][key] = value
        elif bucket == "goal":
            goals = d["user_profile"]["goals"]
            if value not in goals:
                goals.append(value)
        elif bucket == "project":
            d["user_profile"]["projects"][key] = value
        elif bucket == "learned_patterns":
            d["learned_patterns"][key] = value
        else:
            d["world_model"][key] = value
        ok = self._save_semantic(d)
        return {"ok": ok, "bucket": bucket, "key": key}

    def forget_semantic(self, key):
        """Remove a key from any semantic bucket (Class-B gated by caller). Returns where it hit."""
        d = self.load_semantic()
        hit = []
        for bucket in ("world_model", "learned_patterns"):
            if key in d[bucket]:
                del d[bucket][key]; hit.append(bucket)
        up = d["user_profile"]
        if key in up["preferences"]:
            del up["preferences"][key]; hit.append("preferences")
        if key in up["projects"]:
            del up["projects"][key]; hit.append("projects")
        if hit:
            self._save_semantic(d)
        return {"ok": bool(hit), "removed_from": hit}

    # ---- TIER 4: code memory ----
    def log_mutation(self, trigger, files_modified, diff_summary,
                     test_result="pass", rolled_back=False):
        entry = {
            "ts": _now(), "trigger": (trigger or "")[:500],
            "files_modified": files_modified or [],
            "diff_summary": (diff_summary or "")[:2000],
            "test_result": test_result, "rolled_back": bool(rolled_back),
        }
        self._append_jsonl(self.changelog_path, entry)
        return entry

    def recent_mutations(self, n=20):
        return self._read_jsonl(self.changelog_path, tail=n)

    # ---- BOOT BRIEFING (spec format) ----
    def boot_briefing(self, conversation_memory=None):
        """Build the session-start briefing string. If a ConversationMemory is passed,
        its last turns enrich the recap. Never raises."""
        eps = self.recent_episodes(n=50)
        sem = self.load_semantic()
        muts = self.recent_mutations(n=5)
        last = eps[-1] if eps else None

        lines = ["=== JARVIS MEMORY BRIEFING ===", ""]
        if last:
            lines.append(f"LAST SESSION: {last.get('ts','?')}")
            lines.append(f"SUMMARY: {last.get('summary','(none)')}")
            mood = last.get("mood")
            if mood:
                lines.append(f"LAST KNOWN STATE: {mood}")
        else:
            lines.append("LAST SESSION: (first run — no episodic history yet)")
        lines.append("")

        projects = sem.get("user_profile", {}).get("projects", {})
        if projects:
            lines.append("ACTIVE PROJECTS:")
            for name, state in projects.items():
                lines.append(f"- {name}: {state}")
            lines.append("")

        if last and last.get("tasks_completed"):
            lines.append("LAST SESSION TASKS:")
            for t in last["tasks_completed"][:10]:
                lines.append(f"- {t}")
            lines.append("")

        if muts:
            lines.append("RECENT CODE MUTATIONS (last 5):")
            for m in muts:
                flag = " [ROLLED BACK]" if m.get("rolled_back") else ""
                lines.append(f"- {m.get('ts','?')} {m.get('diff_summary','')[:80]}{flag}")
            lines.append("")

        prefs = sem.get("user_profile", {}).get("preferences", {})
        if prefs:
            lines.append("DEW PREFERENCES LEARNED:")
            for k, v in list(prefs.items())[:12]:
                lines.append(f"- {k}: {v}")
            lines.append("")

        if conversation_memory is not None:
            try:
                n = conversation_memory.count()
                lines.append(f"TRANSCRIPT: {n} turns logged across all sessions.")
            except Exception:
                pass

        lines.append("=== END BRIEFING ===")
        return "\n".join(lines)

    def stats(self):
        sem = self.load_semantic()
        return {
            "episodes": len(self.recent_episodes(n=10_000)),
            "mutations": len(self.recent_mutations(n=10_000)),
            "world_model_keys": len(sem.get("world_model", {})),
            "patterns": len(sem.get("learned_patterns", {})),
        }
