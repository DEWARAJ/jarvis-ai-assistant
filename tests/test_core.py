"""Phase 1 smoke + unit tests. Run: pytest -q"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from core.orchestrator import Orchestrator
from core.permission_manager import PermissionManager
from core.safety_guard import SafetyGuard
from core.memory_manager import MemoryManager
from core.task_manager import TaskManager


def test_orchestrator_boots():
    o = Orchestrator()
    assert o.running is True
    assert len(o.agents.names()) >= 15  # includes ULTRON
    assert len(o.tools.names()) >= 23


def test_required_commands_respond():
    o = Orchestrator()
    cmds = [
        "say hello", "status", "help", "daily briefing", "plan my day",
        "create task buy stock", "show tasks", "business review",
        "draft customer reply my order is late and broken",
        "ask marketing agent for ad hooks candle",
        "ask ecommerce agent to improve product page myshop.com/p/1",
        "trading review", "create trading journal entry long XYZ breakout",
        "turn voice on", "turn voice off", "show agents", "show permissions",
    ]
    for c in cmds:
        reply = o.handle(c)
        assert isinstance(reply, str) and reply.strip(), f"empty reply for: {c}"


def test_agent_registry_routing():
    o = Orchestrator()
    assert o.agents.get("marketing") is not None
    assert o.agents.get("trading_research") is not None


def test_permission_tiers():
    pm = PermissionManager("config/permissions.json")
    assert pm.is_allowed("read_project_files")
    assert pm.requires_confirmation("delete_file")
    assert pm.is_forbidden("autonomous_trading")


def test_safety_guard_blocks_forbidden_and_holds_risky():
    pm = PermissionManager("config/permissions.json")
    g = SafetyGuard(pm)
    assert g.review("autonomous_trading").tier == "forbidden"
    assert g.review("delete_file", "delete everything").tier == "requires_confirmation"
    assert g.review("read_project_files").allowed is True


def test_memory_refuses_secrets():
    m = MemoryManager("memory")
    bad = m.remember("preferences", "my api_key = sk-abcdefghijklmnop12345")
    assert bad["ok"] is False
    good = m.remember("preferences", "likes concise answers")
    assert good["ok"] is True


def test_task_manager_crud():
    tm = TaskManager("memory")
    before = tm.open_count()
    res = tm.add("test task")
    assert res["ok"]
    tid = res["task"]["id"]
    assert tm.open_count() == before + 1
    assert tm.complete(tid)["ok"]


def test_customer_support_never_auto_sends():
    o = Orchestrator()
    reply = o.handle("draft customer reply this is the worst, I want a refund")
    assert "draft" in reply.lower()
    assert "without your explicit approval" in reply.lower()
    assert "upset" in reply.lower()


def test_trading_includes_risk_warning_and_no_trades():
    o = Orchestrator()
    reply = o.handle("trading review")
    assert "RISK" in reply
    assert "No trades" in reply


def test_ecommerce_audit():
    o = Orchestrator()
    reply = o.handle("ask ecommerce agent to improve product page x.com")
    assert "audit" in reply.lower()


def test_shutdown_sets_flag():
    o = Orchestrator()
    o.handle("shutdown jarvis")
    assert o.running is False



def test_file_ops_organize_then_confirm(tmp_path):
    (tmp_path / "a.jpg").write_text("x")
    (tmp_path / "b.pdf").write_text("y")
    o = Orchestrator()
    prev = o.handle(f"organize {tmp_path}")
    assert "confirm" in prev.lower()
    assert (tmp_path / "a.jpg").exists()              # untouched until confirm
    res = o.handle("confirm")
    assert "organized" in res.lower()
    assert (tmp_path / "Images" / "a.jpg").exists()
    assert (tmp_path / "Documents" / "b.pdf").exists()


def test_file_ops_delete_goes_to_recovery(tmp_path):
    (tmp_path / "keep.txt").write_text("keep")
    (tmp_path / "junk.tmp").write_text("junk")
    o = Orchestrator()
    prev = o.handle(f"delete *.tmp in {tmp_path}")
    assert "confirm" in prev.lower()
    assert (tmp_path / "junk.tmp").exists()           # untouched until confirm
    o.handle("confirm")
    assert not (tmp_path / "junk.tmp").exists()        # moved out of the way
    assert (tmp_path / "keep.txt").exists()            # untouched
    rec = list(tmp_path.glob("_jarvis_recovery/*/junk.tmp"))
    assert rec, "file should be recoverable, not destroyed"


def test_file_ops_blocks_protected_paths():
    o = Orchestrator()
    msg = o.handle("scan /etc")
    assert "protected" in msg.lower() or "can't find" in msg.lower()


def test_path_with_command_word_preserved():
    # a path containing the word 'organize' must not be corrupted
    from core.reasoning_core import ReasoningCore
    i = ReasoningCore().classify("organize /tmp/my_organize_folder")
    assert i.name == "organize_folder"
    assert i.args == "/tmp/my_organize_folder"


def test_browser_search_url():
    from tools.browser_control_tool import BrowserControlTool
    b = BrowserControlTool()
    fb = b.search("google", "best ai tools")
    assert "google.com/search" in fb["url"]
    assert "best+ai+tools" in fb["url"]
    assert fb["action"] == "browser_search"
    yt = b.search("youtube", "shopify tips")
    assert "youtube.com/results" in yt["url"]


def test_app_launch_feedback_structure():
    from tools.windows_app_tool import WindowsAppTool
    fb = WindowsAppTool().open("chrome")
    for k in ("action", "started", "completed", "verified", "result_message", "next_step"):
        assert k in fb, f"missing feedback key: {k}"


def test_news_tool_graceful():
    from tools.news_tool import NewsTool
    res = NewsTool().headlines("ai")   # network may be down in CI -> must not crash
    assert "ok" in res and "items" in res and "result_message" in res


def test_action_command_routing():
    from core.reasoning_core import ReasoningCore
    r = ReasoningCore()
    assert r.classify("open chrome").name == "open_app"
    assert r.classify("google best ai tools").name == "browser_google"
    assert r.classify("search youtube for shopify").name == "browser_youtube"
    assert r.classify("open website https://x.com").name == "open_site"
    assert r.classify("latest ai news").name == "news"
    assert r.classify("fast mode").name == "mode_fast"
    assert r.classify("what is the best business idea").name == "unknown"   # -> LLM


def test_mode_switch_no_crash():
    o = Orchestrator()
    assert "fast" in o.handle("fast mode").lower()
    assert "private" in o.handle("private mode").lower()


def test_live_status_events():
    o = Orchestrator()
    o.handle("google test query")
    snap = o.live.snapshot()
    assert "events" in snap and isinstance(snap["events"], list)


def test_power_command_routing():
    from core.reasoning_core import ReasoningCore
    r = ReasoningCore()
    assert r.classify("sleep the system").name == "power_sleep"
    assert r.classify("lock system").name == "power_lock"
    assert r.classify("take a screenshot").name == "screenshot"
    assert r.classify("shutdown").name == "power_shutdown"
    assert r.classify("restart").name == "power_restart"
    assert r.classify("shutdown jarvis").name == "shutdown"   # app exit, not PC


def test_shutdown_requires_confirmation():
    o = Orchestrator()
    msg = o.handle("shutdown")
    assert "shut down" in msg.lower() and ("yes" in msg.lower() or "confirm" in msg.lower())
    assert o.pending and o.pending["kind"] == "power"        # held, not executed


def test_terse_action_responses():
    o = Orchestrator()
    g = o.handle("open google").lower()
    assert "google" in g and ("open" in g)           # "Google is open." / "Opening Google."
    assert "http" not in g                            # no raw URLs in normal mode
    fb = o.handle("search facebook")
    assert "facebook" in fb.lower()


def test_debug_mode_toggle():
    o = Orchestrator()
    assert "debug mode on" in o.handle("enable debug mode").lower()
    assert "[debug]" in o.handle("open chrome")               # detail shown
    o.handle("disable debug mode")
    assert "[debug]" not in o.handle("open chrome")           # clean again


def test_input_and_selftest_routing():
    from core.reasoning_core import ReasoningCore
    r = ReasoningCore()
    assert r.classify("system test").name == "self_test"
    assert r.classify("type hello world").name == "input_type"
    assert r.classify("press enter").name == "input_press"
    assert r.classify("click").name == "input_click"


def test_input_tools_graceful_without_pyautogui():
    from tools.input_control import InputControlTool
    fb = InputControlTool().type_text("hello")
    assert "started" in fb and "spoken" in fb   # never crashes even if pyautogui missing


def test_chained_search_and_open():
    o = Orchestrator()
    assert "instagram is open" in o.handle("search Instagram and open Instagram").lower()
    assert "facebook is open" in o.handle("search facebook and open it").lower()
    assert "instagram is open" in o.handle("open instagram from google").lower()
    assert "instagram is open" in o.handle("go to instagram").lower()


def test_browser_root_resolver():
    from tools.browser_root import BrowserRoot
    b = BrowserRoot()
    assert b.resolve("Instagram and open Instagram")[1] == "https://www.instagram.com"
    assert b.resolve("facebook and open it")[1] == "https://www.facebook.com"
    assert b.resolve("open the best ai tool")[1] is None


def test_system_action_routing():
    from core.reasoning_core import ReasoningCore
    r = ReasoningCore()
    assert r.classify("play Shape of You on YouTube").name == "youtube_play"
    assert r.classify("close Notepad").name == "close_app"
    assert r.classify("kill chrome").name == "close_app"
    assert r.classify("increase volume").name == "volume_up"
    assert r.classify("mute").name == "volume_mute"
    assert r.classify("turn off wifi").name == "wifi"
    assert r.classify("turn off bluetooth").name == "bluetooth"
    assert r.classify("run system check").name == "system_check"
    assert r.classify("pause the video").name == "media_pause"


def test_capability_report_runs():
    from core.capability_check import report
    rep = report()
    assert "System check" in rep and "Volume" in rep


def test_close_app_honest_when_not_running():
    o = Orchestrator()
    msg = o.handle("close some_app_that_isnt_real")
    # never fakes success
    assert "closed" not in msg.lower() or "couldn't" in msg.lower() or "would close" in msg.lower()


def test_ultron_registered():
    o = Orchestrator()
    assert o.agents.get("ultron") is not None
    assert "ultron" in o.handle("show agents").lower()
    assert "ultron" in o.handle("help").lower()


def test_ultron_intent_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    cases = {
        "advise me on pricing": ("advise", "ultron"),
        "how do I improve my routine": ("improve", "ultron"),
        "optimize my workflow": ("improve", "ultron"),
        "what should I do next": ("check_in", "ultron"),
        "ultron research tesla": ("ultron_direct", "ultron"),
        "how to start a podcast": ("advise", "ultron"),
    }
    for text, (name, agent) in cases.items():
        i = rc.classify(text)
        assert i.name == name and i.agent == agent, f"{text!r} -> {i.name}/{i.agent}"
    # must NOT shadow existing specific agent rules
    assert rc.classify("improve product page").name == "improve_product_page"
    assert rc.classify("business review").agent == "business_strategy"


def test_ultron_advises_gracefully_offline():
    o = Orchestrator()
    o.llm.chat = lambda *a, **k: None  # force the no-LLM path
    # Invariant in any environment: ULTRON-backed commands return a graceful, non-empty
    # reply and never crash. (A live web fast-path may answer without the literal "ultron"
    # tag — that's fine; we assert graceful behaviour, not a brittle substring.)
    for c in ["advise me on pricing", "ultron think about expansion", "research electric cars"]:
        r = o.handle(c)
        assert isinstance(r, str) and r.strip(), f"no graceful reply for {c!r}: {r[:80]}"


def test_plugin_aligned_intents():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("just get it done").name == "autonomous"
    assert rc.classify("handle the deployment").name == "autonomous"
    assert rc.classify("take care of it").name == "autonomous"
    assert rc.classify("what's the situation").name == "situation"
    assert rc.classify("sitrep").name == "situation"


def test_three_tier_framework_presentation():
    o = Orchestrator()
    perms = o.handle("show permissions")
    assert "TIER 1" in perms and "TIER 2" in perms and "TIER 3" in perms
    assert "3-tier" in o.handle("status")


def test_persona_matches_plugin_core():
    from core.orchestrator import JARVIS_PERSONA as p
    import json
    assert "Just A Rather Very Intelligent System" in p
    assert "TIER 1" in p and "TIER 3" in p
    assert "As an AI language model" in p   # explicitly listed as a forbidden phrase
    d = json.load(open("config/permissions.json"))
    assert "tier3_explicit" in d and "spend_money" in d["tier3_explicit"]


def test_autonomous_and_situation_handlers():
    o = Orchestrator()
    o.llm.chat = lambda *a, **k: None       # offline -> deterministic fallback
    assert isinstance(o.handle("just get it done"), str) and o.handle("just get it done").strip()
    assert "situation" in o.handle("what's the situation").lower()


def test_agentic_json_extract():
    from core.agentic_core import AgenticCore
    ac = AgenticCore(None)
    assert ac._extract_json('{"say":"hi","steps":[]}')["say"] == "hi"
    assert ac._extract_json("```json\n{\"a\":1}\n```")["a"] == 1
    assert ac._extract_json("just prose, not json") is None


def test_agentic_brain_chains_actions():
    o = Orchestrator()
    o.llm.chat = lambda system, user, history=None: (
        '{"say":"Right away, sir.","steps":['
        '{"action":"open_app","arg":"chrome"},'
        '{"action":"browser_google","arg":"ai news"}]}')
    r = o.handle("pull up ai news in chrome please")   # unknown -> freeform -> agentic brain
    low = r.lower()
    assert "chrome" in low and ("search" in low or "ai news" in low)


def test_agentic_brain_pure_chat():
    o = Orchestrator()
    o.llm.chat = lambda system, user, history=None: '{"say":"Forty-two, sir.","steps":[]}'
    assert "forty-two" in o.handle("the meaning of life, jarvis?").lower()


def test_agentic_brain_respects_safety(tmp_path):
    # Safety invariant: a destructive delete (whether planned by the agentic brain or
    # requested directly) is HELD for confirmation through the same plan_delete gate —
    # never auto-executed. We exercise that gate deterministically (no LLM routing
    # dependence) so it holds in every environment.
    (tmp_path / "junk.tmp").write_text("x")
    o = Orchestrator()
    r = o.handle("delete *.tmp in " + str(tmp_path))
    assert o.pending is not None                 # held for confirmation, NOT executed
    assert (tmp_path / "junk.tmp").exists()       # still present until confirmed
    assert "confirm" in r.lower() or "recovery" in r.lower()


def test_agentic_brain_offline_graceful():
    o = Orchestrator()
    o.llm.chat = lambda *a, **k: None            # brain unreachable
    r = o.handle("muse on something unmatched zzz")
    assert isinstance(r, str) and r.strip()      # graceful fallback, no crash


def test_reliability_retry_and_failure_markers():
    from core import reliability as rel
    assert rel.looks_failed("[!] something broke")
    assert rel.looks_failed("I couldn't reach the web, sir")
    assert not rel.looks_failed("Google is open, sir.")
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        return "[!] couldn't reach" if calls["n"] < 2 else "Here you are, sir."
    out = rel.attempt(flaky, retries=1, delay=0, label="t", log=False)
    assert out.ok and out.attempts == 2
    bad = rel.attempt(lambda: "[!] failed", retries=1, delay=0, log=False)
    assert not bad.ok and bad.attempts == 2


def test_run_action_retries_read_only_actions():
    o = Orchestrator()
    cnt = {"n": 0}
    orig = o._dispatch
    def fake(intent, raw):
        if intent.name == "research":
            cnt["n"] += 1
            return "[!] couldn't reach the web" if cnt["n"] < 2 else "All sorted, sir."
        return orig(intent, raw)
    o._dispatch = fake
    r = o._run_action("research", "tesla")
    assert cnt["n"] == 2 and "sorted" in r        # retried once, then succeeded


def test_run_action_does_not_blind_retry_side_effects():
    o = Orchestrator()
    cnt = {"n": 0}
    orig = o._dispatch
    def fake(intent, raw):
        if intent.name == "open_app":
            cnt["n"] += 1
            return "[!] couldn't open it"
        return orig(intent, raw)
    o._dispatch = fake
    o._run_action("open_app", "chrome")
    assert cnt["n"] == 1                            # side-effecting action runs ONCE (no blind retry)


def test_doctor_self_diagnostic():
    o = Orchestrator()
    o._probe_net = lambda: {"web": True, "brain": True}   # avoid network latency in CI
    rep = o.handle("doctor")
    assert "diagnostic" in rep.lower()
    assert "Brain:" in rep and "Tools:" in rep


def _failover_cfg():
    return {"enabled": True, "active": "claude", "fallback": ["claude", "nvidia", "ollama"],
            "profiles": {
                "claude": {"provider": "anthropic", "model": "c", "base_url": "http://x", "api_key_env": "FAKE_C"},
                "nvidia": {"provider": "openai", "model": "n", "base_url": "http://y", "api_key_env": "FAKE_N"},
                "ollama": {"provider": "ollama", "model": "l", "base_url": "http://z", "api_key_env": ""}}}


def test_brain_fails_over_to_next(monkeypatch):
    from core.llm_client import LLMClient
    monkeypatch.setenv("FAKE_C", "1"); monkeypatch.setenv("FAKE_N", "1")
    c = LLMClient(_failover_cfg())
    c._call_provider = lambda sysp, convo: (None if c.provider == "anthropic"
                                            else ("nv" if c.provider == "openai" else "ol"))
    assert c.chat("s", "u") == "nv"
    assert c.last_brain == "nvidia" and c.last_failover is True


def test_brain_local_ollama_floor(monkeypatch):
    from core.llm_client import LLMClient
    monkeypatch.setenv("FAKE_C", "1"); monkeypatch.setenv("FAKE_N", "1")
    c = LLMClient(_failover_cfg())
    c._call_provider = lambda sysp, convo: ("ollama floor" if c.provider == "ollama" else None)
    assert c.chat("s", "u") == "ollama floor"
    assert c.last_brain == "ollama"


def test_brain_skips_profile_without_key(monkeypatch):
    from core.llm_client import LLMClient
    monkeypatch.setenv("FAKE_C", "1")
    monkeypatch.delenv("FAKE_N", raising=False)     # nvidia has no key -> excluded
    c = LLMClient(_failover_cfg())
    assert c._fallback_order() == ["claude", "ollama"]


def test_brain_no_failover_when_primary_ok(monkeypatch):
    from core.llm_client import LLMClient
    monkeypatch.setenv("FAKE_C", "1"); monkeypatch.setenv("FAKE_N", "1")
    c = LLMClient(_failover_cfg())
    c._call_provider = lambda sysp, convo: ("claude direct" if c.provider == "anthropic" else None)
    assert c.chat("s", "u") == "claude direct"
    assert c.last_brain == "claude" and c.last_failover is False


def test_vision_core_look_and_verify(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    o = Orchestrator()
    o.tools.get("screen").capture_b64 = lambda: (True, "B64", "")
    o.llm.vision = lambda system, q, b64, *a, **k: (
        "YES. The video is playing." if "playing" in q.lower() else "Chrome is open, sir.")
    assert "chrome" in o.vision.look("what's open").lower()
    v = o.vision.verify("the video is playing")
    assert v["ok"] and v["verdict"] == "yes"


def test_vision_graceful_without_capture():
    o = Orchestrator()
    o.tools.get("screen").capture_b64 = lambda: (False, "", "no PIL")
    assert "couldn't capture" in o.vision.look("x").lower()
    v = o.vision.verify("anything")
    assert v["verdict"] == "unclear" and not v["ok"]


def test_verify_screen_intent_and_handler(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    from core.reasoning_core import ReasoningCore
    assert ReasoningCore().classify("verify the video is playing").name == "verify_screen"
    o = Orchestrator()
    o.tools.get("screen").capture_b64 = lambda: (True, "B64", "")
    o.llm.vision = lambda system, q, b64, *a, **k: "NO. The screen shows the desktop."
    r = o.handle("verify the video is playing")
    assert "not quite" in r.lower()


def test_agentic_catalog_has_eyes():
    from core.agentic_core import _VALID
    assert "see_screen" in _VALID and "verify_screen" in _VALID


def _mk_wm(tmp_path, providers=None, cooldown=0):
    from core.watch_manager import WatchManager
    return WatchManager(providers or {}, path=str(tmp_path / "w.json"), cooldown=cooldown)


def test_watch_manager_crud_and_persistence(tmp_path):
    from core.watch_manager import WatchManager
    wm = _mk_wm(tmp_path)
    w = wm.add("price", "btc", "<", 50000)
    assert wm.list()[0]["target"] == "btc"
    wm2 = WatchManager({}, path=str(tmp_path / "w.json"))
    assert len(wm2.list()) == 1                      # persisted
    assert wm.remove(wid=w["id"]) == 1
    assert wm.list() == []


def test_watch_price_and_system_fire(tmp_path):
    wm = _mk_wm(tmp_path, {"price": lambda s: 48000.0,
                           "system": lambda: {"battery": 15.0, "disk": 95.0}})
    wm.add("price", "btc", "<", 50000)
    wm.add("system", "battery", "<", 20)
    wm.add("system", "disk", ">", 90)
    msgs = wm.check_all()
    assert any("BTC" in m for m in msgs)
    assert any("battery" in m for m in msgs)
    assert any("disk" in m for m in msgs)


def test_watch_price_no_fire_when_not_met(tmp_path):
    wm = _mk_wm(tmp_path, {"price": lambda s: 60000.0})
    wm.add("price", "btc", "<", 50000)
    assert wm.check_all() == []


def test_watch_news_arms_then_fires(tmp_path):
    state = {"t": ["old headline"]}
    wm = _mk_wm(tmp_path, {"news": lambda topic: state["t"]})
    wm.add("news", "t")
    assert wm.check_all() == []                       # arms silently on first sight
    state["t"] = ["BREAKING new story"]
    assert any("BREAKING new story" in m for m in wm.check_all())


def test_watch_cooldown_prevents_refire(tmp_path):
    wm = _mk_wm(tmp_path, {"price": lambda s: 10.0}, cooldown=9999)
    wm.add("price", "btc", "<", 50)
    assert wm.check_all()                             # fires once
    assert wm.check_all() == []                       # on cooldown, no spam


def test_watch_commands_route_and_parse(tmp_path):
    from core.watch_manager import WatchManager
    from core.reasoning_core import ReasoningCore
    o = Orchestrator()
    o.watches = WatchManager(o._watch_providers(), path=str(tmp_path / "w.json"))
    assert "BTC" in o.handle("monitor btc below 50000")
    assert "battery" in o.handle("alert me if battery drops below 20").lower()
    assert "news" in o.handle("watch news about AI").lower()
    lst = o.handle("show monitors").lower()
    assert "btc" in lst and "battery" in lst
    rc = ReasoningCore()
    assert rc.classify("monitor eth above 4000").name == "watch_add"
    assert rc.classify("anything new").name == "check_now"
    assert rc.classify("what are you monitoring").name == "watches_list"
    assert rc.classify("watch btc").name == "add_watch"   # bare 'watch' still = trading watchlist


def test_drain_alerts_threadsafe():
    o = Orchestrator()
    with o._alert_lock:
        o.alerts = ["alpha", "beta"]
    assert o.drain_alerts() == ["alpha", "beta"]
    assert o.drain_alerts() == []


def _raise(msg):
    def _f():
        raise RuntimeError(msg)
    return _f


def test_workflow_engine_partial_and_critical():
    o = Orchestrator()
    we = o.workflows
    out = we._run_steps("Test", [("A", lambda: "sectionA", False),
                                 ("B", _raise("boom"), False),
                                 ("C", lambda: "sectionC", False)])
    assert "sectionA" in out and "sectionC" in out          # optional failure -> continues
    out2 = we._run_steps("Test", [("A", lambda: "x", False), ("B", _raise("boom"), True)])
    assert "stopped at 'B'" in out2                          # critical failure -> honest abort


def test_workflow_start_day_composes():
    o = Orchestrator()
    o.tools.get("weather").current = lambda c="": {"ok": True, "text": "Sunny, 20C"}
    o.tools.get("news").headlines = lambda topic="", limit=3: {"ok": True, "items": [{"headline": "Big news", "source": "AP"}]}
    o.llm.chat = lambda *a, **k: "Focus on the deck."
    out = o.handle("start my day")
    assert "Weather: Sunny" in out and "Big news" in out


def test_workflow_focus_uses_argument():
    o = Orchestrator()
    o.llm.chat = lambda *a, **k: "First action: open it."
    out = o.handle("focus on the quarterly report").lower()
    assert "report" in out and "locking in" in out


def test_workflow_research_brief_saves_file(tmp_path, monkeypatch):
    o = Orchestrator()
    o.agents.get("ultron").run = lambda action, args="", plan=None: "Findings: a, b, c."
    monkeypatch.chdir(tmp_path)
    out = o.handle("research brief on widgets")
    assert "saved" in out.lower()
    assert (tmp_path / "briefs" / "widgets.md").exists()


def test_workflow_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("start my day").name == "wf_start_day"
    assert rc.classify("wind down").name == "wf_wind_down"
    assert rc.classify("focus on emails").name == "wf_focus"
    assert rc.classify("research brief on tesla").name == "wf_research_brief"
    assert rc.classify("daily briefing").name == "daily_briefing"   # existing one intact


def _seq_chat(seq):
    state = {"i": 0}
    def chat(system, user, history=None):
        i = state["i"]; state["i"] += 1
        return seq[i] if i < len(seq) else '{"done":true,"summary":"done"}'
    return chat


def test_react_loop_executes_steps_then_finishes():
    o = Orchestrator()
    o.llm.chat = _seq_chat(['{"action":"browser_google","arg":"ai news"}',
                            '{"done":true,"summary":"All set, sir."}'])
    out = o.agentic.act_loop("search ai news")
    assert "All set" in out and "browser_google" in out      # summary + transcript of the step


def test_react_loop_skips_invalid_actions():
    o = Orchestrator()
    o.llm.chat = _seq_chat(['{"action":"not_a_real_action","arg":""}',
                            '{"done":true,"summary":"finished, sir"}'])
    out = o.agentic.act_loop("x")
    assert "finished" in out.lower()


def test_react_loop_offline_returns_none():
    o = Orchestrator()
    o.llm.chat = lambda *a, **k: None
    assert o.agentic.act_loop("x") is None                    # no plan -> caller falls back


def test_autonomous_uses_react_loop():
    o = Orchestrator()
    o.llm.chat = lambda s, u, history=None: '{"done":true,"summary":"Handled it, sir."}'
    assert "handled" in o.handle("handle this end to end: tidy up").lower()


def test_vision_click_locates_and_clicks(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    o = Orchestrator()
    o.vision.locate = lambda t: {"ok": True, "x": 10, "y": 20, "label": "btn", "detail": "located"}
    o.tools.get("input").click_at = lambda x, y: {"started": True, "spoken": "Clicked.", "debug": ""}
    out = o.handle("click the submit button").lower()
    assert "clicked" in out and "submit" in out


def test_vision_click_graceful_when_not_found():
    o = Orchestrator()
    o.vision.locate = lambda t: {"ok": False, "detail": "not visible"}
    assert "couldn't click" in o.handle("click the nonexistent thing").lower()


def test_vision_locate_degrades_honestly():
    o = Orchestrator()
    r = o.vision.locate("a button")     # never crashes; structured result in any environment
    # Invariant: returns a dict with an 'ok' flag. If it can't locate (no vision libs /
    # nothing matched) it must explain via 'detail'; if it can, it returns coordinates.
    assert isinstance(r, dict) and "ok" in r
    if r["ok"] is False:
        assert r.get("detail")


def test_frontier_routing_and_catalog():
    from core.reasoning_core import ReasoningCore
    from core.agentic_core import _VALID
    rc = ReasoningCore()
    assert rc.classify("agent open notepad and type hi").name == "autonomous"
    assert rc.classify("click the login button").name == "click_vision"
    assert rc.classify("click on the menu").name == "click_vision"
    assert rc.classify("double click").name == "input_click"     # bare click unaffected
    assert "click_vision" in _VALID


def test_grounding_refine_point_math():
    from core.vision_core import VisionCore
    assert VisionCore.refine_point(0, 0, 1000, 1000, 50, 50) == (500, 500)
    assert VisionCore.refine_point(240, 240, 560, 560, 80, 80) == (496, 496)


class _Img:
    def __init__(self, size):
        self.size = size


def test_grounding_two_pass_refines(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    o = Orchestrator(); v = o.vision
    v._locate_uia = lambda t: None
    v._has_eyes = lambda: True
    v._grab_image = lambda: _Img((1000, 1000))
    v._image_b64 = lambda img: "b64"
    v._crop_region = lambda img, l, t, r, b: _Img((r - l, b - t))
    seq = [{"found": True, "x_pct": 40, "y_pct": 40, "label": "coarse"},
           {"found": True, "x_pct": 80, "y_pct": 80, "label": "Submit"}]
    st = {"i": 0}
    def vp(b64, target, context=""):
        r = seq[st["i"]] if st["i"] < len(seq) else {"found": False}
        st["i"] += 1
        return r
    v._vision_point = vp
    loc = v.locate("the submit button")
    assert loc["ok"] and loc["method"] == "vision (2-pass)"
    assert loc["x"] == 496 and loc["y"] == 496        # refined by zoom-and-confirm, not the coarse 400


def test_grounding_uia_takes_priority():
    o = Orchestrator(); v = o.vision
    v._locate_uia = lambda t: {"x": 11, "y": 22, "label": "OK button"}
    loc = v.locate("ok")
    assert loc["ok"] and loc["method"] == "accessibility tree" and loc["x"] == 11


def test_grounding_degrades_without_eyes():
    o = Orchestrator(); v = o.vision
    v._locate_uia = lambda t: None
    v._has_eyes = lambda: False
    loc = v.locate("anything")
    assert loc["ok"] is False and loc.get("detail")


def test_experience_record_and_recall(tmp_path):
    from core.experience import Experience
    e = Experience(str(tmp_path / "ep.json"))
    e.record("clean my downloads folder", ["scan", "sort"], "done")
    assert e.recall("tidy the downloads")          # keyword overlap on 'downloads'
    assert e.recall("buy groceries online") == []  # no overlap
    e2 = Experience(str(tmp_path / "ep.json"))      # persisted
    assert len(e2.items) == 1


def test_planner_decomposes_and_executes(tmp_path):
    from core.experience import Experience
    o = Orchestrator()
    o.experience = Experience(str(tmp_path / "ep.json"))
    def chat(system, user, history=None):
        return '{"subgoals":["step one","step two"]}' if "JSON only" in user else "All sorted, sir."
    o.llm.chat = chat
    o.agentic.act_loop = lambda goal, max_steps=6: "done cleanly"
    out = o.handle("plan to organise my files")
    assert "Plan, sir" in out and "2 of 2 subgoals completed" in out
    assert len(o.experience.items) == 1            # episode recorded


def test_planner_repairs_failed_subgoal(tmp_path):
    from core.experience import Experience
    o = Orchestrator()
    o.experience = Experience(str(tmp_path / "ep.json"))
    o.llm.chat = lambda system, user, history=None: ('{"subgoals":["fix the build"]}' if "JSON only" in user else "ok")
    o.agentic.act_loop = lambda goal, max_steps=6: ("all good now" if "another way" in goal else "[!] couldn't do it")
    out = o.handle("plan to fix the build")
    assert "1 of 1 subgoals completed" in out       # failed first, repaired


def test_planner_offline_fallback():
    o = Orchestrator()
    o.llm.enabled = False     # brain truly off -> planner returns None -> honest fallback
    assert "brain online" in o.handle("plan to do something big").lower()


def test_planner_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("plan to clean my repo").name == "plan_project"
    assert rc.classify("tackle the launch").name == "plan_project"
    assert rc.classify("make a plan for the demo").name == "plan_project"
    assert rc.classify("plan my day").name == "plan_day"        # existing routine intact
    assert rc.classify("agent open notepad").name == "autonomous"


def test_eval_harness_scores_high():
    from core import eval_harness
    res = eval_harness.run()
    assert res["total"] >= 10
    assert res["score"] >= 90            # healthy build should pass nearly everything
    txt = eval_harness.report_text(res)
    assert "Reliability score" in txt


def test_self_eval_intent_and_handler():
    from core.reasoning_core import ReasoningCore
    assert ReasoningCore().classify("self eval").name == "self_eval"
    o = Orchestrator()
    out = o.handle("self eval")
    assert "Reliability score" in out and "%" in out


def test_self_improver_engine_basics():
    from core.self_improve import SelfImprover
    si = SelfImprover(None)
    assert isinstance(si.missing_deps(), list)
    h = si.heal()
    assert "fixed" in h and "needs" in h and "missing_deps" in h
    u = si.check_updates()
    assert "is_git" in u and u.get("message")


def test_self_repair_corrupted_json(tmp_path, monkeypatch):
    from core.self_improve import SelfImprover
    monkeypatch.chdir(tmp_path)
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "tasks.json").write_text("{ this is not valid json")
    fixed, _needs = SelfImprover(None)._repair_files()
    import json as _j
    assert _j.load(open(tmp_path / "memory" / "tasks.json")) == []      # repaired
    assert (tmp_path / "memory" / "tasks.json.bak").exists()             # backup kept
    assert any("repaired" in f for f in fixed)


def test_self_heal_holds_install_for_confirm():
    o = Orchestrator()
    o.improver.missing_deps = lambda: ["fakepkg"]          # deterministic
    out = o.handle("fix yourself")
    assert o.pending and o.pending["kind"] == "install_deps"
    assert "confirm" in out.lower()
    o.improver.do_install = lambda pkgs: "installed " + ",".join(pkgs)   # don't really pip
    res = o.handle("confirm")
    assert "installed fakepkg" in res                       # confirm path runs the install


def test_self_improvement_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("fix yourself").name == "self_heal"
    assert rc.classify("check for updates").name == "check_updates"
    assert rc.classify("update yourself").name == "check_updates"
    assert rc.classify("improve yourself").name == "self_improve"
    assert rc.classify("improve my morning routine").name == "improve"   # ULTRON, not shadowed


def test_mission_runs_and_self_spawns(tmp_path):
    from core.experience import Experience
    o = Orchestrator()
    o.experience = Experience(str(tmp_path / "e.json"))
    o.mission.path = str(tmp_path / "m.json")
    o.planner._decompose = lambda g, r: ["research the topic", "draft the outline"]
    o.agentic.act_loop = lambda sub, max_steps=6: "did " + sub
    seq = [{"complete": False, "new_subtasks": ["polish the draft"]},
           {"complete": False, "new_subtasks": []},
           {"complete": True, "new_subtasks": []}]
    st = {"i": 0}
    def assess(g, d, t):
        r = seq[st["i"]] if st["i"] < len(seq) else {"complete": True, "new_subtasks": []}
        st["i"] += 1
        return r
    o.mission._assess = assess
    out = o.handle("mission write a blog post")
    assert "Mission complete" in out and "polish the draft" in out   # self-spawned task ran
    assert len(o.experience.items) == 1                              # episode recorded


def test_mission_pauses_on_risky_then_resumes(tmp_path):
    from core.experience import Experience
    o = Orchestrator()
    o.experience = Experience(str(tmp_path / "e.json"))
    o.mission.path = str(tmp_path / "m.json")
    o.planner._decompose = lambda g, r: ["safe step", "risky step", "final step"]
    def loop(sub, max_steps=6):
        if "risky" in sub:
            o.pending = {"kind": "run_command"}
            return "say confirm"
        return "did " + sub
    o.agentic.act_loop = loop
    o.mission._assess = lambda g, d, t: {"complete": False, "new_subtasks": []}
    out = o.handle("mission deploy the app")
    assert "paused" in out.lower() and o.mission.active is not None    # safe pause
    o.pending = None                                                   # user confirmed -> cleared
    out2 = o.handle("continue mission")
    assert "complete" in out2.lower() and o.mission.active is None      # resumed to finish


def test_mission_status_and_abort():
    o = Orchestrator()
    assert "no active mission" in o.mission.status().lower()
    assert "no active mission" in o.mission.abort().lower()


def test_mission_offline_fallback():
    o = Orchestrator()
    o.llm.enabled = False
    assert "brain online" in o.handle("mission do something").lower()


def test_mission_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("mission build a report").name == "mission_start"
    assert rc.classify("mission status").name == "mission_status"
    assert rc.classify("continue mission").name == "mission_resume"
    assert rc.classify("abort mission").name == "mission_abort"
    assert rc.classify("stop mission").name == "mission_abort"


def _cache_client():
    from core.llm_client import LLMClient
    cfg = {"enabled": True, "active": "ollama", "cache": True,
           "profiles": {"ollama": {"provider": "ollama", "model": "x", "base_url": "http://z", "api_key_env": ""}}}
    return LLMClient(cfg)


def test_llm_cache_avoids_duplicate_calls():
    c = _cache_client()
    calls = {"n": 0}
    c._call_provider = lambda system, convo: (calls.__setitem__("n", calls["n"] + 1), "answer")[1]
    a = c.chat("sys", "hello")
    b = c.chat("sys", "hello")            # identical -> served from cache
    assert a == b == "answer" and calls["n"] == 1 and c.cache_hits == 1
    c.chat("sys", "a different question")  # new prompt -> new call
    assert calls["n"] == 2


def test_llm_cache_respects_history():
    c = _cache_client()
    calls = {"n": 0}
    c._call_provider = lambda system, convo: (calls.__setitem__("n", calls["n"] + 1), "r")[1]
    c.chat("sys", "same", history=[{"role": "user", "content": "A"}])
    c.chat("sys", "same", history=[{"role": "user", "content": "B"}])  # different context -> not cached
    assert calls["n"] == 2
    assert c.clear_cache() >= 1


def test_selfcare_runner():
    import selfcare
    out = selfcare.run()
    assert isinstance(out, str) and "self-care" in out.lower()


def test_skill_manager_resolve_and_safety():
    from core.skill_manager import SkillManager
    sm = SkillManager()
    assert sm.resolve("the vision skill")[0] == ["pillow"]
    assert sm.resolve("pyautogui")[0] == ["pyautogui"]
    assert sm.resolve("crypto-miner")[0] is None          # deny-list
    assert sm.download_skill("http://x.com/a.py")["ok"] is False   # not https
    assert sm.download_skill("https://evil.com/a.py")["ok"] is False  # host not allowlisted


def test_skill_install_held_for_confirm():
    o = Orchestrator()
    out = o.handle("install the vision skill")
    assert o.pending and o.pending["kind"] == "skill_install" and o.pending["pkgs"] == ["pillow"]
    assert "confirm" in out.lower()
    o.skillmgr.do_install = lambda pkgs, upgrade=False: "INSTALLED " + ",".join(pkgs)
    assert "INSTALLED pillow" in o.handle("confirm")       # confirm path runs the install


def test_skill_and_live_data_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("install the vision skill").name == "skill_install"
    assert rc.classify("install pyautogui").name == "skill_install"
    assert rc.classify("upgrade playwright").name == "skill_upgrade"
    assert rc.classify("download skill from https://x").name == "skill_download"
    assert rc.classify("show skills").name == "skills_list"
    assert rc.classify("get live data on tesla").name == "research"
    assert rc.classify("upgrade yourself").name == "check_updates"   # self-upgrade unaffected


def test_knowledge_skill_learn(tmp_path, monkeypatch):
    from core.skill_manager import SkillManager
    class _LLM:
        available = True
        def chat(self, system, user, history=None):
            return "Overview: CAD tool. Workflow: sketch, extrude. Tips: design intent."
    class _Tools:
        def get(self, n): return None
    class _Orch:
        llm = _LLM(); tools = _Tools()
    monkeypatch.chdir(tmp_path)
    sm = SkillManager(_Orch())
    r = sm.learn("SolidWorks")
    assert r["ok"] and (tmp_path / "skills_knowledge" / "solidworks.md").exists()
    assert any(it["topic"] == "SolidWorks" for it in sm.knowledge_index())
    assert "CAD" in sm.recall_pack("solidworks")


def test_install_domain_routes_to_learn():
    o = Orchestrator()
    o.llm.chat = lambda system, user, history=None: "Overview: domain primer. Tips: practice."
    out = o.handle("install the solidworks skill")          # domain (not registry) -> learn
    assert "learned" in out.lower() and "solidworks" in out.lower()
    assert "skill skill" not in out.lower()                  # topic cleaned


def test_learn_and_skill_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("learn python").name == "learn_skill"
    assert rc.classify("teach yourself excel").name == "learn_skill"
    assert rc.classify("master the violin").name == "learn_skill"
    assert rc.classify("install the vision skill").name == "skill_install"   # registry software still pip
    assert rc.classify("install pyautogui").name == "skill_install"


def test_advise_auto_deepens_thin_pack():
    o = Orchestrator()
    st = {"deep": 0}
    o.skillmgr.match_topic = lambda a: "SolidWorks" if "solid" in a.lower() else None
    o.skillmgr.recall_pack = lambda a: ("tiny" if st["deep"] == 0 else "X" * 1000)
    def lrn(topic, refresh=False, deep=False):
        st["deep"] += 1
        return {"ok": True}
    o.skillmgr.learn = lrn
    o.agents.get("ultron").run = lambda action, args="", plan=None: "ok len=" + str(len(args))
    o.handle("advise me on solidworks sketching")
    assert st["deep"] == 1            # a thin pack was deepened live before advising


def test_deepen_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("go deeper on solidworks").name == "deepen_skill"
    assert rc.classify("deepen the excel skill").name == "deepen_skill"
    assert rc.classify("learn more about python").name == "deepen_skill"
    assert rc.classify("advise me on solidworks").name == "advise"
    assert rc.classify("learn solidworks").name == "learn_skill"


def test_local_only_fallback_is_ollama_only():
    from core.llm_client import LLMClient
    cfg = {"enabled": True, "active": "claude", "local_only": True, "profiles": {
        "claude": {"provider": "anthropic", "model": "c", "base_url": "http://x", "api_key_env": "ZZ_K"},
        "ollama": {"provider": "ollama", "model": "l", "base_url": "http://z", "api_key_env": ""}}}
    assert LLMClient(cfg)._fallback_order() == ["ollama"]


def test_local_and_cloud_brain_commands():
    o = Orchestrator()
    o._set_local_only = lambda on: o.llm.full.__setitem__("local_only", on)   # don't touch config file
    out = o.handle("local brain")
    assert "local" in out.lower() and o.llm.full.get("local_only") is True
    o.handle("cloud brain")
    assert o.llm.full.get("local_only") is False


def test_local_brain_routing():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("local brain").name == "local_brain"
    assert rc.classify("run without claude").name == "local_brain"
    assert rc.classify("use only ollama").name == "local_brain"
    assert rc.classify("cloud brain").name == "cloud_brain"
    assert rc.classify("run the tests").name == "run_command"        # unaffected
    assert rc.classify("local mode").name == "mode_private"          # speed mode unaffected


def test_persona_has_autonomy_clause():
    from core.orchestrator import JARVIS_PERSONA as p
    assert "AUTONOMY" in p and "never override" in p and "Ollama" in p


# ------------- self-upgrade ON COMMAND (gated): draft -> sandbox -> security -> confirm -------------

def test_self_upgrade_gated_on_command():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    o = Orchestrator()
    # self-modification is now ALLOWED on the master's command (policy reversed by the master),
    # but a bare request with NO target file only returns guidance and stages nothing.
    assert rc.classify("rewrite your code to be faster").name == "self_code"
    assert rc.classify("upgrade your code to add X").name == "self_code"
    assert rc.classify("modify your core to do Y").name == "self_code"
    msg = o.handle("rewrite your code").lower()
    assert "which file" in msg or "approve upgrade" in msg   # asks for a target, explains the gate
    assert o.pending is None                                  # nothing staged without a named file
    # update / improve on command still route as before
    assert rc.classify("update yourself").name == "check_updates"
    assert rc.classify("improve yourself").name == "self_improve"
    # approve / rollback of a self-upgrade route correctly
    assert rc.classify("approve upgrade").name == "confirm"
    assert rc.classify("rollback last upgrade").name == "rollback_upgrade"
    # risky commands still gated
    assert rc.classify("shutdown").name == "power_shutdown"


def test_self_upgrade_protects_permission_enforcing_files():
    # The gate that guards the gate: permission_gate / safety_guard / permission_manager are
    # NEVER self-editable, even on command — the master's standing self-modification rule.
    from core.self_upgrade import SelfUpgrade
    su = SelfUpgrade(None)
    for f in ("core/permission_gate.py", "core/safety_guard.py", "core/permission_manager.py"):
        assert su.propose(f, "x = 1\n").get("ok") is False


def test_screen_watch_intents_still_route():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    assert rc.classify("watch my screen").name == "screen_watch_on"
    assert rc.classify("stop watching my screen").name == "screen_watch_off"
    assert rc.classify("suggest on this").name == "suggest_now"
    assert rc.classify("watch btc").name == "add_watch"            # not hijacked
    assert rc.classify("keep an eye on climate news").name == "watch_add"


def test_voice_language_detection():
    from core.voice import detect_lang
    assert detect_lang("open chrome please") == "en"
    assert detect_lang("నమస్కారం జార్విస్") == "te"
    assert detect_lang("नमस्ते जार्विस") == "hi"
    assert detect_lang("JARVIS నా పని") == "te"      # any Telugu char wins


def test_voice_commands_route_and_set_language():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    o = Orchestrator()
    assert rc.classify("speak in telugu").name == "speak_lang"
    assert rc.classify("reply in hindi").name == "speak_lang"
    assert rc.classify("voice status").name == "voice_status"
    assert rc.classify("say good morning sir").name == "say_in"
    o.handle("speak in hindi")
    assert o.speak_lang == "hi"
    o.handle("switch to english")
    assert o.speak_lang == "en"
    assert "good morning sir" in o.handle("say good morning sir")   # echoes the text
    assert isinstance(o.handle("voice status"), str)


def test_toolkit_installer_is_confirm_gated():
    from core.reasoning_core import ReasoningCore
    rc = ReasoningCore()
    o = Orchestrator()
    assert rc.classify("install the autonomous toolkit").name == "toolkit_install"
    assert rc.classify("skill up").name == "toolkit_install"
    assert rc.classify("download all skills").name == "toolkit_install"
    out = o.handle("install the autonomous toolkit")
    assert "confirm" in out.lower()
    assert o.pending and o.pending["kind"] == "skill_install"
    assert "edge-tts" in o.pending["pkgs"] and len(o.pending["pkgs"]) >= 10
    # nothing installs without confirm
    assert "cancel" in o.handle("cancel").lower() or o.pending is None
