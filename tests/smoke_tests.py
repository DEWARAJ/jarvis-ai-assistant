"""JARVIS v6.0 — Smoke tests. 20 tests covering all new modules.

Run: python -m pytest tests/smoke_tests.py -v
  or: python tests/smoke_tests.py
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import pytest


# ── 1. Root security module ───────────────────────────────────────────────────

def test_security_import():
    from security import classify_action, SecurityClass, AuditLog
    assert SecurityClass.A.value == "A"
    assert SecurityClass.X.value == "X"


def test_security_classify_b():
    from security import classify_action, SecurityClass
    assert classify_action("send email to boss") == SecurityClass.A  # B removed, all B->A


def test_security_classify_x():
    from security import classify_action, SecurityClass
    assert classify_action("modify core identity law") == SecurityClass.X


def test_security_classify_a():
    from security import classify_action, SecurityClass
    assert classify_action("what is 2+2") == SecurityClass.A


def test_audit_log_chain():
    import tempfile
    from security import AuditLog
    d = tempfile.mkdtemp()
    a = AuditLog(d)
    a.record("send email", "B", True)
    a.record("delete file", "C", False)
    ok, msg = a.verify_chain()
    assert ok, f"Chain broken: {msg}"
    entries = a.recent(5)
    assert len(entries) == 2


# ── 2. LLM router ────────────────────────────────────────────────────────────

def test_llm_router_import():
    from llm_router import complexity_score, classify_task, route
    assert callable(complexity_score)


def test_llm_router_complexity_range():
    from llm_router import complexity_score
    s = complexity_score("hi")
    assert 1 <= s <= 10
    s2 = complexity_score(
        "comprehensive deep analysis of trading strategy with OODA loop and "
        "full mission architecture step by step independent thinking research")
    assert 1 <= s2 <= 10
    assert s2 >= s


def test_llm_router_classify():
    from llm_router import classify_task
    assert classify_task("search latest news online") == "web_research"
    assert classify_task("write a Python class") == "code_generation"


# ── 3. Voice pipeline ─────────────────────────────────────────────────────────

def test_voice_pipeline_import():
    from voice_pipeline import WAKE_WORDS, _clean_for_speech, is_wake_word
    assert "jarvis" in WAKE_WORDS
    assert "hey jarvis" in WAKE_WORDS
    assert "okay jarvis" in WAKE_WORDS


def test_voice_clean_strips_tags():
    from voice_pipeline import _clean_for_speech
    raw = "[OBS] spotted threat [ORI] analyzing [DEC] respond [ACT] notify"
    clean = _clean_for_speech(raw)
    assert "[OBS]" not in clean
    assert "[ACT]" not in clean


def test_voice_wake_word_detection():
    from voice_pipeline import is_wake_word, strip_wake_word
    assert is_wake_word("hey jarvis turn on lights")
    assert not is_wake_word("hello there friend")
    stripped = strip_wake_word("okay jarvis play music")
    assert "play music" in stripped.lower()


# ── 4. Cognitive modules ──────────────────────────────────────────────────────

def test_ooda_import():
    from ooda_loop import run_ooda, extract_action, strip_ooda_tags
    assert callable(run_ooda)


def test_ooda_strip():
    from ooda_loop import strip_ooda_tags
    tagged = "[OBS] Screen visible. [ORI] Shows data. [DEC] Report. [ACT] Print output."
    clean  = strip_ooda_tags(tagged)
    assert "[OBS]" not in clean
    assert "Screen visible" in clean


def test_mission_engine_import():
    from mission_engine import (classify_mission, create_mission,
                                 format_mission, get_active_summary, Mission)
    assert callable(classify_mission)
    assert callable(get_active_summary)


def test_adapt_engine_import():
    from adapt_engine import backup_file, smoke_test, list_backups, rollback
    assert callable(backup_file)
    assert callable(smoke_test)


def test_adapt_smoke_nonexistent():
    from adapt_engine import smoke_test
    passed, out = smoke_test("nonexistent_xyzzy.py")
    assert not passed


# ── 5. Module package ─────────────────────────────────────────────────────────

def test_os_control():
    from modules.os_control import system_info
    info = system_info()
    assert isinstance(info, dict)
    assert "platform" in info


def test_network_control():
    from modules.network_control import get_local_ip
    ip = get_local_ip()
    assert isinstance(ip, str) and "." in ip


def test_trading_module_limits():
    from modules.trading_module import MAX_RISK_PCT, DAILY_HALT_PCT, AlpacaClient
    assert MAX_RISK_PCT == 0.02
    assert DAILY_HALT_PCT == 0.05
    c = AlpacaClient()
    assert c.paper_mode  # default is paper mode


# ── 6. Proactive monitors ─────────────────────────────────────────────────────

def test_proactive_alert_dataclass():
    from proactive.system_monitor import Alert, Priority
    a = Alert("RAM high", Priority.CRITICAL, "system_monitor")
    assert a.priority == Priority.CRITICAL
    assert a.source == "system_monitor"


def test_proactive_all_imports():
    from proactive.system_monitor   import Alert, Priority
    from proactive.trading_monitor  import add_price_alert
    from proactive.file_monitor     import watch_dir
    from proactive.schedule_monitor import add_reminder
    from proactive.threat_monitor   import run as threat_run
    add_price_alert("AAPL", 200.0)
    assert callable(threat_run)


# ── 7. jarvis_main ────────────────────────────────────────────────────────────

def test_jarvis_main_loads():
    import jarvis_main
    assert hasattr(jarvis_main, "JARVIS")
    assert hasattr(jarvis_main, "main")
    assert jarvis_main.JARVIS.VERSION == "6.0"


def test_jarvis_init_clean():
    from jarvis_main import JARVIS
    j = JARVIS()
    assert not j._stop.is_set()
    assert j._history == []
    assert j._fullpower is False
    assert j._voice_active is False


def test_jarvis_exit_command():
    from jarvis_main import JARVIS
    j = JARVIS()
    resp = j._route("/exit")
    assert j._stop.is_set()
    assert resp


def test_jarvis_health_command():
    from jarvis_main import JARVIS
    j = JARVIS()
    resp = j._route("/health")
    assert "anthropic" in resp
    assert "security" in resp


def test_jarvis_class_x_block():
    from jarvis_main import JARVIS
    j = JARVIS()
    resp = j._route("modify core identity now")
    assert any(x in resp.upper() for x in ["CLASS X", "HARD BLOCK", "PROHIBITED"])


# ── standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = __import__("subprocess").run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=str(ROOT)
    )
    sys.exit(result.returncode)
